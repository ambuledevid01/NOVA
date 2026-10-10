import pyaudio
import speech_recognition as sr

r = sr.Recognizer()
r.dynamic_energy_threshold = False
r.pause_threshold = 1.0

# Test device indices that are real microphones
for device_index in [3, 10, 18, 22, 1, None]:
    label = f"device_index={device_index}"
    print(f"\n--- Testing {label} ---")
    try:
        mic = sr.Microphone(device_index=device_index)
        with mic as source:
            r.energy_threshold = 50  # very low threshold
            r.adjust_for_ambient_noise(source, duration=0.5)
            print(f"  Threshold after calibration: {r.energy_threshold:.1f}")
            print("  Say something in 3 seconds...")
            audio = r.listen(source, timeout=4, phrase_time_limit=3)
        print(f"  Audio captured! size={len(audio.get_wav_data())} bytes")
        try:
            text = r.recognize_google(audio)
            print(f"  SUCCESS - Recognized: '{text}'")
        except sr.UnknownValueError:
            print("  CAPTURED but Unintelligible for Google")
        except sr.RequestError as e:
            print(f"  Google API error: {e}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    choice = input("\nDid the test capture your voice? (y/n/skip to next): ").strip().lower()
    if choice == "y":
        print(f"\n=== USE device_index={device_index} in your app ===")
        break
