import os
import numpy as np
from sklearn.model_selection import train_test_split

from src.utilities.memory_maker import MemoryMaker


class GenFiles:
    frame_file = 'frame_{}_{:07}.npy'
    numeric_file = 'numeric_{}_{:07}.npy'
    diff_file = 'diff_{}_{:07}.npy'
    steer_file = 'steer_{}_{:07}.npy'
    steer_diff_file = 'steer_diff_{}_{:07}.npy'


class Generator:
    def __init__(self, config, memory_tuple=None, base_path=None, batch_size=32, shuffle=True, column_mode='all', separate_files=False):
        if memory_tuple is not None:
            self.__memory = MemoryMaker(config, memory_tuple)
            self.memory_string = 'n{}_m{}'.format(*memory_tuple)
        else:
            self.__memory = MemoryMaker(config, (config.m_length, config.m_interval))
            self.memory_string = 'n{}_m{}'.format(config.m_length, config.m_interval)

        if base_path is not None:
            self.path = base_path + self.memory_string + '/'
        else:
            self.path = config.path_to_session_files

        self.batch_size = batch_size
        self.shuffle = shuffle
        self.separate_files = separate_files
        self.column_mode = column_mode

        indexes = list(range(0, self.__count_instances()))
        self.train_indexes, self.test_indexes = train_test_split(indexes)

        self.train_batch_count = len(self.train_indexes) // self.batch_size
        self.test_batch_count = len(self.test_indexes) // self.batch_size

    def __count_instances(self):
        return len([fn for fn in os.listdir(self.path) if fn.startswith('frame_')])

    def generate(self, data='train'):
        if data == 'train':
            indexes = self.train_indexes
            batch_count = self.train_batch_count
        elif data == 'test':
            indexes = self.test_indexes
            batch_count = self.test_batch_count
        else:
            raise ValueError

        while True:
            if self.shuffle:
                np.random.shuffle(indexes)

            for i in range(batch_count):
                batch_indexes = indexes[i * self.batch_size:(i + 1) * self.batch_size]
                x_frame, x_numeric, y = self.__load_batch(batch_indexes)

                yield (x_frame, x_numeric), y

    def __load_batch(self, batch_indexes):
        frames = []
        numerics = []
        diffs = []

        for i in batch_indexes:
            frame = np.load(self.path + GenFiles.frame_file.format(self.memory_string, i), allow_pickle=True)

            if self.column_mode == 'steer':
                if self.separate_files:
                    numeric = np.load(self.path + GenFiles.steer_file.format(self.memory_string, i), allow_pickle=True)
                    diff = np.load(self.path + GenFiles.steer_diff_file.format(self.memory_string, i), allow_pickle=True)
                else:
                    numeric = np.load(self.path + GenFiles.numeric_file.format(self.memory_string, i), allow_pickle=True)
                    diff = np.load(self.path + GenFiles.diff_file.format(self.memory_string, i), allow_pickle=True)

                # steering and throttle
                numeric = self.__memory.columns_from_memorized(numeric, (1, 2))
                # steering
                diff = diff[1]
            elif self.column_mode == 'all':
                numeric = np.load(self.path + GenFiles.numeric_file.format(self.memory_string, i), allow_pickle=True)
                diff = np.load(self.path + GenFiles.diff_file.format(self.memory_string, i), allow_pickle=True)
            else:
                raise ValueError

            frames.append(frame)
            numerics.append(numeric)
            diffs.append(diff)

        return np.array(frames), np.array(numerics), np.array(diffs)