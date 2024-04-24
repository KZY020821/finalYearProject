import os
import re
import sys
from json import load
current_file_path = os.path.abspath(__file__)
base_path = os.path.dirname(os.path.dirname(current_file_path))
sys.path.append(base_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")
import django
django.setup()
from json import load
import cv2
from face_recognition import face_encodings, face_distance
from collections import defaultdict
from imutils.video import VideoStream
from eye_status import *
from system.models import UserProfile
from system.models import ClassTable
from system.views.lecturer_views import collect_attendance

processed_names = []
if len(sys.argv) > 1:
    classCode = sys.argv[1]
    creator = sys.argv[2]

def init():
    face_detector = cv2.CascadeClassifier('face_rec-master/haarcascade_frontalface_alt.xml')
    open_eyes_detector = cv2.CascadeClassifier('face_rec-master/haarcascade_eye_tree_eyeglasses.xml')
    left_eye_detector = cv2.CascadeClassifier('face_rec-master/haarcascade_lefteye_2splits.xml')
    right_eye_detector = cv2.CascadeClassifier('face_rec-master/haarcascade_righteye_2splits.xml')
    model = load_model()
    video_capture = VideoStream(src=1).start()
    return (model, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, video_capture)

def process_and_encode():
    dataset = f'media/zhzy/'
    known_face_names = []
    known_face_encodings = []
    user_ids = []
    kelas = ClassTable.objects.get(classCode=classCode)
    classes = kelas.intakeTables.all()
    users = UserProfile.objects.all()
    for user in users:
        if user.intakeCode in classes:
            user_ids.append(user.userId)

    for filename in os.listdir(dataset):
        if filename.lower().endswith(('.json')):
            user_id = filename.split('_')[0]
            filepath = os.path.join(dataset, filename)
            with open(filepath, 'r') as f:
                if user_id in user_ids:
                    data = load(f)
                    known_face_encodings.append(data['face_encoding'])
                    name = filename.split('_')[1]
                    name = name.split('.')[0]
                    cleaned_name = name.replace('-', ' ')
                    status = ('ID: ' + user_id + '  Name: ' + cleaned_name)
                    known_face_names.append(status)

    print("filtered faces")
    print(known_face_names)
    return {"encodings": known_face_encodings, "names": known_face_names}

def isBlinking(history, maxFrames):
    for i in range(maxFrames):
        pattern = '1' + '0' * (i + 1) + '1'
        if pattern in history:
            return True
    return False

def detect_and_display(model, video_capture, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, data, eyes_detected, face_match_threshold):
    frame = video_capture.read()
    frame = cv2.resize(frame, (0, 0), fx=1.0, fy=1.0)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.2,
        minNeighbors=5,
        minSize=(50, 50),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    for (x, y, w, h) in faces:
        encoding = face_encodings(rgb, [(y, x + w, y + h, x)])[0]
        face_distances = face_distance(data["encodings"], encoding)
        matches = face_distances <= face_match_threshold
        name = "Unknown"
        if any(matches):
            best_match_index = np.argmin(face_distances)
            name = data["names"][best_match_index]

        face = frame[y:y + h, x:x + w]
        gray_face = gray[y:y + h, x:x + w]

        open_eyes_glasses = open_eyes_detector.detectMultiScale(
            gray_face,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        if len(open_eyes_glasses) == 2:
            eyes_detected[name] += '1'
            for (ex, ey, ew, eh) in open_eyes_glasses:
                cv2.rectangle(face, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)
        else:
            left_face = frame[y:y + h, x + int(w / 2):x + w]
            left_face_gray = gray[y:y + h, x + int(w / 2):x + w]

            right_face = frame[y:y + h, x:x + int(w / 2)]
            right_face_gray = gray[y:y + h, x:x + int(w / 2)]

            left_eye = left_eye_detector.detectMultiScale(
                left_face_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            right_eye = right_eye_detector.detectMultiScale(
                right_face_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            eye_status = '1' 

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

        if isBlinking(eyes_detected[name], 3):
            if name != "Unknown":
                colour = (0, 255, 0)
            else:
                colour =  (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), colour, 2)
            y = y - 15 if y - 15 > 15 else y + 15
            cv2.putText(frame, name, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, colour, 2)
                
            if name not in processed_names:
                if name != 'Unknown':
                    processed_names.append(f'{name}')
    return frame


if __name__ == "__main__":
    (model, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, video_capture) = init()
    data = process_and_encode()
    eyes_detected = defaultdict(str)
    while True:
        frame = detect_and_display(model, video_capture, face_detector, open_eyes_detector, left_eye_detector,right_eye_detector, data, eyes_detected, 0.5)
        cv2.imshow(f"BOLT-FRAS Face Recognition Attendance System", frame)
        if cv2.waitKey(1) == ord('q'):
            ids = []

            for string in processed_names:
                # Use regex to find the ID pattern
                match = re.search(r'ID: (\w+)', string)

                if match:
                    # Extract the ID from the regex match
                    id_value = match.group(1)
                    ids.append(id_value)
            collect_attendance(ids, classCode, creator)
            break  # Press 'q' to quit the program
    cv2.destroyAllWindows()
    video_capture.stop()
