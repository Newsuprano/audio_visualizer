from pathlib import Path
import numpy as np
import soundfile as sf
import sounddevice as sd

# audio = Path("src/audio/heat_waves.wav")
# audio = Path("src/audio/birds_of_a_feather.mp3")
audio = Path("assets/audio/symphony.mp3")
# audio = Path("src/audio/krunk.mp3")

def open_audio_stream(audio_file_path):
    audio_file = Path(audio_file_path)
    if audio_file.is_file():
        return sf.SoundFile(audio_file)
    print("Error, audio file not found.")
    return None

def read_next_chunk(f):
    if f is None:
        return None, None
        
    data = f.read(1024)
    if len(data) == 0:
        f.seek(0)
        data = f.read(4096)
        
    if len(data) == 0:
        return None, None

    sampling_rate = f.samplerate
    signal = data.mean(axis=1) if data.ndim > 1 else data
    N = len(signal)

    fft_output = np.fft.fft(signal)
    frequencies = np.fft.fftfreq(N, d=1 / sampling_rate)

    half_N = N // 2
    positive_frequencies = frequencies[:half_N]
    raw_amplitude = (2.0 / N) * np.abs(fft_output[:half_N])
    normalized_amplitude = np.log1p(raw_amplitude * 20)
    
    return positive_frequencies, normalized_amplitude

def read_chunk_at_position(f, frame_index, chunk_size=4096, num_bins=64):
    if f is None:
        return None, None
        
    total_frames = len(f)
    safe_frame_index = (frame_index % total_frames) if total_frames > 0 else 0
    
    try:
        f.seek(safe_frame_index)
    except Exception:
        f.seek(0)
        
    data = f.read(chunk_size)
    if len(data) == 0:
        f.seek(0)
        data = f.read(chunk_size)
        
    if len(data) == 0:
        return None, None

    sampling_rate = f.samplerate
    signal = data.mean(axis=1) if data.ndim > 1 else data
    N = len(signal)
    
    fft_output = np.fft.fft(signal)
    frequencies = np.fft.fftfreq(N, d=1 / sampling_rate)

    half_N = N // 2
    positive_frequencies = frequencies[:half_N]
    raw_amplitude = (2.0 / N) * np.abs(fft_output[:half_N])
    
    return get_log_bins(positive_frequencies, raw_amplitude, num_bins)

def get_log_bins(frequencies, amplitudes, num_bins=64):
    if len(frequencies) == 0:
        return np.array([]), np.array([])
        
    min_freq = max(20.0, frequencies[1])
    max_freq = min(10000.0, frequencies[-1])
    log_bins = np.logspace(np.log10(min_freq), np.log10(max_freq), num_bins + 1)
    
    binned_amplitudes = []
    binned_frequencies = []
    
    for i in range(num_bins):
        low_f = log_bins[i]
        high_f = log_bins[i + 1]
        mask = (frequencies >= low_f) & (frequencies < high_f)
        
        if np.any(mask) and np.sum(mask) > 0:
            bin_data = amplitudes[mask]
            val = np.max(bin_data) * 0.8 + np.percentile(bin_data, 50) * 0.2
            binned_amplitudes.append(val)
        else:
            binned_amplitudes.append(0.0)
        binned_frequencies.append((low_f + high_f) / 2)
            
    amps_array = np.array(binned_amplitudes)
    
    if len(amps_array) > 2:
        kernel = np.array([0.2, 0.6, 0.2])
        amps_array = np.convolve(amps_array, kernel, mode='same')

    scaled_amps = np.log1p(amps_array * 50) / 5.0
    final_amps = np.clip(scaled_amps, 0.0, 1.0)

    return np.array(binned_frequencies), final_amps

def open_live_audio_stream(sample_rate=44100, channels=1):
    """Opens a continuous live input stream from the default microphone."""
    return sd.InputStream(samplerate=sample_rate, channels=channels)

def process_live_chunk(latest_chunk, sample_rate=44100, num_bins=64, gain=5.0):
    """Processes a raw live audio buffer using the exact same pipeline as file mode."""
    if latest_chunk is None or len(latest_chunk) == 0:
        return None, None
        
    windowed = latest_chunk * np.hanning(len(latest_chunk))
    fft_output = np.fft.fft(windowed)
    
    N = len(windowed)
    frequencies = np.fft.fftfreq(N, d=1 / sample_rate)

    half_N = N // 2
    positive_frequencies = frequencies[:half_N]
    raw_amplitude = (2.0 / N) * np.abs(fft_output[:half_N])
    
    return get_log_bins(positive_frequencies, raw_amplitude * gain, num_bins)