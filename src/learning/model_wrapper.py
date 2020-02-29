import os
import datetime
import numpy as np
from commons.car_controls import CarControlUpdates

from src.learning.models import create_mlp, create_cnn, create_multi_model, create_cnn_alone
from src.learning.training.car_mapping import CarMapping
from src.utilities.memory_maker import MemoryMaker


class ModelWrapper:
    def __init__(self, config, numeric_shape=(4,), output_shape=1, memory_tuple=None, model_num=None):
        if memory_tuple is not None:
            self.memory_length, self.memory_interval = memory_tuple
        else:
            self.memory_length = config.m_length
            self.memory_interval = config.m_interval

        if model_num is None:
            model_num = config.model_num

        self.__path_to_models = config.path_to_models
        self.__memory = MemoryMaker(config, memory_tuple=memory_tuple)
        self.__prediction_mode = config.prediction_mode

        self.__frames_shape = (config.frame_height, config.frame_width, 3 * self.memory_length)
        self.__numeric_shape = (1 * self.memory_length,)
        self.__output_shape = output_shape

        # TODO split models to steering, throttle & gear models
        if config.pretrained_start:
            model_name = 'model_n{}_m{}_{}.h5'.format(self.memory_length, self.memory_interval, model_num)
            if os.path.isfile(self.__path_to_models + model_name):
                self.model = self.__load_model(model_name)
            else:
                raise ValueError('Model not found!')
        else:
            self.model = self.__create_new_model()

        self.model.summary()
        self.__mapping = CarMapping()

    def __create_new_model(self):
        return create_cnn_alone(input_shape=self.__frames_shape, output_shape=self.__output_shape)

    def __load_model(self, model_filename: str):
        from tensorflow.keras.models import load_model
        print("Loaded " + model_filename)
        return load_model(self.__path_to_models + model_filename)

    def save_model(self, model_filename: str):
        self.model.save(self.__path_to_models + model_filename + ".h5")
        print("Model has been saved to {} as {}.h5".format(self.__path_to_models, model_filename))

    def fit(self, generator, epochs=1, verbose=1):
        try:
            # TODO might need separate generate (with_numeric) method support
            self.model.fit(generator.generate(data='train'),
                           steps_per_epoch=generator.train_batch_count,
                           validation_data=generator.generate(data='test'),
                           validation_steps=generator.test_batch_count,
                           epochs=epochs, verbose=verbose)
        except Exception as ex:
            print("Generator training exception: {}".format(ex))

    def predict(self, mem_frame, mem_telemetry):
        # prediction from frame and steering
        mem_steering = self.__memory.columns_from_memorized(mem_telemetry, columns=(1,))
        predictions = self.model.predict([mem_frame[np.newaxis, :], mem_steering[np.newaxis, :]])

        return self.updates_from_prediction(predictions)

    def updates_from_prediction(self, prediction):
        prediction_values = prediction.tolist()[0]

        return CarControlUpdates(1, prediction_values[0], prediction_values[1], 0.0, self.__prediction_mode)


def get_model_file_name(path_to_models: str):
    date = datetime.datetime.today().strftime("%Y_%m_%d")
    models_from_same_date = list(filter(lambda file: date in file, os.listdir(path_to_models)))

    return date + "_model_" + str(int(len(models_from_same_date) + 1))
