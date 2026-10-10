"""
NOVA Voice Command Control — SpeechRecognition + pyaudio
Uses Python's built-in speech_recognition library.
No model download needed. Works offline for mic capture,
uses Google's free web speech endpoint for transcription.
"""

from __future__ import annotations

import os
import threading
import subprocess
from typing import List, Optional

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
except ImportError:
    pyautogui = None

# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────
_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_status = "Idle"
_logs: List[str] = []
_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    with _lock:
        _logs.append(msg)
        if len(_logs) > 50:
            _logs.pop(0)

# ─────────────────────────────────────────────────────────────────────────────
# Command Execution — keyword matching
# ─────────────────────────────────────────────────────────────────────────────

def _safe_run(cmd: str, fallback_url: Optional[str] = None):
    try:
        subprocess.Popen(cmd, shell=True)
    except Exception:
        if fallback_url:
            os.startfile(fallback_url)

def _kill_proc(process_name: str):
    """Safely terminate a process by name or fallback to Alt+F4."""
    try:
        os.system(f"taskkill /f /im {process_name} >nul 2>&1")
    except Exception:
        if pyautogui:
            pyautogui.hotkey("alt", "f4")

COMMANDS = [
    # ── App Launchers ──────────────────────────────────────────────────────────
    (["open camera", "camera"],
        lambda: os.system("start microsoft.windows.camera:"), "📷 Opening Camera"),
    (["open browser", "open chrome", "open google", "launch browser"],
        lambda: os.startfile("https://google.com"), "🌐 Opening Browser"),
    (["open firefox"],
        lambda: _safe_run("firefox", "https://mozilla.org"), "🌐 Opening Firefox"),
    (["open edge"],
        lambda: _safe_run("msedge", "https://microsoft.com"), "🌐 Opening Edge"),
    (["open file manager", "open files", "open explorer", "open file", "my computer"],
        lambda: subprocess.Popen("explorer"), "📁 Opening File Manager"),
    (["open notepad", "launch notepad", "text editor"],
        lambda: subprocess.Popen("notepad"), "📝 Opening Notepad"),
    (["open calculator", "launch calculator", "calc"],
        lambda: subprocess.Popen("calc"), "🔢 Opening Calculator"),
    (["open settings", "system settings", "open config"],
        lambda: os.system("start ms-settings:"), "⚙ Opening Settings"),
    (["open task manager", "launch task manager", "taskmgr"],
        lambda: subprocess.Popen("taskmgr"), "🖥 Opening Task Manager"),
    (["open command prompt", "open cmd", "open terminal", "launch terminal"],
        lambda: subprocess.Popen("cmd"), "💻 Opening Terminal"),
    (["open vs code", "open vscode", "open code"],
        lambda: _safe_run("code"), "👨‍💻 Opening VS Code"),
    (["open paint", "launch paint", "draw"],
        lambda: subprocess.Popen("mspaint"), "🎨 Opening Paint"),
    (["open snipping tool", "snip screen", "snipping tool"],
        lambda: _safe_run("snippingtool"), "✂ Opening Snipping Tool"),
    (["open youtube", "launch youtube"],
        lambda: os.startfile("https://youtube.com"), "▶ Opening YouTube"),
    (["open spotify", "launch spotify", "play music app"],
        lambda: _safe_run("spotify", "https://open.spotify.com"), "🎵 Opening Spotify"),
    (["open word"],
        lambda: _safe_run("winword"), "📄 Opening Word"),
    (["open excel"],
        lambda: _safe_run("excel"), "📊 Opening Excel"),

    # ── App Closers & Exit Commands ──────────────────────────────────────────
    (["close camera", "exit camera"],
        lambda: _kill_proc("WindowsCamera.exe"), "❌ Closing Camera"),
    (["close notepad", "exit notepad", "quit notepad"],
        lambda: _kill_proc("notepad.exe"), "❌ Closing Notepad"),
    (["close calculator", "close calc", "exit calculator"],
        lambda: _kill_proc("CalculatorApp.exe") or _kill_proc("calc.exe"), "❌ Closing Calculator"),
    (["close browser", "close chrome", "exit chrome"],
        lambda: _kill_proc("chrome.exe"), "❌ Closing Chrome Browser"),
    (["close firefox", "exit firefox"],
        lambda: _kill_proc("firefox.exe"), "❌ Closing Firefox"),
    (["close edge", "exit edge"],
        lambda: _kill_proc("msedge.exe"), "❌ Closing Edge"),
    (["close explorer", "close file manager", "close files"],
        lambda: pyautogui and pyautogui.hotkey("alt", "f4"), "❌ Closing File Explorer"),
    (["close terminal", "close cmd", "close command prompt"],
        lambda: _kill_proc("cmd.exe"), "❌ Closing Terminal"),
    (["close vs code", "close vscode", "close code"],
        lambda: _kill_proc("Code.exe"), "❌ Closing VS Code"),
    (["close spotify", "exit spotify"],
        lambda: _kill_proc("Spotify.exe"), "❌ Closing Spotify"),
    (["close paint", "exit paint"],
        lambda: _kill_proc("mspaint.exe"), "❌ Closing Paint"),
    (["close word", "exit word"],
        lambda: _kill_proc("WINWORD.EXE"), "❌ Closing Word"),
    (["close excel", "exit excel"],
        lambda: _kill_proc("EXCEL.EXE"), "❌ Closing Excel"),
    (["close app", "close window", "close this", "exit app", "quit application", "exit program"],
        lambda: pyautogui and pyautogui.hotkey("alt", "f4"), "❌ Closing Active Window"),

    # ── Navigation & Return Commands ─────────────────────────────────────────
    (["come back", "go back", "switch back", "previous window", "back to previous", "last app"],
        lambda: pyautogui and pyautogui.hotkey("alt", "tab"), "🔄 Coming Back"),
    (["return to nova", "open nova", "go to nova", "show nova"],
        lambda: pyautogui and pyautogui.hotkey("alt", "tab"), "🏠 Returning to NOVA"),
    (["open dashboard", "go to dashboard", "show dashboard", "control center"],
        lambda: os.startfile("http://127.0.0.1:8000/Stream/dashboard_page/"), "🎛 Opening Dashboard"),
    (["open voice control", "go to voice control"],
        lambda: os.startfile("http://127.0.0.1:8000/Stream/voice_control/"), "🎤 Opening Voice Control"),
    (["open home", "go to home"],
        lambda: os.startfile("http://127.0.0.1:8000/"), "🏠 Opening Home Page"),

    # ── Window & Desktop Control ─────────────────────────────────────────────
    (["minimize window", "minimize", "hide window"],
        lambda: pyautogui and pyautogui.hotkey("win", "down"), "➖ Minimize Window"),
    (["maximize window", "maximize", "full screen window"],
        lambda: pyautogui and pyautogui.hotkey("win", "up"), "➕ Maximize Window"),
    (["show desktop", "minimize all"],
        lambda: pyautogui and pyautogui.hotkey("win", "d"), "🖥 Showing Desktop"),
    (["switch window", "next window", "change app"],
        lambda: pyautogui and pyautogui.hotkey("alt", "tab"), "🔄 Switch Window"),
    (["lock pc", "lock computer", "screen lock"],
        lambda: os.system("rundll32.exe user32.dll,LockWorkStation"), "🔒 Locking PC"),
    (["take screenshot", "screenshot", "capture screen"],
        lambda: pyautogui and pyautogui.hotkey("win", "shift", "s"), "📸 Screenshot"),


    # ── Browser & Web Navigation ──────────────────────────────────────────────
    (["new tab"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "t"), "📑 New Tab"),
    (["close tab"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "w"), "❌ Close Tab"),
    (["reopen tab", "restore tab"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "shift", "t"), "↺ Reopen Tab"),
    (["refresh page", "refresh", "reload page"],
        lambda: pyautogui and pyautogui.press("f5"), "🔃 Refresh Page"),
    (["go back", "back page"],
        lambda: pyautogui and pyautogui.hotkey("alt", "left"), "◀ Go Back"),
    (["go forward", "forward page"],
        lambda: pyautogui and pyautogui.hotkey("alt", "right"), "▶ Go Forward"),
    (["bookmark page", "add bookmark"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "d"), "⭐ Bookmark Page"),
    (["zoom in", "make bigger"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "plus"), "🔍 Zoom In"),
    (["zoom out", "make smaller"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "minus"), "🔍 Zoom Out"),
    (["reset zoom", "normal zoom"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "0"), "🔍 Reset Zoom"),

    # ── Mouse & Navigation ───────────────────────────────────────────────────
    (["double click", "double tap"],
        lambda: pyautogui and pyautogui.doubleClick(), "🖱 Double Click"),
    (["right click"],
        lambda: pyautogui and pyautogui.rightClick(), "🖱 Right Click"),
    (["left click", "click"],
        lambda: pyautogui and pyautogui.click(), "🖱 Click"),
    (["scroll down", "go down"],
        lambda: pyautogui and pyautogui.scroll(-500), "⬇ Scroll Down"),
    (["scroll up", "go up"],
        lambda: pyautogui and pyautogui.scroll(500), "⬆ Scroll Up"),
    (["scroll to top", "top of page"],
        lambda: pyautogui and pyautogui.press("home"), "🔝 Scroll to Top"),
    (["scroll to bottom", "bottom of page"],
        lambda: pyautogui and pyautogui.press("end"), "🔚 Scroll to Bottom"),

    # ── Audio & Media Controls ───────────────────────────────────────────────
    (["volume up", "louder", "increase volume"],
        lambda: pyautogui and pyautogui.press("volumeup"), "🔊 Volume Up"),
    (["volume down", "quieter", "decrease volume"],
        lambda: pyautogui and pyautogui.press("volumedown"), "🔉 Volume Down"),
    (["mute volume", "mute sound", "mute"],
        lambda: pyautogui and pyautogui.press("volumemute"), "🔇 Mute Audio"),
    (["play media", "pause media", "play music", "pause music", "pause"],
        lambda: pyautogui and pyautogui.press("playpause"), "⏯ Play/Pause"),
    (["next song", "next track"],
        lambda: pyautogui and pyautogui.press("nexttrack"), "⏭ Next Track"),
    (["previous song", "previous track"],
        lambda: pyautogui and pyautogui.press("prevtrack"), "⏮ Previous Track"),

    # ── Editing, Typing & Text Shortcuts ──────────────────────────────────────
    (["copy that", "copy"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "c"), "📋 Copy"),
    (["paste that", "paste"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "v"), "📋 Paste"),
    (["cut that", "cut"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "x"), "✂ Cut"),
    (["undo that", "undo"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "z"), "↩ Undo"),
    (["redo that", "redo"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "y"), "↪ Redo"),
    (["select all"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "a"), "☑ Select All"),
    (["save file", "save"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "s"), "💾 Save File"),
    (["press enter", "enter"],
        lambda: pyautogui and pyautogui.press("enter"), "↵ Enter"),
    (["press space", "space bar"],
        lambda: pyautogui and pyautogui.press("space"), "␣ Space"),
    (["press escape", "escape"],
        lambda: pyautogui and pyautogui.press("escape"), "⎋ Escape"),
    (["backspace", "delete letter"],
        lambda: pyautogui and pyautogui.press("backspace"), "⌫ Backspace"),
    (["delete word"],
        lambda: pyautogui and pyautogui.hotkey("ctrl", "backspace"), "⌫ Delete Word"),
]



