import pygame

previous_heights = {}

def draw_visualizer(screen, frequencies, amplitudes):
    screen.fill("black")

    screen_width, screen_height = 800, 600
    num_bars = len(amplitudes)
    
    if num_bars > 0:
        # Calculate precise exact width allocated per bar across the full screen width
        column_width = screen_width / num_bars
        bar_width = max(2, column_width * 0.85) # 85% width, 15% gap
        
        for idx, am in enumerate(amplitudes):
            target_height = am * 1200
            
            prev_h = previous_heights.get(idx, 0)
            if target_height > prev_h:
                bar_height = target_height
            else:
                bar_height = prev_h * 0.75 + target_height * 0.25
            
            previous_heights[idx] = bar_height

            final_height = max(4, bar_height)
            y_position = screen_height - final_height
            
            # Position precisely using floating-point math so it hits the exact edge
            x_position = idx * column_width

            red = min(255, idx * 8)
            green = min(255, max(0, int(255 - abs(idx - (num_bars/2)) * 6)))
            blue = max(0, 255 - (idx * 6))
            bar_color = (red, green, blue)

            pygame.draw.rect(
                surface=screen, 
                color=bar_color, 
                rect=(x_position, y_position, bar_width, final_height)
            )

    pygame.display.flip()