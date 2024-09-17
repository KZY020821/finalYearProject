
import os
import sys

import cv2
import face_recognition
import numpy as np

from methods import face_confidence

class FaceRecognition:
    # Initialize class variables
    face_locations = []
    face_encodings = []
    face_names = []
    known_face_encodings = []
    known_face_names = []
    processed_names = set()  # Set to store names that have already been processed
    process_current_frame = True
    face_match_threshold = 0.8
    confidence_threshold = 0.8

    def __init__(self):

        self.encode_faces()  # Call the face encoding function to load known faces

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

    def run_recognition(self):
        # Open the video capture from the default camera (camera index 0)
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
                for face_encoding in self.face_encodings:
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    matches = face_distances <= self.face_match_threshold

                    if True in matches:
                        best_match_index = np.argmin(face_distances)
                        confidence = face_confidence(face_distances[best_match_index], face_match_threshold=0.8)

                        if float(confidence.rstrip('%')) > self.confidence_threshold * 100:
                            name = self.known_face_names[best_match_index]
                            self.face_names.append(f'{name}')
                            if name not in self.processed_names:
                                self.processed_names.add(f'{name}')

                            for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
                                top *= 4
                                right *= 4
                                bottom *= 4
                                left *= 4

                                cv2.rectangle(frame, (left, top), (right, bottom), (124,252,0),
                                              2)  # Draw a red rectangle around the face
                                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (124,252,0),
                                              -1)  # Draw a label background
                                cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8,
                                            (255, 255, 255), 1)  # Put the name and confidence label
                    else:
                        self.face_names.append(f'Unknown')

                        # Draw rectangles and labels on the frame for recognized faces
                        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
                            top *= 4
                            right *= 4
                            bottom *= 4
                            left *= 4

                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255),
                                          2)  # Draw a red rectangle around the face
                            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), -1)  # Draw a label background
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
