import os
import re
import sys
# Get the absolute path of the current file
current_file_path = os.path.abspath(__file__)

# Go up two levels to get the base directory
base_path = os.path.dirname(os.path.dirname(current_file_path))

# Add the base path to sys.path
sys.path.append(base_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")
import django

django.setup()

import cv2
import face_recognition
from tqdm import tqdm
from collections import defaultdict
from imutils.video import VideoStream
from eye_status import *
from system.models import UserProfile
from system.models import ClassTable
from system.views.admin_views import collect_attendance

processed_names = []


def load_qr_code():
    qr_code_image = cv2.imread('system/static/assets/img/qrcode.png',
                               cv2.IMREAD_UNCHANGED)
    return qr_code_image


def overlay_qr_code(frame, qr_code_alpha_channel):
    qr_code_resized = cv2.resize(qr_code_alpha_channel, (150, 150))
    qr_code_alpha_channel = qr_code_resized[:, :, 3]
    mask = cv2.cvtColor(qr_code_alpha_channel, cv2.COLOR_GRAY2BGR) / 255.0
    frame[-150:, -150:] = frame[-150:, -150:] * (1 - mask) + qr_code_resized[:, :, :3] * mask


def init():
    global classCode
    face_cascPath = 'face_rec-master/haarcascade_frontalface_alt.xml'
    open_eye_cascPath = 'face_rec-master/haarcascade_eye_tree_eyeglasses.xml'
    left_eye_cascPath = 'face_rec-master/haarcascade_lefteye_2splits.xml'
    right_eye_cascPath = 'face_rec-master/haarcascade_righteye_2splits.xml'
    dataset = f'media/faceImage/'

    face_detector = cv2.CascadeClassifier(face_cascPath)
    open_eyes_detector = cv2.CascadeClassifier(open_eye_cascPath)
    left_eye_detector = cv2.CascadeClassifier(left_eye_cascPath)
    right_eye_detector = cv2.CascadeClassifier(right_eye_cascPath)

    images = []
    user_ids = []
    if len(sys.argv) > 1:
        classCode = sys.argv[1]

    classCoder = classCode
    kelas = ClassTable.objects.get(classCode=classCoder)
    classes = kelas.intakeTables.all()
    users = UserProfile.objects.all()
    for user in users:
        if user.intakeCode in classes:
            user_ids.append(user.userId)

    for direc, _, files in tqdm(os.walk(dataset)):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                file_parts = file.split('_')
                user_id = file_parts[0]
                if user_id in user_ids:
                    images.append(os.path.join(direc, file))

    print("[LOG] Opening webcam ...")
    video_capture = VideoStream(src=1).start()

    model = load_model()
    qr_code_alpha_channel = load_qr_code()

    return (model, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, video_capture, images,
            qr_code_alpha_channel)


def process_and_encode(images):
    known_face_names = []
    known_full_names = []
    known_face_encodings = []
    for image in images:
        try:
            face_image = face_recognition.load_image_file(image)

            # Use the dlib face recognition model
            face_encoding = face_recognition.face_encodings(face_image, model='large')[0]

            known_face_encodings.append(face_encoding)
            file_name = os.path.basename(image)
            user_id = file_name.split('_')[0]
            name = file_name.split('_')[1]
            name = name.split('.')[0]
            cleaned_name = name.replace('-', ' ')
            status = ('ID: ' + user_id + '  Name: ' + cleaned_name)
            full_name = (cleaned_name +" Your attendance has been taken")
            known_face_names.append(status)
            known_full_names.append(full_name)
        except Exception as ex:
            print(ex)

    return {"encodings": known_face_encodings, "names": known_face_names, "statuses":known_full_names}


def isBlinking(history, maxFrames):
    """ @history: A string containing the history of eyes status
         where a '1' means that the eyes were closed and '0' open.
        @maxFrames: The maximal number of successive frames where an eye is closed """
    for i in range(maxFrames):
        pattern = '1' + '0' * (i + 1) + '1'
        if pattern in history:
            return True
    return False


def detect_and_display(model, video_capture, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector,
                       data, eyes_detected, qr_code_alpha_channel, face_match_threshold):
    frame = video_capture.read()
    # resize the frame
    frame = cv2.resize(frame, (0, 0), fx=1.0, fy=1.0)
    overlay_qr_code(frame, qr_code_alpha_channel)

    text = "Blink your eye to take attendance"
    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

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
        # Encode the face into a 128-d embeddings vector
        # Encode the face into a 128-d embeddings vector
        # Encode the face into a 128-d embeddings vector
        encoding = face_recognition.face_encodings(rgb, [(y, x + w, y + h, x)])[0]

        # Face distances for the current encoding
        face_distances = face_recognition.face_distance(data["encodings"], encoding)
        matches = face_distances <= face_match_threshold

        # For now, we don't know the person name
        name = "Unknown"

        # If there is at least one match:
        if True in matches:
            matchedIdxs = [i for (i, b) in enumerate(matches) if b]
            counts = {}
            for i in matchedIdxs:
                name = data["names"][i]
                status = data["statuses"][i]
                counts[name] = counts.get(name, 0) + 1

            # Determine the recognized face with the largest number of votes
            name = max(counts, key=counts.get)

        face = frame[y:y + h, x:x + w]
        gray_face = gray[y:y + h, x:x + w]

        eyes = []

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

            # For each eye check wether the eye is closed.
            # If one is closed we conclude the eyes are closed
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
            eyes_detected[name] += eye_status

        # Each time, we check if the person has blinked
        # If yes, we display its name
        if isBlinking(eyes_detected[name], 3):
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # Display name
            y = y - 15 if y - 15 > 15 else y + 15
            cv2.putText(frame, name, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
            
            bottom_left_corner = (10, frame.shape[0] - 10)
            cv2.putText(frame, status, bottom_left_corner, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            if name not in processed_names:
                if name != 'Unknown':
                    processed_names.append(f'{name}')
    return frame


if __name__ == "__main__":
    (model, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, video_capture, images,
     qr_code_alpha_channel) = init()
    data = process_and_encode(images)

    eyes_detected = defaultdict(str)
    processed_names = []
    while True:
        frame = detect_and_display(model, video_capture, face_detector, open_eyes_detector, left_eye_detector,
                                   right_eye_detector, data, eyes_detected, qr_code_alpha_channel, 0.3)
        cv2.imshow("BOLT-FRAS Face Recognition Attendance System", frame)
        if cv2.waitKey(1) == ord('q'):
            ids = []

            for string in processed_names:
                # Use regex to find the ID pattern
                match = re.search(r'ID: (\w+)', string)

                if match:
                    # Extract the ID from the regex match
                    id_value = match.group(1)
                    ids.append(id_value)

            if len(sys.argv) > 1:
                classCode = sys.argv[1]
                creator = sys.argv[2]
            collect_attendance(ids, classCode, creator)
            break  # Press 'q' to quit the program
    cv2.destroyAllWindows()
    video_capture.stop()
