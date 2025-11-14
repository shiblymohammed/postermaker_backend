"""
One-time script to migrate existing campaign frames to CampaignFrame model
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from campaigns.models import Campaign, CampaignFrame

def migrate_frames():
    """Migrate existing frame_image to CampaignFrame"""
    migrated = 0
    skipped = 0
    
    for campaign in Campaign.objects.all():
        if campaign.frame_image:
            # Check if already migrated
            if not campaign.frames.exists():
                CampaignFrame.objects.create(
                    campaign=campaign,
                    frame_image=campaign.frame_image,
                    name="Default Frame",
                    is_default=True,
                    order=0
                )
                migrated += 1
                print(f"✓ Migrated frame for campaign: {campaign.name}")
            else:
                skipped += 1
                print(f"- Skipped (already has frames): {campaign.name}")
        else:
            print(f"⚠ No frame for campaign: {campaign.name}")
    
    print(f"\n{'='*50}")
    print(f"Migration complete!")
    print(f"Migrated: {migrated}")
    print(f"Skipped: {skipped}")
    print(f"{'='*50}")

if __name__ == "__main__":
    migrate_frames()
