#!/usr/bin/env python
"""
Quick script to check Cloudinary configuration
Run: python check_cloudinary.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

print("=" * 50)
print("CLOUDINARY CONFIGURATION CHECK")
print("=" * 50)

print(f"\nCLOUD_NAME: {settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', 'NOT SET')}")
print(f"API_KEY: {settings.CLOUDINARY_STORAGE.get('API_KEY', 'NOT SET')}")
print(f"API_SECRET: {'***' + settings.CLOUDINARY_STORAGE.get('API_SECRET', '')[-4:] if settings.CLOUDINARY_STORAGE.get('API_SECRET') else 'NOT SET'}")

print(f"\nDEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'NOT SET')}")

if hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE:
    print("\n✓ Cloudinary is ENABLED")
else:
    print("\n✗ Cloudinary is NOT ENABLED (using local storage)")

# Test Cloudinary connection
if settings.CLOUDINARY_STORAGE.get('CLOUD_NAME'):
    try:
        import cloudinary
        import cloudinary.api
        
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
            api_key=settings.CLOUDINARY_STORAGE['API_KEY'],
            api_secret=settings.CLOUDINARY_STORAGE['API_SECRET']
        )
        
        # Try to ping Cloudinary
        result = cloudinary.api.ping()
        print(f"\n✓ Cloudinary connection: SUCCESS")
        print(f"Status: {result.get('status', 'unknown')}")
    except Exception as e:
        print(f"\n✗ Cloudinary connection: FAILED")
        print(f"Error: {str(e)}")

# Check existing frames
from campaigns.models import CampaignFrame
frames = CampaignFrame.objects.all()[:3]

print(f"\n{'=' * 50}")
print(f"SAMPLE FRAME URLS (first 3)")
print(f"{'=' * 50}")

for frame in frames:
    print(f"\nFrame: {frame.name}")
    print(f"Campaign: {frame.campaign.name}")
    if frame.frame_image:
        print(f"Image URL: {frame.frame_image.url}")
    else:
        print("No image uploaded")

print(f"\n{'=' * 50}")
