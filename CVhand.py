import cv2
import pyautogui
import mediapipe as mp
import time

cap = cv2.VideoCapture(0)
# Set resolution to ~140p (256x144)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 80)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 60)

mp_hands = mp.solutions.hands
hands_detector = mp_hands.Hands(static_image_mode=False, max_num_hands=1,
                              min_detection_confidence=0.8, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

is_pointing_detected = False

while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands_detector.process(image_rgb)
    
    if results.multi_hand_landmarks:
        for hand_no, hand_landmarks in enumerate(results.multi_hand_landmarks):
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            ring_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
            pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
            
            cv2.putText(frame, f"Thumb tip y: {round(thumb_tip.y, 2)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Index tip y: {round(index_finger_tip.y, 2)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Middle tip y: {round(middle_finger_tip.y, 2)}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Ring tip y: {round(ring_finger_tip.y, 2)}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Pinky tip y: {round(pinky_tip.y, 2)}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            is_hand_closed = (
                index_finger_tip.y > thumb_tip.y and
                middle_finger_tip.y > thumb_tip.y and
                ring_finger_tip.y > thumb_tip.y and
                pinky_tip.y > thumb_tip.y
            )
            
            hand_center_x = (
                thumb_tip.x + index_finger_tip.x +
                middle_finger_tip.x + ring_finger_tip.x + pinky_tip.x
            ) / 5

            is_pointing = (
                index_finger_tip.y < thumb_tip.y and 
                middle_finger_tip.y > index_finger_tip.y and  
                ring_finger_tip.y > index_finger_tip.y and
                pinky_tip.y > index_finger_tip.y
            )
            
            if hand_no == 0:
                if is_pointing and not is_pointing_detected:
                    print("up")
                    #pyautogui.press('up')
                    is_pointing_detected = True
                elif is_hand_closed:
                    print("down")
                    #pyautogui.press('down')
                if hand_center_x < 0.4:
                    #pyautogui.press('right')
                    print("right")
                    time.sleep(0.1)
                    
                if hand_center_x > 0.6:
                    #pyautogui.press('left')
                    time.sleep(0.1)
                    print("left")

            if not is_pointing:
                is_pointing_detected = False
            # if hand_no == 1:
            #     if not is_hand_closed:
            #         pyautogui.press('down')
            #         time.sleep(0.1)
    
    cv2.imshow('CV', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()