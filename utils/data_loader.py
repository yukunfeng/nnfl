#! /usr/bin/env python3
"""
Authors: fengyukun
Date:   2016/03/22
Brief:  data loader
The input data should have following format:
    1. Provide a directory where data files lie
    2. All files are named by verb itself
    3. Each line in one data file should like this:
        frame_id\tword1 word2 word3\tverb\tword4 word5, 
        where \t means a tab seperator and words are separated
        by a space. If the words on the left or right of verb are empty, 
        keep the seperator \t here. For example, 
            2\t\ttake\taway
            3\tI like\teating\t
"""

import os
import nltk
import numpy as np
import gensim
from gensim.models import Word2Vec
from tools import*

import logging
logging.basicConfig(
    level=logging.DEBUG, 
    format=" [%(levelname)s]%(filename)s:%(lineno)s[function:%(funcName)s] %(message)s"
)

class DataLoader(object):
    """
    Data loader class
    """
    def __init__(self, data_path, vocab, oov, left_win=5, right_win=5, use_verb=False, lower=False):
        """
        vocab: dict, word to word index. The vocab must have oov and keep oov_index=vocab[oov]
        oov: string, out ov vocabulary 
                Used when word is not in vocabulary and padding where necessary
        left_win: int, left windows length, -1 will include all left words
        right_win: int, right windows length, -1 will include all right words
        use_verb: bool, whether use verb
        lower: bool, whether lowercase the sentences
        """

        # verb to data set x and data answer y
        self.verb2x = {}
        self.verb2y = {}
        file_names = os.listdir(data_path)
        for file_name in file_names:
            file_path = "%s/%s" % (data_path, file_name)
            fh = open(file_path, "r")
            for line in fh:
                line = line.strip("\n")
                # Skip empty line
                if line == "":
                    continue
                if lower:
                    line = line.lower()
                items = line.split("\t")
                if len(items) != 4:
                    logging.error("data format error: %s" % line)
                    raise Exception
                frame_id = int(items[0])
                # sents[0](left sentences), sents[1](verb), sents[2](right sentence)
                sents = [nltk.word_tokenize(items[i]) for i in range(1, len(items))]
                sents_indexs = sents2indexs(sents, vocab, oov)
                left_sent = sent_indexs_trunc(sents_indexs[0], left_win, "left", vocab[oov])
                right_sent = sent_indexs_trunc(sents_indexs[2], right_win, "right", vocab[oov])
                # Final input sentence
                if use_verb:
                    input_sent = left_sent + sents_indexs[1] + right_sent
                else:
                    input_sent = left_sent + right_sent
                if file_name not in self.verb2x:
                    self.verb2x[file_name] = []
                    self.verb2y[file_name] = []
                self.verb2x[file_name].append(input_sent)
                self.verb2y[file_name].append(frame_id)

            fh.close()

    def get_data(self, train_part, test_part, validation_part,\
            sent_num_threshold=0, frame_threshold=0):
        """
        Divide these data into train data, test data and validation data 

        train_part, test_part, validation_part: float, sum of three <= 1.0
        sent_num_threshold: int, the threshold of sentence number for each verb
        frame_threshold: int, the threshold of verb frame number for each verb

        return [train, test, validation], each element is a dict where key is
            verb and value is a two-length list. That is 
            train_x = train[verb][0]
            train_y = train[verb][1]
            train_x, train_y both are numpy.ndarray
        """

        # Parameters checking
        if train_part < 0 or test_part < 0 or validation_part < 0\
                or (train_part + test_part + validation_part) > 1.0:
            logging.error("Invalid parameters: train_part:%f\ttest_part:%f\tvalidation_part:%f" \
                % (train_part, test_part, validation_part))
            raise Exception

        train = {}
        test = {}
        validation = {}
        for verb in self.verb2x:
            x = self.verb2x[verb]    
            y = self.verb2y[verb]
            frames = set(y)
            if len(x) < sent_num_threshold or len(frames) < frame_threshold:
                continue
            train_x = []
            train_y = []
            test_x = []
            test_y = []
            validation_x = []
            validation_y = []
            for frame in frames:
                frame_x = [x[i] for i in range(0, len(y)) if y[i] == frame]
                train_num = int(train_part * len(frame_x)) 
                train_x.extend(frame_x[0:train_num])
                train_y.extend([frame for k in range(0, train_num)])
                test_num = int(test_part * len(frame_x))
                test_x.extend(frame_x[train_num:train_num + test_num])
                test_y.extend([frame for k in range(0, test_num)])
                validation_num = int(validation_part * len(frame_x))
                real_sum = train_num + test_num + validation_num
                validation_x.extend(frame_x[train_num + test_num:real_sum])
                validation_y.extend([frame for k in range(0, validation_num)])
                # Add the loss to train data (because int operation is a floor function)
                loss_num = int((train_part + test_part + validation_part) * len(frame_x)) - real_sum
                train_x.extend(frame_x[real_sum:real_sum + loss_num])
                train_y.extend([frame for k in range(0, loss_num)])
             
            # Shuffling
            train_x, train_y = shuffle_two_lists(train_x, train_y)
            test_x, test_y = shuffle_two_lists(test_x, test_y)
            validation_x, validation_y = shuffle_two_lists(validation_x, validation_y)
            # The final result
            train[verb] = [np.array(train_x, dtype=INT), np.array(train_y, dtype=INT)]
            test[verb] = [np.array(test_x, dtype=INT), np.array(test_y, dtype=INT)]
            validation[verb] = [
                np.array(validation_x, dtype=INT), np.array(validation_y, dtype=INT)
            ]
        return [train, test, validation]


