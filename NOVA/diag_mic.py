import pyaudio
import speech_recognition as sr

pa = pyaudio.PyAudio()
print("=== ALL INPUT DEVICES (with maxInputChannels > 0) ===")
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if info["maxInputChannels"] > 0:
        print(f"  [{i}] {info['name']}  channels={info['maxInputChannels']}  rate={int(info['defaultSampleRate'])}")
pa.terminate()

print()
print("=== DEFAULT INPUT DEVICE ===")
pa2 = pyaudio.PyAudio()
try:
    d = pa2.get_default_input_device_info()
    print(f"  [{d['index']}] {d['name']}")
except Exception as e:
    print(f"  No default: {e}")
pa2.terminate()

print()
print("=== QUICK RECORD TEST (2 seconds) ===")
r = sr.Recognizer()
r.dynamic_energy_threshold = False
r.energy_threshold = 300

# Try device 0 first (default) – adjust index if needed
try:
    mic = sr.Microphone(device_index=None)
    with mic as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        print(f"  Energy threshold after calibration: {r.energy_threshold:.1f}")
        print("  Recording 2 seconds of audio now...")
        audio = r.listen(source, timeout=3, phrase_time_limit=3)
    
    with open("diag_test.wav", "wb") as f:
        f.write(audio.get_wav_data())
    print("  Saved wav to diag_test.wav")

    try:
        text = r.recognize_google(audio)
        print(f"  Recognized: '{text}'")
    except sr.UnknownValueError:
        print("  Google returned: UNINTELLIGIBLE (audio captured, but speech not clear enough)")
    except sr.RequestError as e:
        print(f"  Google API error: {e}")
except Exception as e:
    print(f"  ERROR: {e}")
