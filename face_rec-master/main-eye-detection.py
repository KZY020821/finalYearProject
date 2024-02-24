import face_recognition
import os, sys
import cv2
import numpy as np
import math
import dlib
import datetime
from PIL import Image

import os
import sys
sys.path.append('/Users/khorzeyi/code/finalYearProject')

# Set the DJANGO_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")

# Initialize Django
import django
django.setup()
from tqdm import tqdm
from collections import defaultdict
from imutils.video import VideoStream
from eye_status import *

# Import Django models
from system.views.admin_views import collect_attendance
# Define a function to calculate face recognition confidence
def face_confidence(face_distance, face_match_threshold=0.4):
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
        face_cascPath = '/Users/khorzeyi/code/finalYearProject/face_rec-master/haarcascade_frontalface_alt.xml'
        # face_cascPath = 'lbpcascade_frontalface.xml'

        open_eye_cascPath = '/Users/khorzeyi/code/finalYearProject/face_rec-master/haarcascade_eye_tree_eyeglasses.xml'
        left_eye_cascPath = '/Users/khorzeyi/code/finalYearProject/face_rec-master/haarcascade_lefteye_2splits.xml'
        right_eye_cascPath ='/Users/khorzeyi/code/finalYearProject/face_rec-master/haarcascade_righteye_2splits.xml'
        self.face_detector = cv2.CascadeClassifier(face_cascPath)
        self.open_eyes_detector = cv2.CascadeClassifier(open_eye_cascPath)
        self.left_eye_detector = cv2.CascadeClassifier(left_eye_cascPath)
        self.right_eye_detector = cv2.CascadeClassifier(right_eye_cascPath)
        model = load_model()
        self.encode_faces()  # Call the face encoding function to load known faces
        self.load_qr_code()  # Call the function to load the QR code image

    def encode_faces(self):
        # if len(sys.argv) > 1:
        #     classCode = sys.argv[1]
        directory = f'/Users/khorzeyi/code/finalYearProject/media/6612YCOM1/'
        files = os.listdir(directory)
        image_files = [file for file in files if file.lower().endswith(('.jpg', '.jpeg', '.png'))]

        # Use the dlib face recognition model (e.g., 'dlib_face_recognition_resnet_model_v1.dat')
        dlib_model_path = 'dlib_face_recognition_resnet_model_v1.dat'
        dlib_model = dlib.face_recognition_model_v1(dlib_model_path)

        for image in image_files:
            try:
                face_image = face_recognition.load_image_file(os.path.join(directory, image))
                
                # Use the dlib face recognition model
                face_encoding = face_recognition.face_encodings(face_image, model='large')[0]

                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(image)
            except Exception as ex:
                print(ex)
        print(self.known_face_names)

    def isBlinking(history, maxFrames):
        """ @history: A string containing the history of eyes status 
            where a '1' means that the eyes were closed and '0' open.
            @maxFrames: The maximal number of successive frames where an eye is closed """
        for i in range(maxFrames):
            pattern = '1' + '0'*(i+1) + '1'
            if pattern in history:
                return True
        return False

    def load_qr_code(self):
        # Load the static QR code image with alpha channel
        qr_code_image = cv2.imread('system/static/assets/img/qrcode.png', cv2.IMREAD_UNCHANGED)
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
                for face_encoding in self.face_encodings:
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
                        # Draw rectangles and labels on the frame for recognized faces
                        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
                            top *= 4
                            right *= 4
                            bottom *= 4
                            left *= 4

                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)  # Draw a red rectangle around the face
                            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), -1)  # Draw a label background
                            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8,
                                        (255, 255, 255), 1)  # Put the name and confidence label
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
                if len(sys.argv) > 1:
                    classCode = sys.argv[1]
                    creator = sys.argv[2]
                collect_attendance(list(self.processed_names), classCode, creator)
                break  # Press 'q' to quit the program

        video_capture.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    fr = FaceRecognition()  # Create an instance of the FaceRecognition class
    fr.run_recognition()  # Run the face recognition process
