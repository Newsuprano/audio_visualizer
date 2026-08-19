import queue
import numpy as np
import pyaudiowpatch as pyaudio

class AudioManager:
    def __init__(self):
        self.pyaudio_instance = pyaudio.PyAudio()
        self.live_stream = None
        self.audio_queue = queue.Queue()

    def get_devices(self):
        """Returns a list of valid input devices for microphones."""
        devices = []
        try:
            device_count = self.pyaudio_instance.get_device_count()
            for i in range(device_count):
                dev_info = self.pyaudio_instance.get_device_info_by_index(i)
                dev_name = dev_info['name']
                if "loopback" not in dev_name.lower() and dev_info['maxInputChannels'] > 0:
                    devices.append((i, dev_name))
        except Exception as e:
            print(f"Error enumerating devices: {e}")
        return devices

    def start_stream(self, device_idx, channels, rate):
        self.stop_stream()
        self.audio_queue = queue.Queue()
        target_queue = self.audio_queue

        def pyaudio_callback(in_data, frame_count, time_info, status):
            audio_data = np.frombuffer(in_data, dtype=np.float32).copy()
            if channels > 1 and audio_data.size > 0:
                audio_data = audio_data[::channels]
            target_queue.put(audio_data)
            return (None, pyaudio.paContinue)

        try:
            self.live_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device_idx,
                frames_per_buffer=1024,
                stream_callback=pyaudio_callback
            )
            self.live_stream.start_stream()
        except Exception as e:
            print(f"Stream start error on index {device_idx}: {e}")

    def get_default_desktop_loopback(self):
        """Finds and returns the default WASAPI loopback device for system audio."""
        try:
            wasapi_info = self.pyaudio_instance.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = self.pyaudio_instance.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            target_loopback = None
            for loopback in self.pyaudio_instance.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    target_loopback = loopback
                    break
            
            if target_loopback is None:
                target_loopback = self.pyaudio_instance.get_default_wasapi_loopback()

            return {
                'index': target_loopback['index'],
                'channels': int(target_loopback['maxInputChannels']) if int(target_loopback['maxInputChannels']) >= 1 else 2,
                'rate': int(target_loopback['defaultSampleRate']) if int(target_loopback['defaultSampleRate']) > 0 else 44100
            }
        except Exception as e:
            print(f"Failed to get desktop loopback: {e}")
            return None

    def stop_stream(self):
        if self.live_stream is not None:
            try:
                self.live_stream.stop_stream()
                self.live_stream.close()
            except Exception:
                pass
            self.live_stream = None