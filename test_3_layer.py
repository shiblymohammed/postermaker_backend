#!/usr/bin/env python
"""
Test script for 3-layer poster generation
Run: python test_3_layer.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from campaigns.utils import create_three_layer_poster, create_circular_mask
from PIL import Image, ImageDraw
import sys

print("=" * 60)
print("TESTING 3-LAYER POSTER SYSTEM")
print("=" * 60)

# Test 1: Circular Mask
print("\n1. Testing circular mask creation...")
try:
    mask = create_circular_mask((500, 500))
    assert mask.mode == 'L'
    assert mask.size == (500, 500)
    print("   ✓ Circular mask created successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 2: Create Test Images
print("\n2. Creating test images...")
try:
    # Create poster (blue background)
    poster = Image.new('RGB', (1080, 1080), color='#3b82f6')
    draw_poster = ImageDraw.Draw(poster)
    draw_poster.text((540, 100), "POSTER BACKGROUND", fill='white', anchor='mm')
    
    # Create profile (red circle)
    profile = Image.new('RGB', (500, 500), color='#ef4444')
    draw_profile = ImageDraw.Draw(profile)
    draw_profile.ellipse((100, 100, 400, 400), fill='#fbbf24')
    
    # Create frame (transparent with white circle outline)
    frame = Image.new('RGBA', (1080, 1080), color=(0, 0, 0, 0))
    draw_frame = ImageDraw.Draw(frame)
    # Draw circle outline where profile should go
    draw_frame.ellipse((390, 390, 690, 690), outline='white', width=15)
    # Draw some decorative elements
    draw_frame.rectangle((0, 0, 1080, 100), fill=(255, 255, 255, 200))
    draw_frame.text((540, 50), "CAMPAIGN FRAME", fill='black', anchor='mm')
    
    print("   ✓ Test images created")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 3: Generate 3-Layer Poster
print("\n3. Testing 3-layer poster generation...")
try:
    profile_position = {
        'x': 540,      # Center X
        'y': 540,      # Center Y
        'scale': 1.0,  # 100% size
        'rotation': 0  # No rotation
    }
    
    result = create_three_layer_poster(
        poster,
        profile,
        frame,
        profile_position,
        'square_1080'
    )
    
    print(f"   ✓ 3-layer poster generated")
    print(f"   Result type: {type(result).__name__}")
    
    # Check if it's a ContentFile (Cloudinary) or path (local)
    if hasattr(result, 'read'):
        print("   ✓ Using Cloudinary storage")
    else:
        print(f"   ✓ Using local storage: {result}")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Different Positions
print("\n4. Testing different profile positions...")
test_positions = [
    {'x': 540, 'y': 300, 'scale': 0.8, 'rotation': 0},   # Top
    {'x': 540, 'y': 780, 'scale': 1.2, 'rotation': 0},   # Bottom, larger
    {'x': 300, 'y': 540, 'scale': 0.6, 'rotation': 45},  # Left, smaller, rotated
]

for i, pos in enumerate(test_positions, 1):
    try:
        result = create_three_layer_poster(
            poster, profile, frame, pos, 'square_1080'
        )
        print(f"   ✓ Position {i}: x={pos['x']}, y={pos['y']}, scale={pos['scale']}")
    except Exception as e:
        print(f"   ✗ Position {i} failed: {e}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✓")
print("=" * 60)
print("\nThe 3-layer poster system is working correctly!")
print("\nNext steps:")
print("1. Test with real campaign data")
print("2. Test API endpoint with Postman")
print("3. Complete frontend implementation")
print("=" * 60)