def _execute(text: str) -> Optional[str]:
    """Try to match text against COMMANDS. Return label if matched, else None."""
    t = text.lower()
    for keywords, action, label in COMMANDS:
        for kw in keywords:
            if kw in t:
                try:
                    action()
                except Exception as e:
                    return f"⚠ Error running '{label}': {e}"
                return label
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Microphone list
# ─────────────────────────────────────────────────────────────────────────────

def get_microphone_list() -> List[str]:
    if sr is None:
        return ["speech_recognition not installed"]
    try:
        return sr.Microphone.list_microphone_names()
    except Exception as e:
        return [f"Error listing mics: {e}"]


# ─────────────────────────────────────────────────────────────────────────────
# Listen Loop — uses SpeechRecognition (pyaudio backend)
# ─────────────────────────────────────────────────────────────────────────────

def _run(device_index: Optional[int]) -> None:
    global _status

    if sr is None:
        _log("❌ speech_recognition not installed — run: pip install SpeechRecognition pyaudio")
        _status = "Error: speech_recognition missing"
        return

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300        # mic sensitivity
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8         # seconds of silence before phrase ends

    try:
        mic_kwargs = {}
        if device_index is not None:
            mic_kwargs["device_index"] = device_index

        with sr.Microphone(**mic_kwargs) as source:
            _log("🎤 Calibrating microphone for ambient noise (2s)...")
            _status = "Calibrating..."
            recognizer.adjust_for_ambient_noise(source, duration=2)
            _log("✅ Ready! Say a command now.")
            _status = "Listening"

            while not _stop_event.is_set():
                try:
                    _log("… listening...")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                except sr.WaitTimeoutError:
                    # No speech heard — loop again
                    continue

                if _stop_event.is_set():
                    break

                # Remove the last "… listening..." partial line before adding result
                with _lock:
                    if _logs and _logs[-1].startswith("…"):
                        _logs.pop()

                _log("⏳ Processing speech...")
                try:
                    text = recognizer.recognize_google(audio)
                    text = text.strip()
                    if text:
                        label = _execute(text)
                        if label:
                            _log(f"✔ '{text}'  →  {label}")
                        else:
                            _log(f"💬 Heard: '{text}'  (no command matched)")
                    else:
                        _log("🔇 Couldn't make out anything, try again.")
                except sr.UnknownValueError:
                    _log("🔇 Could not understand — speak clearly and try again.")
                except sr.RequestError as e:
                    _log(f"❌ Speech service error: {e}")
                    # Try again after a short wait
                    import time
                    time.sleep(2)

    except OSError as e:
        _log(f"❌ Microphone error: {e}  — check mic connection.")
        _status = f"Error: mic unavailable"
    except Exception as e:
        _log(f"❌ Unexpected error: {e}")
        _status = f"Error: {e}"
    finally:
        _status = "Stopped"
        _log("⏹ Voice control stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# Public API (called by Django views)
# ─────────────────────────────────────────────────────────────────────────────

def start_voice_control(device_index: Optional[int] = None) -> None:
    global _thread, _stop_event, _status
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_run, args=(device_index,), daemon=True)
    _thread.start()
    _status = "Starting..."


def stop_voice_control() -> None:
    """Signal the listener thread to stop. Non-blocking — returns immediately."""
    global _status
    _stop_event.set()
    _status = "Stopping..."
    # Thread is daemon=True so it will die on its own; no join needed here
    _log("⏹ Stop requested — finishing current phrase...")


def get_status() -> str:
    return _status


def get_logs() -> List[str]:
    with _lock:
        return list(_logs)


def clear_logs() -> None:
    with _lock:
        _logs.clear()


def execute_command_from_text(text: str) -> dict:
    """Public helper to process a text command, log it, execute it, and return JSON status."""
    clean_text = text.strip()
    if not clean_text:
        return {"status": "empty", "label": None, "text": clean_text}
    
    label = _execute(clean_text)
    if label:
        if label.startswith("⚠ Error"):
            _log(f"{label}")
            return {"status": "error", "message": label, "text": clean_text}
        else:
            _log(f"✔ '{clean_text}'  →  {label}")
            return {"status": "executed", "label": label, "text": clean_text}
    else:
        _log(f"💬 Heard: '{clean_text}'  (no command matched)")
        return {"status": "no_match", "label": None, "text": clean_text}

