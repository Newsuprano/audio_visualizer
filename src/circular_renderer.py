import pygame
import math

previous_heights = {}

def draw_circular_visualizer(screen, frequencies, amplitudes):
    screen.fill("black")

    screen_width, screen_height = 800, 600
    center_x = screen_width // 2
    center_y = screen_height // 2
    
    num_bars = len(amplitudes)
    if num_bars == 0:
        pygame.display.flip()
        return

    # Base radius of the inner circle where the bars sprout from
    inner_radius = 120
    max_bar_length = 300

    angle_step = 360 / num_bars

    for idx, am in enumerate(amplitudes):
        target_length = am * max_bar_length
        
        # Smooth out the decay movement just like before
        prev_h = previous_heights.get(idx, 0)
        if target_length > prev_h:
            bar_length = target_length
        else:
            bar_length = prev_h * 0.75 + target_length * 0.25
        
        previous_heights[idx] = bar_length

        # Ensure a tiny minimum floor so the circle stays complete
        final_length = max(3, bar_length)
        
        # Calculate angle in radians
        angle_deg = idx * angle_step
        angle_rad = math.radians(angle_deg)
        
        # Inner starting point (on the circumference of the inner circle)
        start_x = center_x + math.cos(angle_rad) * inner_radius
        start_y = center_y + math.sin(angle_rad) * inner_radius
        
        # Outer ending point (extending outward based on audio amplitude)
        outer_radius = inner_radius + final_length
        end_x = center_x + math.cos(angle_rad) * outer_radius
        end_y = center_y + math.sin(angle_rad) * outer_radius

        # Color gradient looping smoothly around the circle
        red = min(255, idx * 4)
        green = min(255, max(0, int(255 - abs(idx - (num_bars/2)) * 3)))
        blue = max(0, 255 - (idx * 4))
        bar_color = (red, green, blue)

        # Draw each bar as a thick line radiating outward
        pygame.draw.line(screen, bar_color, (start_x, start_y), (end_x, end_y), width=3)

    pygame.display.flip()