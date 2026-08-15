from pathlib import Path
import numpy as np
import soundfile as sf

#audio = Path("src/audio/heat_waves.wav")
#audio = Path("src/audio/birds_of_a_feather.mp3")
#audio = Path("src/audio/symphony.mp3")
audio = Path("src/audio/krunk.mp3")

def open_audio_stream():
    audio_file = Path(audio)
    if audio_file.is_file():
        # Open the file persistently in read mode
        f = sf.SoundFile(audio_file)
        return f
    else:
        print("Error, audio file not found.")
        return None

def read_next_chunk(f):
    if f is None:
        return None, None
        
    data = f.read(1024)
    
    # If we reach the end of the file, loop back to the beginning
    if len(data) == 0:
        f.seek(0)
        data = f.read(4096)
        
    if len(data) == 0:
        return None, None

    sampling_rate = f.samplerate
    
    # Handle multi-channel audio by averaging to mono
    if data.ndim > 1:
        signal = data.mean(axis=1)
    else:
        signal = data
        
    N = len(signal)

    # Compute FFT
    fft_output = np.fft.fft(signal)
    frequencies = np.fft.fftfreq(N, d=1/sampling_rate)

    half_N = N // 2
    positive_frequencies = frequencies[:half_N]
    raw_amplitude = (2.0 / N) * np.abs(fft_output[:half_N])
    normalized_amplitude = np.log1p(raw_amplitude * 20)
    
    return positive_frequencies, normalized_amplitude

import numpy as np

def read_chunk_at_position(f, frame_index, chunk_size=4096, num_bins=64):
    if f is None:
        return None, None
        
    total_frames = len(f)
    if total_frames > 0:
        safe_frame_index = frame_index % total_frames
    else:
        safe_frame_index = 0
        
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
    
    if data.ndim > 1:
        signal = data.mean(axis=1)
    else:
        signal = data
        
    N = len(signal)
    fft_output = np.fft.fft(signal)
    frequencies = np.fft.fftfreq(N, d=1/sampling_rate)

    half_N = N // 2
    positive_frequencies = frequencies[:half_N]
    raw_amplitude = (2.0 / N) * np.abs(fft_output[:half_N])
    
    # Pass the linear data into our aggressive log-binning function
    binned_freqs, binned_amps = get_log_bins(positive_frequencies, raw_amplitude, num_bins)
    
    return binned_freqs, binned_amps

def get_log_bins(frequencies, amplitudes, num_bins=64):
    if len(frequencies) == 0:
        return np.array([]), np.array([])
        
    min_freq = max(20.0, frequencies[1])
    
    # Cap the max frequency to ~10,000 Hz so the high end doesn't sit empty 
    # (since instruments/vocals rarely have useful data past this point)
    max_freq = min(10000.0, frequencies[-1])
    
    log_bins = np.logspace(np.log10(min_freq), np.log10(max_freq), num_bins + 1)
    
    binned_amplitudes = []
    binned_frequencies = []
    
    for i in range(num_bins):
        low_f = log_bins[i]
        high_f = log_bins[i+1]
        
        mask = (frequencies >= low_f) & (frequencies < high_f)
        
        if np.any(mask) and np.sum(mask) > 0:
            bin_data = amplitudes[mask]
            # Shift weight to np.max so sharp kicks/bass hits punch through instantly
            val = np.max(bin_data) * 0.8 + np.percentile(bin_data, 50) * 0.2
            binned_amplitudes.append(val)
            binned_frequencies.append((low_f + high_f) / 2)
        else:
            binned_amplitudes.append(0.0)
            binned_frequencies.append((low_f + high_f) / 2)
            
    amps_array = np.array(binned_amplitudes)
    
    # --- Safe Vectorized Neighbor Smoothing ---
    if len(amps_array) > 2:
        # A simple moving average kernel (weights add up to 1.0)
        kernel = np.array([0.2, 0.6, 0.2])
        # 'same' mode keeps the output array the exact same length as amps_array
        amps_array = np.convolve(amps_array, kernel, mode='same')
    # ------------------------------------------

    scaled_amps = np.log1p(amps_array * 50) / 5.0
    final_amps = np.clip(scaled_amps, 0.0, 1.0)

    return np.array(binned_frequencies), final_amps