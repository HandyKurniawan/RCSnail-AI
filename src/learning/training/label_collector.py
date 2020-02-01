from src.learning.training.car_mapping import CarMapping


class LabelCollector:
    def __init__(self):
        self.__mapping = CarMapping()

    def collect_numeric_inputs(self, telemetry_df):
        return telemetry_df[self.numeric_columns()]

    def collect_expert_labels(self, telemetry_df):
        return telemetry_df[self.diff_columns()]

    def numeric_columns(self):
        return [
            self.__mapping.gear,
            self.__mapping.steering,
            self.__mapping.throttle,
            self.__mapping.braking
        ]

    def diff_columns(self):
        return [
            self.__mapping.d_gear,
            self.__mapping.d_steering,
            self.__mapping.d_throttle,
            self.__mapping.d_braking
        ]

    def steering_columns(self):
        return [
            self.__mapping.steering,
            self.__mapping.throttle
        ]

    def diff_steering_columns(self):
        return [
            self.__mapping.d_steering
        ]
