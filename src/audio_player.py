import pygame
from mutagen import File
import numpy as np


class AudioPlayer:
    """Handles static audio file playback, duration tracking, and seeking.
    Designed with a modular interface to easily swap or extend with live desktop audio later.
    """

    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        self.file_path = None
        self.duration = 0.0
        self.is_playing = False
        self.is_loaded = False
        self.current_offset = 0.0

        self._cached_frame = -1
        self._cached_amplitudes = None

    def load_file(self, file_path: str) -> bool:
        """Loads an audio file (.mp3, .wav, etc.), extracts duration, and sets up mixer."""
        try:
            self.file_path = file_path
            
            audio_info = File(file_path)
            self.duration = audio_info.info.length if (audio_info is not None and audio_info.info.length) else 0.0

            pygame.mixer.music.load(file_path)
            self.is_loaded = True
            
            # Reset cache state on new file load
            self._cached_frame = -1
            self._cached_amplitudes = None
            return True
        except Exception as e:
            print(f"Error loading audio file: {e}")
            self.is_loaded = False
            return False

    def play(self, start_sec: float = 0.0):
        """Starts or resumes playback from a specific second offset."""
        if not self.is_loaded:
            return
        
        try:
            self.current_offset = start_sec
            pygame.mixer.music.play(start=start_sec)
            self.is_playing = True
        except Exception as e:
            print(f"Error playing audio stream: {e}")

    def pause(self):
        """Pauses playback and updates current offset."""
        if self.is_loaded and self.is_playing:
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms > 0:
                self.current_offset += pos_ms / 1000.0
            pygame.mixer.music.pause()
            self.is_playing = False

    def unpause(self):
        """Resumes playback from pause."""
        if self.is_loaded and not self.is_playing:
            pygame.mixer.music.unpause()
            self.is_playing = True

    def seek(self, target_sec: float):
        """Seeks to a specific timestamp in seconds."""
        if not self.is_loaded:
            return
        
        target_sec = max(0.0, min(target_sec, self.duration))
        self.current_offset = target_sec
        pygame.mixer.music.play(start=target_sec)

        # Invalidate cache on manual seek jump
        self._cached_frame = -1
        self._cached_amplitudes = None

        if not self.is_playing:
            pygame.mixer.music.pause()

    def get_current_position(self) -> float:
        """Returns the precise current playback position in seconds."""
        if not self.is_loaded:
            return 0.0
        
        if self.is_playing:
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms != -1:
                return min(self.duration, self.current_offset + (pos_ms / 1000.0))
                
        return self.current_offset

    def set_volume(self, volume_value: float):
        """Sets volume using the 0 to 100 scale directly accepted by pygame."""
        vol = max(0.0, min(100.0, volume_value)) / 100.0
        pygame.mixer.music.set_volume(vol)

    def get_duration(self) -> float:
        return self.duration

    def get_active_mode(self) -> str:
        """Returns mode identifier for future modular expansion (e.g., 'file' vs 'desktop')."""
        return "file"

    def get_amplitudes_at_time(self, time_sec: float, chunk_size: int, num_bins: int, audio_stream) -> np.array:
        if audio_stream is None:
            return None
        
        sampling_rate = getattr(audio_stream, 'samplerate', 44100)
        current_frame = int(time_sec * sampling_rate)
        
        if self._cached_amplitudes is None or abs(current_frame - self._cached_frame) >= (chunk_size // 2):
            from audio import read_chunk_at_position
            _, amplitudes = read_chunk_at_position(
                audio_stream,
                current_frame,
                chunk_size=chunk_size,
                num_bins=num_bins,
            )
            self._cached_frame = current_frame
            
            if amplitudes is not None:
                if self._cached_amplitudes is None or len(self._cached_amplitudes) != len(amplitudes):
                    self._cached_amplitudes = amplitudes.copy()
                else:
                    self._cached_amplitudes = self._cached_amplitudes + (amplitudes - self._cached_amplitudes) * 0.4
                    
        return self._cached_amplitudes