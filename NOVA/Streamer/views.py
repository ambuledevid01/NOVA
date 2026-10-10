"""
Streamer/views.py — Django views for all NOVA control modules.

Each control module (eye, hand, head, facial, voice) follows the same pattern:
  - Page view   : renders the HTML template (stops all other controllers first)
  - start_*/stop_* : JSON API endpoints called by the frontend via fetch()
  - video feeds  : StreamingHttpResponse for MJPEG camera previews
"""

import logging

import cv2
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render

from control_engine.brain_control import clear_logs as brain_clear_logs
from control_engine.eye_mouse import (
    eye_get_encoded_frame,
    get_eye_mouse_controller,
)
from control_engine.vision.facial_keyboard import (
    clear_logs as facial_clear_logs,
    facial_get_encoded_frame,
    start_facial_keyboard,
    stop_facial_keyboard,
)
from control_engine.vision.hand_control import (
    get_encoded_frame,
    get_hand_controller,
    start_gesture_control,
    stop_gesture_control,
)
from control_engine.vision.head_control import (
    head_get_encoded_frame,
    start_head_control,
    stop_head_control,
)
from control_engine.voice_control import (
    clear_logs as voice_clear_logs,
    execute_command_from_text,
    get_logs,
    get_microphone_list,
    get_status,
    start_voice_control,
    stop_voice_control,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def stop_all_controllers():
    """Gracefully stop every active control module. Logs — never raises."""
    for name, fn in [
        ("gesture",  stop_gesture_control),
        ("head",     stop_head_control),
        ("voice",    stop_voice_control),
        ("facial",   stop_facial_keyboard),
    ]:
        try:
            fn()
        except Exception as exc:
            logger.warning("Error stopping %s controller: %s", name, exc)

    try:
        get_eye_mouse_controller().stop()
    except Exception as exc:
        logger.warning("Error stopping eye controller: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Page views
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard_page(request):
    stop_all_controllers()
    return render(request, "dashboard/dashboard.html")


@login_required
def eye_control(request):
    stop_all_controllers()
    return render(request, "dashboard/eye_control.html")


@login_required
def facial_exp(request):
    stop_all_controllers()
    return render(request, "dashboard/facial_exp.html")


@login_required
def voice_control(request):
    stop_all_controllers()
    return render(request, "dashboard/voice_control.html")


@login_required
def hand_control(request):
    stop_all_controllers()
    return render(request, "dashboard/hand_control.html")


@login_required
def head_control(request):
    stop_all_controllers()
    return render(request, "dashboard/head_control.html")


@login_required
def settings_page(request):
    stop_all_controllers()
    return render(request, "dashboard/settings.html")


def about_us(request):
    return render(request, "about_us.html")


# ─────────────────────────────────────────────────────────────────────────────
# Settings / system
# ─────────────────────────────────────────────────────────────────────────────

def reset_system(request):
    """Clear Django cache and all module activity logs."""
    cache.clear()
    for fn in (voice_clear_logs, facial_clear_logs, brain_clear_logs):
        try:
            fn()
        except Exception as exc:
            logger.warning("Error clearing logs: %s", exc)
    return JsonResponse({"status": "success", "message": "Memory cache and logs cleared."})


# ─────────────────────────────────────────────────────────────────────────────
# Voice control
# ─────────────────────────────────────────────────────────────────────────────

def start_voice(request):
    mic_idx_str = request.GET.get("mic_index", "")
    device_index = int(mic_idx_str) if mic_idx_str.isdigit() else None
    try:
        start_voice_control(device_index=device_index)
        return JsonResponse({"status": "started"})
    except Exception as exc:
        logger.error("Failed to start voice control: %s", exc)
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


def stop_voice(request):
    stop_voice_control()
    return JsonResponse({"status": "stopped"})


def voice_logs(request):
    return JsonResponse({"logs": get_logs(), "status": get_status()})


def list_microphones(request):
    return JsonResponse({"microphones": get_microphone_list()})


def execute_voice_command(request):
    text = request.GET.get("text", "") or request.POST.get("text", "")
    if not text:
        return JsonResponse({"status": "error", "message": "No command text provided"}, status=400)
    result = execute_command_from_text(text)
    return JsonResponse(result)


# ─────────────────────────────────────────────────────────────────────────────
# Eye control
# ─────────────────────────────────────────────────────────────────────────────

def start_eye(request):
    try:
        get_eye_mouse_controller().start()
        return JsonResponse({"status": "started"})
    except Exception as exc:
        logger.error("Failed to start eye control: %s", exc)
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


def stop_eye(request):
    try:
        get_eye_mouse_controller().stop()
    except Exception as exc:
        logger.warning("Error stopping eye control: %s", exc)
    return JsonResponse({"status": "stopped"})


def eye_video_feed(request):
    import time
    def generate():
        while True:
            frame = eye_get_encoded_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            else:
                time.sleep(0.1)
    return StreamingHttpResponse(
        generate(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Facial expression control
# ─────────────────────────────────────────────────────────────────────────────

def start_facial(request):
    try:
        start_facial_keyboard()
        return JsonResponse({"status": "started"})
    except Exception as exc:
        logger.error("Failed to start facial control: %s", exc)
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


def stop_facial(request):
    stop_facial_keyboard()
    return JsonResponse({"status": "stopped"})


def facial_logs(request):
    from control_engine.vision.facial_keyboard import get_logs, get_status
    return JsonResponse({"logs": get_logs(), "status": get_status()})


def facial_video_feed(request):
    import time
    def generate():
        while True:
            frame = facial_get_encoded_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            else:
                time.sleep(0.1)
    return StreamingHttpResponse(
        generate(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Hand gesture control
# ─────────────────────────────────────────────────────────────────────────────

def start_hand_control(request):
    try:
        start_gesture_control()
        return JsonResponse({"status": "started"})
    except Exception as exc:
        logger.error("Failed to start hand control: %s", exc)
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


def stop_hand_control(request):
    stop_gesture_control()
    return JsonResponse({"status": "stopped"})


def hand_set_settings(request):
    """Apply pointer_gain, scroll_gain, smooth_alpha from GET or POST params."""
    ctrl = get_hand_controller()
    params = request.GET if request.method == "GET" else request.POST
    try:
        ctrl.set_settings(
            pointer_gain=float(params["pointer_gain"]) if "pointer_gain" in params else None,
            scroll_gain=float(params["scroll_gain"])   if "scroll_gain"  in params else None,
            smooth_alpha=float(params["smooth_alpha"]) if "smooth_alpha" in params else None,
        )
    except (ValueError, KeyError) as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)
    return JsonResponse({"status": "ok", **ctrl.get_settings()})


def hand_get_settings(request):
    return JsonResponse(get_hand_controller().get_settings())


def hand_begin_calibration(request):
    return JsonResponse(get_hand_controller().begin_calibration())


def hand_finish_calibration(request):
    return JsonResponse(get_hand_controller().finish_calibration())


def hand_reset_calibration(request):
    return JsonResponse(get_hand_controller().reset_calibration())


def video_feed(request):
    import time
    def generate():
        while True:
            frame = get_encoded_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            else:
                time.sleep(0.1)
    return StreamingHttpResponse(
        generate(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Head movement control
# ─────────────────────────────────────────────────────────────────────────────

def start_head(request):
    try:
        start_head_control()
        return JsonResponse({"status": "started"})
    except Exception as exc:
        logger.error("Failed to start head control: %s", exc)
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


def stop_head(request):
    stop_head_control()
    return JsonResponse({"status": "stopped"})


def get_encoded_frame_head(request):
    import time
    def generate():
        while True:
            frame = head_get_encoded_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            else:
                time.sleep(0.1)
    return StreamingHttpResponse(
        generate(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )