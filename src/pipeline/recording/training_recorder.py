
import numpy as np
import cv2


class TrainingRecorder:
    def __init__(self, training_session, resolution=(60, 40), fps=20.0):
        self.training_session = training_session
        self.resolution = resolution
        self.fps = fps

        self.session_frames = []
        self.session_telemetry = []

    def record(self, frame, telemetry):
        self.session_frames.append(frame)
        self.session_telemetry.append(telemetry)

    def save_session(self):
        session_length = len(self.session_telemetry)
        assert session_length == len(self.session_frames), "Video and telemetry sizes are not identical"
        print("Number of training instances to be saved: " + str(session_length))

        with open(self.training_session + '.csv', 'w') as file:
            out = cv2.VideoWriter(self.training_session + ".avi",
                                  cv2.VideoWriter_fourcc(*'DIVX'),
                                  self.fps,
                                  self.resolution)

            for i in range(session_length):
                if self.session_telemetry[i] is not None and self.session_frames[i] is not None:
                    file.write(str(self.session_telemetry[i]) + "\n")
                    out.write(np.array(self.session_frames[i]))

            out.release()
        print("Telemetry and video saved successfully.")
