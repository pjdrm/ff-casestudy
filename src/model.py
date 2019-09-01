'''
Created on Aug 31, 2019

@author: pjdrm
'''
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers import Bidirectional
from dataset import Data
import sys
import json

class BiLSTMCodeSwitch(object):
    '''
    LSTM deep neural network for the code switch task.
    The LSTM learns how to classify sequences of queries
    into their corresponding product category. The sequences are represented
    with bag-of-words vectors.
    '''
    def __init__(self, dataset, lstm_units=75, epochs=100):
        '''
        Constructor
        :param dataset: DatasetCodeSwitch object argument
        :param lstm_units: dimensionality of the output space
        :param epochs: number of epochs to train the BiLSTM
        '''
        self.dataset = dataset
        self.epochs = epochs
        self.model = Sequential()
        self.model.add(LSTM(lstm_units,
                            input_shape=(self.dataset.W_counts.shape[1],
                                         self.dataset.W_counts.shape[2]),
                            return_sequences=True))
        self.model.add(Dense(len(self.dataset.cat_map.keys()),
                             activation='softmax'))
        self.model.compile(loss='categorical_crossentropy',
                           optimizer='adam',
                           metrics=['accuracy'])
    
    def train_bilstm(self, out_model_fp):
        '''
        Trains the LSTM model and saves the model to disk.
        :param out_model_fp: out model file path
        '''
        self.model.fit(self.dataset.W_counts,
                       self.dataset.Y,
                       epochs=self.epochs,
                       verbose=2)
        
                
if __name__ == "__main__":
    if len(sys.argv) == 1:
        cfg_path = "configs.json"
    else:
        cfg_path = sys.argv[1]
        
    with open(cfg_path) as f:    
        cfg = json.load(f)
        
    dataset = Data(cfg['dataset']['products_path'],
                   cfg['dataset']['queries_path'],
                   max_samples=cfg['dataset']['max_samples'],
                   max_W=cfg['dataset']['max_W'])
    
    bilst_cs = BiLSTMCodeSwitch(dataset,
                                cfg['model']['lstm_units'],
                                cfg['model']['epochs'])
    bilst_cs.train_bilstm(cfg['model']['out_model_fp'])