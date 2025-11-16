#!/usr/bin/env python
"""
Reset all campaigns and related data
Run: python reset_campaigns.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from campaigns.models import Campaign, CampaignPoster, CampaignFrame, GeneratedImage

print("=" * 60)
print("RESETTING ALL CAMPAIGNS")
print("=" * 60)

# Count existing data
campaign_count = Campaign.objects.count()
poster_count = CampaignPoster.objects.count()
frame_count = CampaignFrame.objects.count()
generated_count = GeneratedImage.objects.count()

print(f"\nCurrent data:")
print(f"  Campaigns: {campaign_count}")
print(f"  Posters: {poster_count}")
print(f"  Frames: {frame_count}")
print(f"  Generated Images: {generated_count}")

if campaign_count == 0:
    print("\nNo campaigns to delete.")
else:
    confirm = input(f"\nAre you sure you want to delete all {campaign_count} campaigns? (yes/no): ")
    
    if confirm.lower() == 'yes':
        # Delete all generated images
        GeneratedImage.objects.all().delete()
        print(f"✓ Deleted {generated_count} generated images")
        
        # Delete all frames
        CampaignFrame.objects.all().delete()
        print(f"✓ Deleted {frame_count} frames")
        
        # Delete all posters
        CampaignPoster.objects.all().delete()
        print(f"✓ Deleted {poster_count} posters")
        
        # Delete all campaigns
        Campaign.objects.all().delete()
        print(f"✓ Deleted {campaign_count} campaigns")
        
        print("\n" + "=" * 60)
        print("ALL CAMPAIGNS DELETED!")
        print("=" * 60)
        print("\nYou can now create new campaigns in the admin panel.")
    else:
        print("\nCancelled. No data was deleted.")

print("\n" + "=" * 60)
