import numpy as np

from src.utilities.car_controls import CarControls, CarControlDiffs


class DataInterceptor:
    def __init__(self, resolution=(60, 40), model=None, recorder=None, aggregated_recording=False):
        self.renderer = None
        self.training_recorder = recorder
        self.resolution = resolution
        self.model = model

        self.frame = None
        self.telemetry = None
        self.expert_actions = None
        self.expert_controls = CarControlDiffs(0, 0.0, 0.0, 0.0)
        self.predicted_diffs = None

        self.recording_enabled = self.training_recorder is not None and not aggregated_recording
        self.aggregation_enabled = self.training_recorder is not None and aggregated_recording

    def set_renderer(self, renderer):
        self.renderer = renderer

    def intercept_frame(self, frame):
        self.renderer.handle_new_frame(frame)

        if frame is not None:
            self.frame = self.__convert_frame(frame)

            if self.recording_enabled:
                self.__record_state()
            elif self.aggregation_enabled:
                self.__record_state_with_expert()

    def intercept_telemetry(self, telemetry):
        self.telemetry = telemetry

    def __convert_frame(self, frame):
        return np.array(frame.to_image().resize(self.resolution))

    def __record_state(self):
        self.training_recorder.record(self.frame, self.telemetry)

    def __record_state_with_expert(self):
        self.training_recorder.record_expert(self.frame, self.telemetry, self.expert_actions)

    async def car_update_override(self, car):
        self.expert_controls = CarControlDiffs(car.gear, car.d_steering, car.d_throttle, car.d_braking)
        print(self.expert_controls.d_steering)
        print(self.telemetry["sa"])

        if self.aggregation_enabled:
            # TODO implement dagger Pi_i training here
            self.update_car_from_predictions(car)
        else:
            self.update_car_from_predictions(car)

    def update_car_from_predictions(self, car):
        if self.frame is not None and self.telemetry is not None:
            self.predicted_diffs = self.model.predict(self.frame, self.telemetry)

            if self.predicted_diffs is not None:
                car.gear = self.predicted_diffs.gear
                car.diff_update_steering(self.predicted_diffs.d_steering)
                car.diff_update_linear_movement(self.predicted_diffs.d_throttle, self.predicted_diffs.d_braking)
