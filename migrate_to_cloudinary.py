#!/usr/bin/env python
"""
Migrate existing local images to Cloudinary
Run: python migrate_to_cloudinary.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.files import File
from campaigns.models import CampaignFrame
import cloudinary.uploader

print("=" * 60)
print("MIGRATE LOCAL IMAGES TO CLOUDINARY")
print("=" * 60)

frames = CampaignFrame.objects.all()
total = frames.count()
migrated = 0
skipped = 0
errors = 0

print(f"\nFound {total} frames to check\n")

for frame in frames:
    if not frame.frame_image:
        print(f"⊘ Skipping {frame.name} - No image")
        skipped += 1
        continue
    
    # Check if already on Cloudinary
    if 'cloudinary.com' in frame.frame_image.url:
        print(f"✓ Skipping {frame.name} - Already on Cloudinary")
        skipped += 1
        continue
    
    print(f"→ Migrating {frame.name} ({frame.campaign.name})...")
    
    try:
        # Get the local file path
        local_path = frame.frame_image.path
        
        if not os.path.exists(local_path):
            print(f"  ✗ File not found: {local_path}")
            errors += 1
            continue
        
        # Upload to Cloudinary
        with open(local_path, 'rb') as f:
            # Save will automatically upload to Cloudinary
            frame.frame_image.save(
                os.path.basename(local_path),
                File(f),
                save=True
            )
        
        print(f"  ✓ Migrated successfully")
        print(f"  New URL: {frame.frame_image.url}")
        migrated += 1
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        errors += 1

print("\n" + "=" * 60)
print("MIGRATION COMPLETE")
print("=" * 60)
print(f"Total frames: {total}")
print(f"Migrated: {migrated}")
print(f"Skipped: {skipped}")
print(f"Errors: {errors}")
print("=" * 60)

if migrated > 0:
    print("\n✓ Images successfully migrated to Cloudinary!")
    print("You can now delete the local /media folder if needed.")
elif skipped == total:
    print("\n✓ All images are already on Cloudinary!")
else:
    print("\n⚠ Some images could not be migrated. Check errors above.")
