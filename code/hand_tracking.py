import cv2
import mediapipe as mp

class HandController:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)

        self.mp_hands = mp.solutions.hands
        # ✅ Chỉnh max_num_hands=2 để nhận diện được cả 2 tay
        self.hands = self.mp_hands.Hands(
            max_num_hands=2, 
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

        self.mp_draw = mp.solutions.drawing_utils
        self.direction = (0, 0)
        self.is_shooting = False
        
        # ✅ Tách biệt số ngón tay của từng tay
        self.left_fingers = 0  # Tay trái: dùng vật phẩm
        self.right_fingers = 0 # Tay phải: di chuyển + bắn
        self.fingers_up = 0    # Biến chung để tránh lỗi code cũ

        self.cap = cv2.VideoCapture(0)
        
        # ✅ Khởi tạo cửa sổ 1 lần duy nhất tại đây
        self.window_name = "Hand Tracking"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 240, 180)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)

    def update(self):
        success, frame = self.cap.read()
        if not success: return

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        # Reset dữ liệu mỗi frame để tránh bị dính lệnh cũ
        self.direction = (0, 0)
        self.is_shooting = False 
        self.left_fingers = 0
        self.right_fingers = 0

        if results.multi_hand_landmarks and results.multi_handedness:
            for handLms, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                # Xác định tay Trái hay Phải
                label = handedness.classification[0].label 

                # Logic đếm ngón tay (giữ nguyên để nhận diện trạng thái tay)
                fingers = []
                # Ngón cái
                if label == "Right": 
                    if handLms.landmark[4].x > handLms.landmark[3].x: fingers.append(1)
                    else: fingers.append(0)
                else: 
                    if handLms.landmark[4].x < handLms.landmark[3].x: fingers.append(1)
                    else: fingers.append(0)

                # 4 ngón còn lại
                tips = [8, 12, 16, 20]
                for tip in tips:
                    if handLms.landmark[tip].y < handLms.landmark[tip - 2].y:
                        fingers.append(1)
                    else:
                        fingers.append(0)
                
                count = fingers.count(1)

                # --- CHIA LẠI NHIỆM VỤ ---
                if label == "Right": 
                    # TAY PHẢI: CHỈ DI CHUYỂN & BẮN
                    self.right_fingers = count
                    
                    # 1. Di chuyển (theo ngón trỏ)
                    lm = handLms.landmark[8]
                    self.direction = ((lm.x - 0.5) * 2, (lm.y - 0.5) * 2)
                    
                    # 2. Bắn (Khi nắm tay - 0 ngón mở)
                    if count == 0:
                        self.is_shooting = True
                    
                    # Triệt tiêu khả năng dùng item của tay phải (nếu có biến liên quan)
                    # Không gán self.left_fingers ở đây.
                
                elif label == "Left": 
                    # TAY TRÁI: CHỈ DÙNG VẬT PHẨM
                    self.left_fingers = count
                
                # Vẽ để kiểm tra trên màn hình cam
                self.mp_draw.draw_landmarks(frame, handLms, self.mp_hands.HAND_CONNECTIONS)

        cv2.imshow(self.window_name, frame)
        cv2.waitKey(1)