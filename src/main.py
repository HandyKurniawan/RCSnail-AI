import os
import datetime
import asyncio
import logging
import signal
import numpy as np
import zmq
from zmq.asyncio import Context

from commons.common_zmq import recv_array_with_json, initialize_synced_sub, initialize_synced_pub
from commons.configuration_manager import ConfigurationManager

from learning.model_wrapper import ModelWrapper
from learning.training.training_transformer import TrainingTransformer
from utilities.recorder import Recorder


async def main_dagger(context: Context):
    config_manager = ConfigurationManager()
    config = config_manager.config
    recorder = Recorder(config)
    transformer = TrainingTransformer()

    data_queue = context.socket(zmq.SUB)
    controls_queue = context.socket(zmq.PUB)

    try:
        model = ModelWrapper(config)
        data_count = 0
        dagger_iteration = 0

        await initialize_synced_sub(context, data_queue, config.data_queue_port)
        await initialize_synced_pub(context, controls_queue, config.controls_queue_port)

        while True:
            frame, data = await recv_array_with_json(queue=data_queue)
            telemetry, expert_actions = data
            recorder.record_expert(frame, telemetry, expert_actions)

            data_count += 1

            if data_count % 200 == 0:
                print(data_count)
                await fitting_model(model, recorder, transformer)
                dagger_iteration += 1

            try:
                expert_probability = np.exp(-0.5 * dagger_iteration)
                model_probability = np.random.random()
                if model_probability > expert_probability:
                    prediction = model.predict(frame, telemetry)
                else:
                    prediction = expert_actions

                controls_queue.send_json(prediction.to_dict())
            except Exception as ex:
                print("Dagger predicting exception: {}".format(ex))
    finally:
        data_queue.close()
        controls_queue.close()

        if recorder is not None:
            recorder.save_session()


async def main(context: Context):
    config_manager = ConfigurationManager()
    config = config_manager.config
    recorder = Recorder(config)
    transformer = TrainingTransformer()

    data_queue = context.socket(zmq.SUB)
    controls_queue = context.socket(zmq.PUB)

    try:
        model = ModelWrapper(config)
        turbo_count = 0

        await initialize_synced_sub(context, data_queue, config.data_queue_port)
        await initialize_synced_pub(context, controls_queue, config.controls_queue_port)

        while True:
            frame, telemetry = await recv_array_with_json(queue=data_queue)
            recorder.record(frame, telemetry)

            turbo_count += 1

            if turbo_count % 500 == 0:
                print(turbo_count)
                await fitting_model(model, recorder, transformer)

            try:
                prediction = model.predict(frame, telemetry)
                controls_queue.send_json(prediction.to_dict())
            except Exception as ex:
                print("Predicting exception: {}".format(ex))
    finally:
        data_queue.close()
        controls_queue.close()

        if recorder is not None:
            recorder.save_session()


async def fitting_model(model, recorder, transformer):
    logging.info("fitting")
    try:
        frames, telemetry, expert_actions = recorder.get_current_data()
        print(len(frames))

        train, test = transformer.transform_aggregation_to_inputs(frames, telemetry, expert_actions)
        model.fit(train, test)
        logging.info("fitting done")
    except Exception as ex:
        print("Fitting exception: {}".format(ex))


def cancel_tasks(loop):
    for task in asyncio.Task.all_tasks(loop):
        task.cancel()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, cancel_tasks, loop)
    loop.add_signal_handler(signal.SIGTERM, cancel_tasks, loop)

    context = zmq.asyncio.Context()
    try:
        loop.run_until_complete(main_dagger(context))
    except Exception as ex:
        logging.error("Base interruption: {}".format(ex))
    finally:
        loop.close()
        context.destroy()
