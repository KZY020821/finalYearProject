import face_recognition
import os
import sys
import cv2
import numpy as np
import math
import os
import django
import dlib
import tensorflow as tf
from keras.models import Sequential
from keras.layers import Conv2D
from keras.layers import AveragePooling2D
from keras.layers import Flatten
from keras.layers import Dense
from keras.preprocessing.image import ImageDataGenerator

# Set the DJANGO_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")

# Initialize TensorFlow
tf.compat.v1.disable_eager_execution()

# Initialize Django
django.setup()

# Import Django models

# Define a function to calculate face recognition confidence
def face_confidence(face_distance, face_match_threshold=0.6):
    # Calculate confidence linearly based on face distance
    range = (1.0 - face_match_threshold)
    linear_val = (1.0 - face_distance) / (range * 2.0)

    if face_distance > face_match_threshold:
        return str(round(linear_val * 100, 2)) + '%'  # Return confidence as a percentage
    else:
        # Adjust confidence using a non-linear formula
        value = (linear_val + ((1.0 - linear_val) * math.pow((linear_val - 0.5) * 2, 0.2))) * 100
        return str(round(value, 2)) + '%'  # Return adjusted confidence as a percentage

class FaceRecognition():
    # Initialize class variables
    face_locations = []
    face_encodings = []
    face_names = []
    known_face_encodings = []
    known_face_names = []
    processed_names = set()  # Set to store names that have already been processed
    process_current_frame = True
    face_match_threshold = 0.4
    confidence_threshold = 0.3

    def __init__(self):
        self.encode_faces()  # Call the face encoding function to load known faces
        self.load_qr_code()  # Call the function to load the QR code image

    def encode_faces(self):
        if len(sys.argv) > 1:
            subjectCode = sys.argv[1]
        directory = f'/Users/khorzeyi/code/finalYearProject/media/6700YCOM/'
        files = os.listdir(directory)
        image_files = [file for file in files if file.lower().endswith(('.jpg', '.jpeg', '.png'))]

        # Use the dlib face recognition model (e.g., 'dlib_face_recognition_resnet_model_v1.dat')
        dlib_model_path = '/Users/khorzeyi/code/finalYearProject/dlib_face_recognition_resnet_model_v1.dat'
        dlib_model = dlib.face_recognition_model_v1(dlib_model_path)

        for image in image_files:
            try:
                face_image = face_recognition.load_image_file(os.path.join(directory, image))
                
                # Use the dlib face recognition model
                face_encoding = face_recognition.face_encodings(face_image)[0]

                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(image)
            except Exception as ex:
                print(ex)
        print(self.known_face_names)

    def load_qr_code(self):
        # Load the static QR code image with an alpha channel
        qr_code_image = cv2.imread('/Users/khorzeyi/code/finalYearProject/system/static/assets/img/qrcode.png', cv2.IMREAD_UNCHANGED)
        self.qr_code_alpha_channel = qr_code_image

    def overlay_qr_code(self, frame):
        # Resize QR code image to fit in the bottom right corner
        qr_code_resized = cv2.resize(self.qr_code_alpha_channel, (150, 150))

        # Extract the alpha channel from the resized QR code image
        qr_code_alpha_channel = qr_code_resized[:, :, 3]

        # Create a mask for the QR code alpha channel
        mask = cv2.cvtColor(qr_code_alpha_channel, cv2.COLOR_GRAY2BGR) / 255.0

        # Overlay QR code on the frame at the bottom right corner
        frame[-150:, -150:] = frame[-150:, -150:] * (1 - mask) + qr_code_resized[:, :, :3] * mask

    def eye_aspect_ratio(self, eye):
        # Convert eye landmarks to NumPy array
        eye = np.array(eye, dtype=np.float32)

        # Calculate Euclidean distances between pairs of eye landmarks
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])

        # Calculate Euclidean distance between the horizontal eye landmarks
        C = np.linalg.norm(eye[0] - eye[3])

        # Calculate the eye aspect ratio
        ear = (A + B) / (2 * C)

        return ear

    def liveness_detection(self, landmarks):
        # Extract the left and right eye landmarks
        left_eye = landmarks['left_eye']
        right_eye = landmarks['right_eye']

        # Calculate the eye aspect ratio for both eyes
        left_ear = self.eye_aspect_ratio(left_eye)
        right_ear = self.eye_aspect_ratio(right_eye)

        # Average of the eye aspect ratios for liveness detection
        liveness_value = (left_ear + right_ear) / 2.0

        return liveness_value


    def run_recognition(self):
        # Open the video capture from the default camera (camera index 0)
        video_capture = cv2.VideoCapture(0)

        if not video_capture.isOpened():
            sys.exit('Video source not found....')  # Exit if the video source is not found

        while True:
            ret, frame = video_capture.read()  # Read a frame from the video source

            if self.process_current_frame:
                # Resize the frame for faster face recognition
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = small_frame[:, :, ::-1]  # Convert BGR to RGB

                # Find all faces in the current frame
                self.face_locations = face_recognition.face_locations(rgb_small_frame)
                self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)

                self.face_names = []
                self.overlay_qr_code(frame)
                for face_location, face_encoding in zip(self.face_locations, self.face_encodings):
                    top, right, bottom, left = face_location

                    # Extract facial landmarks
                    landmarks = face_recognition.face_landmarks(rgb_small_frame, [face_location])[0]

                    # Perform liveness detection
                    liveness_value = self.liveness_detection(landmarks)

                    # Check liveness value and perform face recognition only if liveness is detected
                    if liveness_value > 0.2:
                        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                        matches = face_distances <= self.face_match_threshold

                        if any(matches):
                            best_match_index = np.argmin(face_distances)
                            confidence = face_confidence(face_distances[best_match_index], face_match_threshold=0.7)

                            if float(confidence.rstrip('%')) > self.confidence_threshold * 100:
                                name = self.known_face_names[best_match_index]
                                self.face_names.append(f'{name} ({confidence})')
                                if name not in self.processed_names:
                                    self.processed_names.add(f'{name}')
                        else:
                            # Face does not match any known face above the confidence threshold
                            unknown_confidence = face_confidence(np.min(face_distances), face_match_threshold=0.7)
                            if float(unknown_confidence.rstrip('%')) > self.confidence_threshold * 100:
                                self.face_names.append(f'Unknown')

            # Draw rectangles and labels on the frame for recognized faces
            for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)  # Draw a red rectangle around the face
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), -1)  # Draw a label background
                cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8,
                            (255, 255, 255), 1)  # Put the name and confidence label

            cv2.imshow('face recognition', frame)  # Display the frame with face recognition

            if cv2.waitKey(1) == ord('q'):
                print(list(self.processed_names))
                break  # Press 'q' to quit the program

        video_capture.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    fr = FaceRecognition()  # Create an instance of the FaceRecognition class
    fr.run_recognition()  # Run the face recognition process
