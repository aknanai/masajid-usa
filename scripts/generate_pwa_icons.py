"""Generate PWA icons for Masajid USA"""
from PIL import Image, ImageDraw
import os

def create_mosque_icon(size, maskable=False):
    """Create a mosque dome icon with crescent & star"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors from site theme
    primary = (26, 95, 74)      # #1a5f4a
    primary_dark = (13, 61, 46)  # #0d3d2e
    accent = (201, 162, 39)     # #c9a227
    white = (255, 255, 255)
    
    if maskable:
        # Fill background for maskable icons (safe zone is 80% of canvas)
        padding = size * 0.1
        draw.rounded_rectangle(
            [padding, padding, size - padding, size - padding],
            radius=size * 0.12,
            fill=primary
        )
    else:
        # Transparent background for non-maskable
        pass
    
    cx, cy = size // 2, size // 2
    r = size * 0.42
    
    # Main dome (inverted semi-circle)
    dome_bbox = [cx - r, cy - r * 0.1, cx + r, cy + r * 1.1]
    draw.pieslice(dome_bbox, 180, 0, fill=primary_dark, outline=None)
    
    # Inner dome highlight
    inner_r = r * 0.82
    inner_bbox = [cx - inner_r, cy - r * 0.05, cx + inner_r, cy + r * 1.0]
    draw.pieslice(inner_bbox, 180, 0, fill=primary, outline=None)
    
    # Minaret on left
    minaret_x = cx - r * 0.85
    minaret_w = size * 0.04
    minaret_h = size * 0.30
    draw.rectangle(
        [minaret_x - minaret_w/2, cy - minaret_h, minaret_x + minaret_w/2, cy + r * 0.2],
        fill=primary_dark
    )
    # Minaret top (small ball)
    ball_r = minaret_w * 1.2
    draw.ellipse(
        [minaret_x - ball_r, cy - minaret_h - ball_r*2, minaret_x + ball_r, cy - minaret_h],
        fill=accent
    )
    
    # Minaret on right
    minaret_x2 = cx + r * 0.85
    draw.rectangle(
        [minaret_x2 - minaret_w/2, cy - minaret_h * 0.85, minaret_x2 + minaret_w/2, cy + r * 0.2],
        fill=primary_dark
    )
    draw.ellipse(
        [minaret_x2 - ball_r, cy - minaret_h*0.85 - ball_r*2, minaret_x2 + ball_r, cy - minaret_h*0.85],
        fill=accent
    )
    
    # Crescent moon
    moon_r = size * 0.11
    moon_cx = cx + r * 0.55
    moon_cy = cy - r * 0.55
    draw.ellipse(
        [moon_cx - moon_r, moon_cy - moon_r, moon_cx + moon_r, moon_cy + moon_r],
        fill=accent
    )
    # Inner cutout for crescent shape
    cut_r = moon_r * 0.75
    cut_offset = moon_r * 0.25
    draw.ellipse(
        [moon_cx - cut_r + cut_offset, moon_cy - cut_r - cut_offset, 
         moon_cx + cut_r + cut_offset, moon_cy + cut_r - cut_offset],
        fill=(255, 255, 255, 0) if not maskable else primary
    )
    
    # Star
    star_size = size * 0.04
    star_cx = moon_cx + moon_r * 0.4
    star_cy = moon_cy - moon_r * 0.3
    draw.polygon([
        (star_cx, star_cy - star_size),
        (star_cx + star_size * 0.3, star_cy - star_size * 0.3),
        (star_cx + star_size, star_cy),
        (star_cx + star_size * 0.3, star_cy + star_size * 0.3),
        (star_cx, star_cy + star_size),
        (star_cx - star_size * 0.3, star_cy + star_size * 0.3),
        (star_cx - star_size, star_cy),
        (star_cx - star_size * 0.3, star_cy - star_size * 0.3),
    ], fill=accent)
    
    # Base line
    base_y = cy + r * 0.15
    draw.rectangle(
        [cx - r * 0.7, base_y, cx + r * 0.7, base_y + size * 0.02],
        fill=primary_dark
    )
    
    # Door
    door_w = size * 0.10
    door_h = size * 0.14
    door_x = cx - door_w / 2
    door_y = cy + r * 0.1
    draw.rounded_rectangle(
        [door_x, door_y, door_x + door_w, door_y + door_h],
        radius=size * 0.02,
        fill=accent
    )
    
    return img

def main():
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'icons')
    os.makedirs(out_dir, exist_ok=True)
    
    sizes = [96, 192, 512]
    
    for size in sizes:
        icon = create_mosque_icon(size, maskable=False)
        path = os.path.join(out_dir, f'icon-{size}x{size}.png')
        icon.save(path, 'PNG')
        print(f'Created: {path} ({size}x{size})')
        
        maskable = create_mosque_icon(size, maskable=True)
        maskable_path = os.path.join(out_dir, f'icon-{size}x{size}-maskable.png')
        maskable.save(maskable_path, 'PNG')
        print(f'Created: {maskable_path} (maskable, {size}x{size})')

if __name__ == '__main__':
    main()
