import numpy as np
from os import urandom
from keras.callbacks import ModelCheckpoint, LearningRateScheduler
from keras.models import Model
from keras.layers import Dense, Conv1D, Input, Reshape, Permute, Add, Flatten, BatchNormalization, Activation, Dropout
from keras.regularizers import l2
import matplotlib.pyplot as plt
import time
from tensorflow.keras import layers

bs = 5000

cardinality = 32

def expand_key(k, t, n):
    ks = np.zeros((t+1, 64, n), dtype=np.uint8)

    for i in range(0, t+1):
        ks[i][0:64] = k[16:80]
        for j in range(80):
            k[j] = k[(j + 19) % 80]
        k[76 + 3] = 1 ^ k[76] ^ k[76 + 1] ^ k[76 + 3] ^ (k[76 + 1] & k[76 + 2]) ^ (k[76] & k[76 + 1] & k[76 + 2]) ^ (
                    k[76] & k[76 + 1] & k[76 + 3]) ^ (k[76] & k[76 + 2] & k[76 + 3])
        k[76 + 2] = 1 ^ k[76 + 2] ^ k[76 + 3] ^ (k[76] & k[76 + 1]) ^ (k[76] & k[76 + 3]) ^ (k[76 + 1] & k[76 + 3]) ^ (
                    k[76] & k[76 + 1] & k[76 + 3]) ^ (k[76] & k[76 + 2] & k[76 + 3])
        k[76 + 1] = k[76 + 1] ^ k[76 + 3] ^ (k[76 + 1] & k[76 + 3]) ^ (k[76 + 2] & k[76 + 3]) ^ (
                    k[76] & k[76 + 1] & k[76 + 2]) ^ (k[76] & k[76 + 1] & k[76 + 3]) ^ (k[76] & k[76 + 2] & k[76 + 3])
        k[76] = k[76] ^ k[76 + 2] ^ k[76 + 3] ^ (k[76 + 1] & k[76 + 2])
        if i == 0:
            k[15] = k[15] ^ 1
        elif i == 1:
            k[16] = k[16] ^ 1
        elif i == 2:
            k[16] = k[16] ^ 1
            k[15] = k[15] ^ 1
        elif i == 3:
            k[17] = k[17] ^ 1
        elif i == 4:
            k[17] = k[17] ^ 1
            k[15] = k[15] ^ 1
        elif i == 5:
            k[17] = k[17] ^ 1
            k[16] = k[16] ^ 1
        elif i == 6:
            k[17] = k[17] ^ 1
            k[16] = k[16] ^ 1
            k[15] = k[15] ^ 1
        elif i == 7:
            k[18] = k[18] ^ 1
        elif i == 8:
            k[18] = k[18] ^ 1
            k[15] = k[15] ^ 1
        elif i == 9:
            k[18] = k[18] ^ 1
            k[16] = k[16] ^ 1
        elif i == 10:
            k[18] = k[18] ^ 1
            k[16] = k[16] ^ 1
            k[15] = k[15] ^ 1
        elif i == 11:
            k[18] = k[18] ^ 1
            k[17] = k[17] ^ 1
    return (ks)


def encrypt_one_round(p, k, n):
    Y = np.zeros((64, 16, n), dtype=np.uint8)
    Z = np.zeros((64, 16, n), dtype=np.uint8)

    for j in range(16):
        for i in range(64):
            p[i][j] = p[i][j] ^ k[i]

    for i in range(0, 64, 4):
        Z[i + 3] = 1 ^ p[i] ^ p[i + 1] ^ p[i + 3] ^ (p[i + 1] & p[i + 2]) ^ (p[i] & p[i + 1] & p[i + 2]) ^ (
                    p[i] & p[i + 1] & p[i + 3]) ^ (p[i] & p[i + 2] & p[i + 3])
        Z[i + 2] = 1 ^ p[i + 2] ^ p[i + 3] ^ (p[i] & p[i + 1]) ^ (p[i] & p[i + 3]) ^ (p[i + 1] & p[i + 3]) ^ (
                    p[i] & p[i + 1] & p[i + 3]) ^ (p[i] & p[i + 2] & p[i + 3])
        Z[i + 1] = p[i + 1] ^ p[i + 3] ^ (p[i + 1] & p[i + 3]) ^ (p[i + 2] & p[i + 3]) ^ (
                    p[i] & p[i + 1] & p[i + 2]) ^ (p[i] & p[i + 1] & p[i + 3]) ^ (p[i] & p[i + 2] & p[i + 3])
        Z[i] = p[i] ^ p[i + 2] ^ p[i + 3] ^ (p[i + 1] & p[i + 2])

    for i in range(63):
        Y[(16 * i) % 63] = Z[i]
    Y[63] = Z[63]

    return Y


