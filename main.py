import face_recognition
import os, sys
import cv2
import numpy as np
import math
import os
import django

# Set the DJANGO_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")

# Initialize Django
django.setup()

# Import Django models
from system.models import Attendance as attendanceModel

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

class FaceRecognition:
    # Initialize class variables
    face_locations = []
    face_encodings = []
    face_names = []
    known_face_encodings = []
    known_face_names = []
    processed_names = set()  # Set to store names that have already been processed
    process_current_frame = True

    def __init__(self):
        self.encode_faces()  # Call the face encoding function to load known faces

    def encode_faces(self):
        # Specify the directory path where known face images are stored
        directory = '/Users/khorzeyi/code/finalYearProject/media/faceImage/'

        # List all files in the directory
        files = os.listdir(directory)

        # Filter out only image files (jpg, jpeg, png)
        image_files = [file for file in files if file.lower().endswith(('.jpg', '.jpeg', '.png'))]

        # Loop through image files and encode known faces
        for image in image_files:
            face_image = face_recognition.load_image_file(f'/Users/khorzeyi/code/finalYearProject/media/faceImage/{image}')
            face_encoding = face_recognition.face_encodings(face_image)[0]

            self.known_face_encodings.append(face_encoding)
            self.known_face_names.append(image)
        print(self.known_face_names)  # Print the names of known faces

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

                for face_encoding in self.face_encodings:
                    # Compare faces with known faces and find the best match
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                    name = "Unknown"
                    confidence = "Unknown"

                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    best_matches_index = np.argmin(face_distances)

                    if matches[best_matches_index]:
                        full_name = self.known_face_names[best_matches_index]
                        name, _ = full_name.split('_') 
                        confidence = face_confidence(face_distances[best_matches_index])
                        self.face_names.append(f'{name} ({confidence})')
                        if name not in self.processed_names:
                            self.save_attendance(f'{name}')
                            self.processed_names.add(f'{name}')

            self.process_current_frame = not self.process_current_frame

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
                break  # Press 'q' to quit the program

        video_capture.release()
        cv2.destroyAllWindows()

    def save_attendance(self, name):            
        try:
            attendance = attendanceModel(name=name)
            attendance.save()
        except Exception as e:
            print(f"Error saving attendance: {str(e)}")


if __name__ == '__main__':
    fr = FaceRecognition()  # Create an instance of the FaceRecognition class
    fr.run_recognition()  # Run the face recognition process
