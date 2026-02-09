import pyaudio

def list_audio_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    print("--- Available Audio Devices ---")
    for i in range(0, numdevices):
        dev = p.get_device_info_by_host_api_device_index(0, i)
        print(f"Index {i}: {dev.get('name')} - Input: {dev.get('maxInputChannels')}, Output: {dev.get('maxOutputChannels')}")

    p.terminate()

if __name__ == "__main__":
    list_audio_devices()