def test_data_loader():
    p = {
        # "word2vec_path": "../data/data2vec.txt", 
        "word2vec_path": "../data/data2vec.txt.chn", 
        # "word2vec_path": "../../word2vec/vector_model/glove.twitter.27B.25d.txt", 
        "vec_binary": False, 
        "norm_vec": False, 
        "data_path": "../data/sample/", 
        "oov": "O_O_V", 
        "left_win": 2, 
        "right_win": 2, 
        "use_verb": True, 
        "lower": True
    } 
    # Generate vocab
    vec_model = gensim.models.Word2Vec.load_word2vec_format(
        p["word2vec_path"], binary=p["vec_binary"], norm_only=p["norm_vec"]
    )
    vocab = {}
    for word, obj in vec_model.vocab.items():
        vocab[word] = obj.index
    # Add oov to vocab
    vocab[p["oov"]] = max(vocab.values()) + 1
    index2word_vocab = {k:v for v, k in vocab.items()}

    data_loader = DataLoader(
        data_path=p["data_path"], 
        vocab=vocab, 
        oov=p["oov"], 
        left_win=p["left_win"], 
        right_win=p["right_win"], 
        use_verb=p["use_verb"], 
        lower=p["lower"]
    )
    train, test, validation = data_loader.get_data(0.5, 0.4, 0.1)
    for verb in train.keys():
        print("verb:%s" % verb)
        print("training data:%d" % len(train[verb][1]))
        sents = indexs2sents(train[verb][0], index2word_vocab)
        for sent, frame in zip(sents, train[verb][1]):
            print("%s:\t%s" % (frame, sent))
        print("\ntesting data:%d" % len(test[verb][1]))
        sents = indexs2sents(test[verb][0], index2word_vocab)
        for sent, frame in zip(sents, test[verb][1]):
            print("%s:\t%s" % (frame, sent))
        print("\nvalidation data:%d" % len(validation[verb][1]))
        sents = indexs2sents(validation[verb][0], index2word_vocab)
        for sent, frame in zip(sents, validation[verb][1]):
            print("%s:\t%s" % (frame, sent))
    

if __name__ == "__main__":
    test_data_loader()
