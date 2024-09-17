import math

def face_confidence(face_distance, face_match_threshold=1.0):
    ranges = (1.0 - face_match_threshold)
    linear_val = (1.0 - face_distance) / (ranges * 2.0)

    if face_distance > face_match_threshold:
        return str(round(linear_val * 100, 2)) + '%'  # Return confidence as a percentage
    else:
        # Adjust confidence using a non-linear formula
        value = (linear_val + ((1.0 - linear_val) * math.pow((linear_val - 0.5) * 2, 0.2))) * 100
        return str(round(value, 2)) + '%'  # Return adjusted confidence as a percentage