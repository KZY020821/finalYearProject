import os
import sys
sys.path.append('/Users/khorzeyi/code/finalYearProject')

# Set the DJANGO_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")

# Initialize Django
import django
django.setup()

import cv2
import face_recognition
import numpy as np
import math
from tqdm import tqdm
from collections import defaultdict
from imutils.video import VideoStream
from eye_status import *
from system.views.admin_views import collect_attendance

processed_names = set()
face_locations = []
face_encodings = []
face_names = []
known_face_encodings = []
known_face_names = []
process_current_frame = True
face_match_threshold = 0.4
confidence_threshold = 0.3
# Set the DJANGO_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")

# Initialize Django
django.setup()

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


def load_qr_code():
    # Load the static QR code image with an alpha channel
    qr_code_image = cv2.imread('/Users/khorzeyi/code/finalYearProject/system/static/assets/img/qrcode.png', cv2.IMREAD_UNCHANGED)
    return qr_code_image

def overlay_qr_code(frame, qr_code_alpha_channel):
    # Resize QR code image to fit in the bottom right corner
    qr_code_resized = cv2.resize(qr_code_alpha_channel, (150, 150))

    # Extract the alpha channel from the resized QR code image
    qr_code_alpha_channel = qr_code_resized[:, :, 3]

    # Create a mask for the QR code alpha channel
    mask = cv2.cvtColor(qr_code_alpha_channel, cv2.COLOR_GRAY2BGR) / 255.0

    # Overlay QR code on the frame at the bottom right corner
    frame[-150:, -150:] = frame[-150:, -150:] * (1 - mask) + qr_code_resized[:, :, :3] * mask

    
def init():
    face_cascPath = '/Users/khorzeyi/code/finalYearProject/face_rec-master/haarcascade_frontalface_alt.xml'
    # face_cascPath = 'lbpcascade_frontalface.xml'

    open_eye_cascPath = '/Users/khorzeyi/code/finalYearProject/face_rec-master/haarcascade_eye_tree_eyeglasses.xml'
    left_eye_cascPath = '/Users/khorzeyi/code/finalYearProject/face_rec-master/haarcascade_lefteye_2splits.xml'
    right_eye_cascPath ='/Users/khorzeyi/code/finalYearProject/face_rec-master/haarcascade_righteye_2splits.xml'
    if len(sys.argv) > 1:
            classCode = sys.argv[1]
    # dataset = f'/Users/khorzeyi/code/finalYearProject/media/{classCode}/'
    dataset = f'/Users/khorzeyi/code/finalYearProject/media/6612YCOM1/'

    face_detector = cv2.CascadeClassifier(face_cascPath)
    open_eyes_detector = cv2.CascadeClassifier(open_eye_cascPath)
    left_eye_detector = cv2.CascadeClassifier(left_eye_cascPath)
    right_eye_detector = cv2.CascadeClassifier(right_eye_cascPath)

    print("[LOG] Opening webcam ...")
    video_capture = VideoStream(src=1).start()

    model = load_model()


    print("[LOG] Collecting images ...")
    images = []
    imageName = []
    for direc, _, files in tqdm(os.walk(dataset)):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                images.append(os.path.join(direc,file))
                imageName.append(file)
    print(imageName)            
    qr_code_alpha_channel = load_qr_code()

    return (model, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, video_capture, images, qr_code_alpha_channel)

def process_and_encode(images):
    # initialize the list of known encodings and known names
    known_encodings = []
    known_names = []
    print("[LOG] Encoding faces ...")

    for image_path in tqdm(images):
        # Load image
        image = cv2.imread(image_path)
        # Convert it from BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
     
        # detect face in the image and get its location (square boxes coordinates)
        boxes = face_recognition.face_locations(image, model='hog')

        # Encode the face into a 128-d embeddings vector
        encoding = face_recognition.face_encodings(image, boxes)

        # the person's name is the name of the folder where the image comes from
        name = image_path.split(os.path.sep)[-1]

        if len(encoding) > 0 : 
            known_encodings.append(encoding[0])
            known_names.append(name)

    known_face_names = known_names
    return {"encodings": known_encodings, "names": known_names, "known_face_names": known_face_names, "face_match_threshold": face_match_threshold, "confidence_threshold": confidence_threshold}

def isBlinking(history, maxFrames):
    """ @history: A string containing the history of eyes status 
         where a '1' means that the eyes were closed and '0' open.
        @maxFrames: The maximal number of successive frames where an eye is closed """
    for i in range(maxFrames):
        pattern = '1' + '0'*(i+1) + '1'
        if pattern in history:
            return True
    return False