def encrypt(p, ks, n, nr):
    y = p
    for k in ks[0: nr]:
        y = encrypt_one_round(y, k, n)

    for j in range(16):
        for i in range(64):
            y[i][j] = y[i][j] ^ ks[nr][i]

    return (y)


def make_train_data(n, nr):
    K = np.zeros((80, n), dtype=np.uint8)
    for i in range(80):
        K[i] = np.frombuffer(urandom(n), dtype=np.uint8)
        K[i] = K[i] & 1
    ks = expand_key(K, nr, n)

    Xreal = np.zeros((64, 16, n), dtype=np.uint8)
    Xrand = np.zeros((64, 16, n), dtype=np.uint8)

    arr = [[0, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 0, 1, 1], [0, 1, 0, 0], [0, 1, 0, 1], [0, 1, 1, 0],
           [0, 1, 1, 1], [1, 0, 0, 0], [1, 0, 0, 1], [1, 0, 1, 0], [1, 0, 1, 1], [1, 1, 0, 0], [1, 1, 0, 1],
           [1, 1, 1, 0], [1, 1, 1, 1]]

    Active = np.array(arr).transpose()

    for i in range(0, 64):
        real = np.frombuffer(urandom(n), dtype=np.uint8)
        real = real & 1
        Xreal[i][0] = real

    for j in range(16):
        for i in range(4):
            Xreal[i][j] = Xreal[i][0] ^ Active[i][j]
        for i in range(4, 64):
            Xreal[i][j] = Xreal[i][0]

    for j in range(16):
        for i in range(0, 64):
            rand = np.frombuffer(urandom(n), dtype=np.uint8)
            rand = rand & 1
            Xrand[i][j] = rand

    creal = encrypt(Xreal, ks, n, nr)
    crand = encrypt(Xrand, ks, n, nr)

    creal = creal.reshape(1024, n)
    crand = crand.reshape(1024, n)

    cipher = np.concatenate((creal, crand), axis=1)
    cipher = cipher.transpose()

    Yreal = np.ones(n)
    Yrand = np.zeros(n)
    Y = np.concatenate((Yreal, Yrand))

    return (cipher, Y)


def cyclic_lr(num_epochs, high_lr, low_lr):
    res = lambda i: low_lr + ((num_epochs - 1) - i % num_epochs) / (num_epochs - 1) * (high_lr - low_lr)
    return (res)


def make_checkpoint(datei):
    res = ModelCheckpoint(datei, monitor='val_loss', save_best_only=True)
    return (res)

def grouped_convolution(y, nb_channels,ks):
       
        # in a grouped convolution layer, input and output channels are divided into `cardinality` groups,
        # and convolutions are separately performed within each group
        _d = nb_channels // cardinality
        groups = []
        for j in range(cardinality):
            groups.append(layers.Conv1D(_d, kernel_size=ks, padding='same')(y))
            
        # the grouped convolutional layer concatenates them as the outputs of the layer
        y = layers.concatenate(groups)
        

        return y
