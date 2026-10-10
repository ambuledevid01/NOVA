"""
Head Control - Option B (Stable & Practical)

Gestures:
- Head movement → Cursor move
- Mouth open → Left click
- Tilt right (hold 0.6s) → Right click
- Sustained vertical movement → Scroll
"""

import cv2
import numpy as np
import threading
import time
import pyautogui
from pathlib import Path

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe import Image, ImageFormat

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


class HeadControlController:

    def __init__(self):
        self._capture = None
        self._thread = None
        self._stop_event = threading.Event()
        self._last_frame = None
        self._last_cursor = None
        self._last_click_time = 0
        self._last_rclick_time = 0
        self._baseline_x = None
        self._baseline_y = None
        self._tilt_start_time = None
        self._prev_scroll_y = None

        screen = pyautogui.size()
        self.screen_w = screen.width
        self.screen_h = screen.height

        # MediaPipe detector — loaded lazily in start() to avoid crashing
        # the server at import time if the model file is missing.
        self.detector = None
        self._model_path = Path(__file__).resolve().parents[1] / "models" / "face_landmarker.task"

    # ---------------- START / STOP ----------------

    def start(self):
        if self.is_running:
            return

        # Load the MediaPipe model here so a missing file gives a clear
        # error message scoped to head control — not a startup crash.
        if self.detector is None:
            if not self._model_path.exists():
                raise RuntimeError(
                    f"MediaPipe face_landmarker.task model not found at:\n"
                    f"  {self._model_path}\n"
                    "Download it from https://storage.googleapis.com/mediapipe-models/"
                    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
                )
            base_options = python.BaseOptions(model_asset_path=str(self._model_path))
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1,
            )
            self.detector = vision.FaceLandmarker.create_from_options(options)

        self._capture = cv2.VideoCapture(0)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._capture:
            self._capture.release()

    @property
    def is_running(self):
        return self._thread and self._thread.is_alive()

    def latest_frame(self):
        return self._last_frame

    # ---------------- MAIN LOOP ----------------

    def _loop(self):
        while not self._stop_event.is_set():
            ret, frame = self._capture.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)

            # Use real millisecond timestamp — MediaPipe VIDEO mode requires it
            timestamp_ms = int(time.time() * 1000)
            results = self.detector.detect_for_video(mp_image, timestamp_ms)

            if results.face_landmarks:

                face = results.face_landmarks[0]

                # Nose for movement
                nose = face[1]
                norm_x = nose.x
                norm_y = nose.y

                current_time = time.time()

                # Initialize baseline
                if self._baseline_x is None:
                    self._baseline_x = norm_x
                    self._baseline_y = norm_y

                dx = norm_x - self._baseline_x
                dy = norm_y - self._baseline_y

                # ---------------- CURSOR MOVE ----------------
                self._move_cursor(dx, dy)

                # ---------------- LEFT CLICK (Left Eye Blink) ----------------
                left_eye_dist = abs(face[159].y - face[145].y)
                right_eye_dist = abs(face[386].y - face[374].y)

                blink_thresh = 0.018  # raised from 0.012 — real blinks produce 0.02–0.04

                # If only left eye blinks
                if left_eye_dist < blink_thresh and right_eye_dist >= blink_thresh:
                    if current_time - self._last_click_time > 1.2:
                        pyautogui.click()
                        self._last_click_time = current_time

                # ---------------- RIGHT CLICK (Right Eye Blink) ----------------
                # If only right eye blinks
                if right_eye_dist < blink_thresh and left_eye_dist >= blink_thresh:
                    if current_time - self._last_rclick_time > 1.2:
                        pyautogui.rightClick()
                        self._last_rclick_time = current_time

                # ---------------- SCROLL ----------------
                if abs(dy) > 0.12:
                    if self._prev_scroll_y is None:
                        self._prev_scroll_y = dy

                    scroll_delta = (self._prev_scroll_y - dy) * 2000
                    pyautogui.scroll(int(scroll_delta))
                    self._prev_scroll_y = dy
                else:
                    self._prev_scroll_y = None

                # Draw nose pointer
                h, w, _ = frame.shape
                cx, cy = int(norm_x * w), int(norm_y * h)
                cv2.circle(frame, (cx, cy), 6, (0, 255, 0), -1)

                # Debug overlay: show live eye distance values
                cv2.putText(frame, f"L-eye: {left_eye_dist:.4f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(frame, f"R-eye: {right_eye_dist:.4f}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(frame, f"thresh: {blink_thresh}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
                if left_eye_dist < blink_thresh:
                    cv2.putText(frame, "LEFT BLINK!", (10, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                if right_eye_dist < blink_thresh:
                    cv2.putText(frame, "RIGHT BLINK!", (10, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            self._last_frame = frame

    # ---------------- CURSOR ----------------

    def _move_cursor(self, dx, dy):

        deadzone = 0.03

        if abs(dx) < deadzone:
            dx = 0
        if abs(dy) < deadzone:
            dy = 0

        sensitivity = 3.0

        target_x = self.screen_w / 2 + dx * self.screen_w * sensitivity
        target_y = self.screen_h / 2 + dy * self.screen_h * sensitivity

        target_x = np.clip(target_x, 0, self.screen_w)
        target_y = np.clip(target_y, 0, self.screen_h)

        if self._last_cursor is None:
            smooth_x, smooth_y = target_x, target_y
        else:
            px, py = self._last_cursor
            alpha = 0.25
            smooth_x = (1 - alpha) * px + alpha * target_x
            smooth_y = (1 - alpha) * py + alpha * target_y

        pyautogui.moveTo(smooth_x, smooth_y)
        self._last_cursor = (smooth_x, smooth_y)


# -------- Singleton --------

_HEAD = None

def get_head_controller():
    global _HEAD
    if _HEAD is None:
        _HEAD = HeadControlController()
    return _HEAD

def start_head_control():
    get_head_controller().start()

def stop_head_control():
    get_head_controller().stop()

def head_get_encoded_frame():
    frame = get_head_controller().latest_frame()
    if frame is None:
        return None
    _, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes()