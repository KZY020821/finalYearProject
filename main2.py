import math
import os
import sys

import cv2
import django
import face_recognition
import numpy as np

# Set the DJANGO_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")

# Initialize Django
django.setup()


# Import Django models
# Define a function to calculate face recognition confidence
def face_confidence(face_distance, face_match_threshold):
    ranges = (1.0 - face_match_threshold)
    linear_val = (1.0 - face_distance) / (ranges * 2.0)

    if face_distance > face_match_threshold:
        return str(round(linear_val * 100, 2)) + '%' 
    else:
        # Adjust confidence using a non-linear formula
        value = (linear_val + ((1.0 - linear_val) * math.pow((linear_val - 0.5) * 2, 0.2))) * 100
        return str(round(value, 2)) + '%'  # Return adjusted confidence as a percentage


class FaceRecognition:
    # Initialize class variables
    face_locations = []
    face_encodings = []
    face_names = []
    known_face_encodings = []
    known_face_names = []
    processed_names = set()  # Set to store names that have already been processed
    process_current_frame = True
    face_match_threshold = 0.5
    confidence_threshold = 0.5

    def __init__(self):
        self.qr_code_alpha_channel = None
        self.encode_faces()  # Call the face encoding function to load known faces
        self.load_qr_code()  # Call the function to load the QR code image

    def encode_faces(self):
        directory = f'media/zhzy/'
        files = os.listdir(directory)
        image_files = [file for file in files if file.lower().endswith(('.jpg', '.jpeg', '.png'))]

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

        # Overlay QR code on the frame in the bottom right corner
        frame[-150:, -150:] = frame[-150:, -150:] * (1 - mask) + qr_code_resized[:, :, :3] * mask

    def run_recognition(self):
        # Open the video capture from the default camera (camera index 0)
        colour = []
        video_capture = cv2.VideoCapture(1)

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

                    if True in matches:
                        best_match_index = np.argmin(face_distances)
                        confidence = face_confidence(face_distances[best_match_index], self.face_match_threshold)

                        if float(confidence.rstrip('%')) > self.confidence_threshold * 100:
                            name = self.known_face_names[best_match_index]
                            self.face_names.append(f'{name} ({confidence})')
                            if name not in self.processed_names:
                                self.processed_names.add(f'{name}')
                            colour = (124, 252, 0)
                    else:
                        unknown_confidence = face_confidence(np.min(face_distances), self.face_match_threshold)
                        if float(unknown_confidence.rstrip('%')) > self.confidence_threshold * 100:
                            self.face_names.append(f'Unknown')
                        colour = (0, 0, 255)
            # Draw rectangles and labels on the frame for recognized faces
            for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                cv2.rectangle(frame, (left, top), (right, bottom), colour, 2)  # Draw a red rectangle around the face
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), colour, -1)  # Draw a label background
                cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8,
                            (255, 255, 255), 1)  # Put the name and confidence label

            cv2.imshow('face recognition', frame)  # Display the frame with face recognition

            if cv2.waitKey(1) == ord('q'):
                break  # Press 'q' to quit the program

        video_capture.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    fr = FaceRecognition()  # Create an instance of the FaceRecognition class
    fr.run_recognition()  # Run the face recognition process