def detect_and_display(model, video_capture, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, data, eyes_detected, qr_code_alpha_channel):
    frame = video_capture.read()
    # resize the frame
    frame = cv2.resize(frame, (0, 0), fx=1.0, fy=1.0)
    overlay_qr_code(frame, qr_code_alpha_channel)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(50, 50),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    
    # for each detected face
    for (x, y, w, h) in faces:
        face = frame[y:y + h, x:x + w]
        gray_face = gray[y:y + h, x:x + w]

        eyes = []

        # Extract the person's name
        name = "Unknown"  # Default name if not recognized
        face_encoding = face_recognition.face_encodings(frame, [(y, x + w, y + h, x)])[0]

        # Compare the vector with all known faces encodings
        matches = face_recognition.compare_faces(data["encodings"], face_encoding)

        # If there is at least one match:
        if True in matches:
            matchedIdxs = [i for (i, b) in enumerate(matches) if b]
            counts = {}
            for i in matchedIdxs:
                name = data["names"][i]
                counts[name] = counts.get(name, 0) + 1

            # Determine the recognized face with the largest number of votes
            name = max(counts, key=counts.get)

        eyes_detected[name] += '1'  # Assuming eyes are open by default

        # Eyes detection
        # check first if eyes are open (with glasses taking into account)
        open_eyes_glasses = open_eyes_detector.detectMultiScale(
            gray_face,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        # if open_eyes_glasses detect eyes then they are open
        if len(open_eyes_glasses) == 2:
            eyes_detected[name] += '1'
            for (ex, ey, ew, eh) in open_eyes_glasses:
                cv2.rectangle(face, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

        # otherwise try detecting eyes using left and right_eye_detector
        # which can detect open and closed eyes
        else:
            # separate the face into left and right sides
            left_face = frame[y:y + h, x + int(w / 2):x + w]
            left_face_gray = gray[y:y + h, x + int(w / 2):x + w]

            right_face = frame[y:y + h, x:x + int(w / 2)]
            right_face_gray = gray[y:y + h, x:x + int(w / 2)]

            # Detect the left eye
            left_eye = left_eye_detector.detectMultiScale(
                left_face_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            # Detect the right eye
            right_eye = right_eye_detector.detectMultiScale(
                right_face_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            eye_status = '1'  # we suppose the eyes are open

            # For each eye check whether the eye is closed.
            # If one is closed, we conclude the eyes are closed
            for (ex, ey, ew, eh) in right_eye:
                color = (0, 255, 0)
                pred = predict(right_face[ey:ey + eh, ex:ex + ew], model)
                if pred == 'closed':
                    eye_status = '0'
                    color = (0, 0, 255)
                cv2.rectangle(right_face, (ex, ey), (ex + ew, ey + eh), color, 2)
            for (ex, ey, ew, eh) in left_eye:
                color = (0, 255, 0)
                pred = predict(left_face[ey:ey + eh, ex:ex + ew], model)
                if pred == 'closed':
                    eye_status = '0'
                    color = (0, 0, 255)
                cv2.rectangle(left_face, (ex, ey), (ex + ew, ey + eh), color, 2)
            
            # Display the name and confidence only when eyes are closed (blink detected)
            # Display the name and confidence only when eyes are closed (blink detected)
            if isBlinking(eyes_detected[name], maxFrames=3):
                confidence = face_confidence(0.0)  # You can set the confidence to 0.0 when eyes are closed
                cv2.putText(frame, f'{name} ({confidence})', (x, y - 10), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
            



        # Confidence-based recognition
        # Resize the frame for faster face recognition
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]  # Convert BGR to RGB

        # Find all faces in the current frame
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        overlay_qr_code(frame, qr_code_alpha_channel)
        for face_encoding in face_encodings:
            face_distances = face_recognition.face_distance(data["encodings"], face_encoding)
            matches = face_distances <= data["face_match_threshold"]

            if any(matches):
                best_match_index = np.argmin(face_distances)
                confidence = face_confidence(face_distances[best_match_index], face_match_threshold=0.7)

                if float(confidence.rstrip('%')) > data["confidence_threshold"] * 100:
                    name = data["known_face_names"][best_match_index]
                    face_names.append(f'{name} ({confidence})')
                # Draw rectangles and labels on the frame for recognized faces
                for (top, right, bottom, left), name in zip(face_locations, face_names):
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
                if float(unknown_confidence.rstrip('%')) > data["confidence_threshold"] * 100:
                    face_names.append(f'Unknown')
                # Draw rectangles and labels on the frame for recognized faces
                for (top, right, bottom, left), name in zip(face_locations, face_names):
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4

                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)  # Draw a red rectangle around the face
                    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), -1)  # Draw a label background
                    cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8,
                                (255, 255, 255), 1)  # Put the name and confidence label
    return frame

if __name__ == "__main__":
    (model, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, video_capture, images, qr_code_alpha_channel) = init()
    data = process_and_encode(images)

    eyes_detected = defaultdict(str)
    while True:
        frame = detect_and_display(model, video_capture, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, data, eyes_detected, qr_code_alpha_channel)
        cv2.imshow("Face Liveness Detector", frame)
        if cv2.waitKey(1) == ord('q'):
                print(list(processed_names))
                # if len(sys.argv) > 1:
                #     classCode = sys.argv[1]
                #     creator = sys.argv[2]
                # collect_attendance(list(processed_names), classCode, creator)
                break  # Press 'q' to quit the program
    cv2.destroyAllWindows()
    video_capture.stop()