#make residual tower of convolutional blocks
def make_resnet(num_words=16,multiset=16, num_filters=512, num_outputs=1, d1=1024, d2=1024, word_size=4, ks=3,depth=5, reg_param=0.0001, final_activation='sigmoid'):
  #Input and preprocessing layers
  inp = Input(shape=(num_words * word_size *multiset ,))
  rs = Reshape((num_words*multiset, word_size))(inp)
  perm = Permute((2,1))(rs)
  #add a single residual layer that will expand the data to num_filters channels
  #this is a bit-sliced layer
  conv0 = Conv1D(num_filters , kernel_size=1, padding='same', kernel_regularizer=l2(reg_param))(perm)
  conv0 = BatchNormalization()(conv0)
  conv0 = Activation('relu')(conv0)
  #add residual blocks
  shortcut = conv0
  for i in range(depth):
    conv1 = Conv1D(num_filters, kernel_size=ks, padding='same', kernel_regularizer=l2(reg_param))(shortcut)
    conv1 = BatchNormalization()(conv1)
    conv1 = Activation('relu')(conv1)
    #grouped convolution
    conv1 = grouped_convolution(conv1, num_filters,ks)
    conv1 = BatchNormalization()(conv1)
    conv1 = Activation('relu')(conv1)
       
    conv2 = Conv1D(num_filters, kernel_size=ks, padding='same',kernel_regularizer=l2(reg_param))(conv1)
    conv2 = BatchNormalization()(conv2)
    conv2=Dropout(0.2)(conv2)
    conv2 = Activation('relu')(conv2)
    shortcut = Add()([shortcut, conv2])
  #add prediction head
  flat1 = Flatten()(shortcut)
  dense1 = Dense(d1,kernel_regularizer=l2(reg_param))(flat1)
  dense1 = BatchNormalization()(dense1)
  dense1 = Activation('relu')(dense1)
  dense2 = Dense(d2, kernel_regularizer=l2(reg_param))(dense1)
  dense2 = BatchNormalization()(dense2)
  dense2 = Activation('relu')(dense2)
  dense2=Dropout(0.2)(dense2)
  out = Dense(num_outputs, activation=final_activation, kernel_regularizer=l2(reg_param))(dense2)
  model = Model(inputs=inp, outputs=out)
  return(model)

def train_present_distinguisher(num_epochs, num_rounds, depth):
    # create the network
    net = make_resnet(depth=depth, reg_param=10 ** -5)
    net.compile(optimizer='adam', loss='mse', metrics=['acc'])

    # generate training and validation data and test data
    X, Y = make_train_data(2 ** 20, num_rounds)
    X_eval, Y_eval = make_train_data(2 ** 16, num_rounds)
    X_test, Y_test = make_train_data(2 ** 16, num_rounds)

    # create learnrate schedule
    lr = LearningRateScheduler(cyclic_lr(10, 0.002, 0.0001))

    # train and evaluate
    h = net.fit(X, Y, epochs=num_epochs, batch_size=bs, validation_data=(X_eval, Y_eval), callbacks=[lr])
    loss, accuracy = net.evaluate(X_test, Y_test)

    print("\nWhen training for a", num_rounds, "round PRESENT ", num_epochs, "epochs:")
    print("\nBest validation accuracy: ", np.max(h.history['val_acc']))
    print('\nTest loss:', loss)
    print('\nTest accuracy:', accuracy)

    # f = open(save_path + "result_for_lyu_train_PRESENT.txt", "a")
    f = open("./result_for_lyu_train_PRESENT.txt", "a")
    f.write("\nWhen training for a " + str(num_rounds) + "-round PRESENT " + str(num_epochs) + " epochs:")
    f.write("\nBest validation accuracy: " + str(np.max(h.history['val_acc'])))
    f.write('\nTest loss: ' + str(loss))
    f.write('\nTest accuracy: ' + str(accuracy))
    f.close()

    return (net, h)


# test(7,8,9)
# save_path = "./results_for_PRESENT/"

time_start = time.time()

_, history = train_present_distinguisher(10, num_rounds=7, depth=10)

time_end = time.time()
total_time = time_end - time_start
print('\nTotal training time is: %.2f seconds.' % total_time)

# f = open(save_path + "result_for_lyu_train_PRESENT.txt","a")
f = open("./result_for_lyu_train_PRESENT.txt", "a")
f.write('\nTotally training time is: %.2f seconds.\n' % total_time)
f.close()

acc = history.history['acc']
val_acc = history.history['val_acc']
epochs = range(1, len(acc) + 1)

plt.figure(figsize=(6, 4))
plt.plot(epochs, acc, 'b', label='Training accuracy')
plt.plot(epochs, val_acc, 'g', label='Validation accuracy')
plt.title('Training and validation accuracy')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.legend(loc='upper left')
# plt.savefig(fname = save_path + "Training_10r_PRESENT_10_epochs_"+time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())+".png")
plt.savefig(fname="./Training_7r_PRESENT_10_epochs_" + time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + ".png")
plt.show()
