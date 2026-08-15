import pygame
from audio import open_audio_stream, read_chunk_at_position
from renderer import draw_visualizer
from circular_renderer import draw_circular_visualizer

audio = "birds_of_a_feather.mp3"

pygame.init()
pygame.mixer.init()

screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

pygame.mixer.music.load(audio)
pygame.mixer.music.play(-1)

audio_file = open_audio_stream()
sampling_rate = audio_file.samplerate

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Get current playback time in milliseconds from Pygame mixer
    # (returns -1 if music isn't playing)
    current_time_ms = pygame.mixer.music.get_pos()
    
    if current_time_ms >= 0:
        # Convert milliseconds to frame index
        target_frame = int((current_time_ms / 1000.0) * sampling_rate)
        
        # Read the exact chunk corresponding to the music's current timestamp
        frequencies, amplitudes = read_chunk_at_position(audio_file, target_frame)
        
        if frequencies is not None and amplitudes is not None:
            draw_visualizer(screen, frequencies, amplitudes)

    clock.tick(144)

pygame.quit()