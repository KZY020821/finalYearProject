import os
import sys
current_file_path = os.path.abspath(__file__)
base_path = os.path.dirname(os.path.dirname(current_file_path))
sys.path.append(base_path)
import cv2
import face_recognition
from tqdm import tqdm
from collections import defaultdict
from imutils.video import VideoStream
from eye_status import *

processed_names = []
def load_qr_code():
    qr_code_image = cv2.imread('system/static/assets/img/qrcode.png', cv2.IMREAD_UNCHANGED)
    return qr_code_image

def overlay_qr_code(frame, qr_code_alpha_channel):
    qr_code_resized = cv2.resize(qr_code_alpha_channel, (150, 150))
    qr_code_alpha_channel = qr_code_resized[:, :, 3]
    mask = cv2.cvtColor(qr_code_alpha_channel, cv2.COLOR_GRAY2BGR) / 255.0
    frame[-150:, -150:] = frame[-150:, -150:] * (1 - mask) + qr_code_resized[:, :, :3] * mask

def init():
    face_detector = cv2.CascadeClassifier('face_rec-master/haarcascade_frontalface_alt.xml')
    open_eyes_detector = cv2.CascadeClassifier('face_rec-master/haarcascade_eye_tree_eyeglasses.xml')
    left_eye_detector = cv2.CascadeClassifier('face_rec-master/haarcascade_lefteye_2splits.xml')
    right_eye_detector = cv2.CascadeClassifier('face_rec-master/haarcascade_righteye_2splits.xml')

    dataset = f'media/faceImage/'
    images = []
    for direc, _, files in tqdm(os.walk(dataset)):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):    
                images.append(os.path.join(direc, file))

    qr_code_alpha_channel = load_qr_code()  
    model = load_model()
    video_capture = VideoStream(src=1).start()
    return (model, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, video_capture, images, qr_code_alpha_channel)

def process_and_encode(images):
    known_face_names = []
    known_face_encodings = []
    for image in images:
        try:
            face_image = face_recognition.load_image_file(image)
            face_encoding = face_recognition.face_encodings(face_image, model='large')[0]

            known_face_encodings.append(face_encoding)
            file_name = os.path.basename(image)
            user_id = file_name.split('_')[0]
            name = file_name.split('_')[1]
            name = name.split('.')[0]
            cleaned_name = name.replace('-', ' ')
            status = ('ID: ' + user_id + '  Name: ' + cleaned_name)
            known_face_names.append(status)
        
        except Exception as ex:
            print(ex)
    return {"encodings": known_face_encodings, "names": known_face_names}

def isBlinking(history, maxFrames):
    for i in range(maxFrames):
        pattern = '1' + '0' * (i + 1) + '1'
        if pattern in history:
            return True
    return False

def detect_and_display(model, video_capture, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, data, eyes_detected, qr_code_alpha_channel, face_match_threshold):
    frame = video_capture.read()
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
        encoding = face_recognition.face_encodings(rgb, [(y, x + w, y + h, x)])[0]
        face_distances = face_recognition.face_distance(data["encodings"], encoding)
        matches = face_distances <= face_match_threshold
        name = "Unknown"
        if any(matches):
            best_match_index = np.argmin(face_distances)
            name = data["names"][best_match_index]

        face = frame[y:y + h, x:x + w]
        gray_face = gray[y:y + h, x:x + w]

        eyes = []
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
    (model, face_detector, open_eyes_detector, left_eye_detector, right_eye_detector, video_capture, images, qr_code_alpha_channel) = init()
    data = process_and_encode(images)
    eyes_detected = defaultdict(str)
    while True:
        frame = detect_and_display(model, video_capture, face_detector, open_eyes_detector, left_eye_detector,right_eye_detector, data, eyes_detected, qr_code_alpha_channel, 0.7)
        cv2.imshow(f"BOLT-FRAS Face Recognition Attendance System", frame)
        if cv2.waitKey(1) == ord('q'):
            break 
    cv2.destroyAllWindows()
    video_capture.stop()