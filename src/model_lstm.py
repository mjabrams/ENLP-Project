import keras
import numpy as np
import pandas as pd
from keras.callbacks import ModelCheckpoint, ReduceLROnPlateau, EarlyStopping
from keras.constraints import maxnorm
from keras.layers import Embedding
from keras.layers.core import Dense, Dropout
from keras.layers.recurrent import LSTM
from keras.models import Sequential
from keras.optimizers import SGD
from keras.preprocessing import sequence
from keras.preprocessing.text import Tokenizer

seed = 19960214
np.random.seed(seed)


def load_train_data(path):  # loads data , caluclate Mean & subtract it data, gets the COV. Matrix.
    D = pd.read_csv(path, sep='\t', header=0)
    feature_names = np.array(list(D.columns.values))
    X_train = np.array(list(D['Phrase']))
    Y_train = np.array(list(D['Sentiment']));
    return X_train, Y_train, feature_names


def load_test_data(path):  # loads data , caluclate Mean & subtract it data, gets the COV. Matrix.
    D = pd.read_csv(path, sep='\t', header=0)
    X_test = np.array(list(D['Phrase']))
    X_test_PhraseID = np.array(list(D['PhraseId']))
    return X_test, X_test_PhraseID


def shuffle_2(a, b):  # Shuffles 2 arrays with the same order
    s = np.arange(a.shape[0])
    np.random.shuffle(s)
    return a[s], b[s]


X_train, Y_train, feature_names = load_train_data('../data/train_extract.tsv')
X_test, X_test_PhraseID = load_test_data('../data/test.tsv')
print('============================== Training data shapes ==============================')
print('X_train.shape is ', X_train.shape)
print('Y_train.shape is ', Y_train.shape)

Tokenizer = Tokenizer()
Tokenizer.fit_on_texts(np.concatenate((X_train, X_test), axis=0))
# Tokenizer.fit_on_texts(X_train)
Tokenizer_vocab_size = len(Tokenizer.word_index) + 1
print("Vocab size", Tokenizer_vocab_size)

# masking
num_test = 1000
mask = range(num_test)

Y_Val = Y_train[:num_test]
Y_Val2 = Y_train[:num_test]
X_Val = X_train[:num_test]

X_train = X_train[num_test:]
Y_train = Y_train[num_test:]

maxWordCount = 60
maxDictionary_size = Tokenizer_vocab_size

encoded_words = Tokenizer.texts_to_sequences(X_train)
encoded_words2 = Tokenizer.texts_to_sequences(X_Val)
encoded_words3 = Tokenizer.texts_to_sequences(X_test)

# padding all text to same size
X_Train_encodedPadded_words = sequence.pad_sequences(encoded_words, maxlen=maxWordCount)
X_Val_encodedPadded_words = sequence.pad_sequences(encoded_words2, maxlen=maxWordCount)
X_test_encodedPadded_words = sequence.pad_sequences(encoded_words3, maxlen=maxWordCount)

# One Hot Encoding
Y_train = keras.utils.to_categorical(Y_train, 5)
Y_Val = keras.utils.to_categorical(Y_Val, 5)

# shuffling the traing Set
shuffle_2(X_Train_encodedPadded_words, Y_train)

# model
model = Sequential()

model.add(Embedding(maxDictionary_size, 32, input_length=maxWordCount))  # to change words to ints
# model.add(Conv1D(filters=32, kernel_size=3, padding='same', activation='relu'))
# model.add(MaxPooling1D(pool_size=2))
# model.add(Dropout(0.5))
# model.add(Conv1D(filters=32, kernel_size=2, padding='same', activation='relu'))
# model.add(MaxPooling1D(pool_size=2))
# hidden layers
model.add(LSTM(10))
# model.add(Flatten())
model.add(Dropout(0.6))
model.add(Dense(1200, activation='relu', W_constraint=maxnorm(1)))
# model.add(Dropout(0.6))
model.add(Dense(500, activation='relu', W_constraint=maxnorm(1)))

# model.add(Dropout(0.5))
# output layer
model.add(Dense(5, activation='softmax'))

# Compile model
# adam=Adam(lr=learning_rate, beta_1=0.7, beta_2=0.999, epsilon=1e-08, decay=0.0000001)

model.summary()

learning_rate = 0.0001
epochs = 1
batch_size = 32  # 32
sgd = SGD(lr=learning_rate, nesterov=True, momentum=0.7, decay=1e-4)
Nadam = keras.optimizers.Nadam(lr=0.002, beta_1=0.9, beta_2=0.999, epsilon=1e-08, schedule_decay=0.004)
model.compile(loss='categorical_crossentropy', optimizer=Nadam, metrics=['accuracy'])

tensorboard = keras.callbacks.TensorBoard(log_dir='./logs/log_25', histogram_freq=0, write_graph=True,
                                          write_images=False)
checkpointer = ModelCheckpoint(filepath="./weights/weights_25.hdf5", verbose=1, save_best_only=True, monitor="val_loss")
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.8, patience=0, verbose=1, mode='auto', cooldown=0,
                              min_lr=1e-6)
earlyStopping = EarlyStopping(monitor='val_loss', min_delta=0, patience=6, verbose=1)

# Loading best weights
# model.load_weights("./weights/weights_19.hdf5")

print("=============================== Training =========================================")

history = model.fit(X_Train_encodedPadded_words, Y_train, epochs=epochs, batch_size=batch_size, verbose=1,
                    validation_data=(X_Val_encodedPadded_words, Y_Val),
                    callbacks=[tensorboard, reduce_lr, checkpointer, earlyStopping])

print("=============================== Score =========================================")

scores = model.evaluate(X_Val_encodedPadded_words, Y_Val, verbose=0)
print("Accuracy: %.2f%%" % (scores[1] * 100))
