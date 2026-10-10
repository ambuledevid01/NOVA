import sounddevice as sd
devs = sd.query_devices()
for i, d in enumerate(devs):
    if d["max_input_channels"] > 0:
        print(f"[{i}] {d['name']}  in={d['max_input_channels']}  rate={int(d['default_samplerate'])}")
print()
print("Default input:", sd.default.device[0])
