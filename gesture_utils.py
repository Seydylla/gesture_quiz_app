# gesture_utils.py
import mediapipe as mp
import time

mp_hands = mp.solutions.hands
mp_face = mp.solutions.face_detection

class GestureDetector:
    def __init__(self):
        # Initialize Mediapipe Hands and FaceDetection models
        self.hands = mp_hands.Hands(min_detection_confidence=0.7)
        self.faces = mp_face.FaceDetection(min_detection_confidence=0.7)
        self.cheating_start = None  # Timestamp when cheating condition first detected
        self.cheating_flag = False  # Flag to indicate if cheating is currently detected
        self.cheating_detected_time = 0 # To track how long cheating has been detected

    def detect(self, frame):
        import cv2
        # Convert the frame from BGR to RGB, as Mediapipe models expect RGB input
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame to detect hands and faces
        hands_result = self.hands.process(frame_rgb)
        faces_result = self.faces.process(frame_rgb)

        # Count the number of hands and faces detected
        num_hands = len(hands_result.multi_hand_landmarks) if hands_result.multi_hand_landmarks else 0
        num_faces = len(faces_result.detections) if faces_result.detections else 0

        # Cheating condition: Only trigger if more than 1 face (i.e., person) is detected.
        # This modification specifically addresses the oversensitivity with two hands
        # by removing any 'num_hands' based cheating detection.
        cheating_in_frame = (num_faces > 1)

        # Logic to manage cheating flag and duration
        if cheating_in_frame:
            if self.cheating_start is None:
                self.cheating_start = time.time() # Start timer if cheating just began
            self.cheating_detected_time = time.time() - self.cheating_start # Calculate duration
            if self.cheating_detected_time > 10:  # If cheating lasts for more than 10 seconds
                self.cheating_flag = True # Set cheating flag
        else:
            self.cheating_start = None  # Reset timer if no cheating detected
            self.cheating_detected_time = 0 # Reset duration
            self.cheating_flag = False  # Reset cheating flag if no cheating

        # Return detection results including cheating status
        return {
            'num_hands': num_hands,
            'num_faces': num_faces,
            'hands_result': hands_result,
            'faces_result': faces_result,
            'cheating_flag': self.cheating_flag,
            'cheating_duration': self.cheating_detected_time
        }

def detect_answer_gesture(hands_result, frame_shape, answer_boxes):
    """
    Detect index fingertip position and check if inside answer boxes.
    answer_boxes: list of tuples (x1,y1,x2,y2) coordinates on frame
    Returns: index of answer 1-4 or None
    """
    if not hands_result.multi_hand_landmarks:
        return None

    # We take the first detected hand for simplicity to identify answer gestures
    hand_landmarks = hands_result.multi_hand_landmarks[0]
    h, w = frame_shape[:2] # Get height and width of the frame

    # Index finger tip is landmark 8 in the Mediapipe hand model
    x_norm = hand_landmarks.landmark[8].x
    y_norm = hand_landmarks.landmark[8].y

    # Convert normalized coordinates to pixel coordinates
    x_px = int(x_norm * w)
    y_px = int(y_norm * h)

    # Check if the index fingertip is within any of the defined answer boxes
    for i, (x1, y1, x2, y2) in enumerate(answer_boxes):
        if x1 < x_px < x2 and y1 < y_px < y2:
            return i + 1  # Return 1-indexed answer number

    return None # No answer gesture detected
