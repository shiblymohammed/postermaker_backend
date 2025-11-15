import random
import string
from django.db import models
from cloudinary.models import CloudinaryField


class Campaign(models.Model):
    name = models.CharField(max_length=100, default='Untitled Campaign', help_text="Campaign name (e.g., 'Summer Sale', 'Wedding 2024')")
    code = models.CharField(max_length=6, unique=True, db_index=True)
    frame_image = CloudinaryField('image', folder='frames/', null=True, blank=True)  # Keep for backward compatibility
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def slug(self):
        """Generate URL-friendly slug: campaignname-CODE"""
        # Convert name to lowercase, replace spaces with hyphens, remove special chars
        import re
        name_slug = re.sub(r'[^a-z0-9]+', '-', self.name.lower()).strip('-')
        return f"{name_slug}-{self.code}"
    
    @staticmethod
    def generate_unique_code():
        """Generate a unique 6-character alphanumeric code."""
        # Use uppercase letters and digits, excluding ambiguous characters
        characters = string.ascii_uppercase + string.digits
        characters = characters.replace('O', '').replace('I', '')  # Remove O and I to avoid confusion with 0 and 1
        
        max_attempts = 10
        for _ in range(max_attempts):
            code = ''.join(random.choices(characters, k=6))
            if not Campaign.objects.filter(code=code).exists():
                return code
        
        # If we couldn't generate a unique code after max_attempts, raise an error
        raise ValueError("Unable to generate unique code after maximum attempts")


class CampaignFrame(models.Model):
    """Multiple frames for a campaign"""
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='frames'
    )
    frame_image = CloudinaryField('image', folder='frames/')
    name = models.CharField(max_length=100, default='Frame')
    is_default = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        
    def __str__(self):
        return f"{self.name} - {self.campaign.name}"
    
    def save(self, *args, **kwargs):
        # If this is set as default, unset other defaults
        if self.is_default:
            CampaignFrame.objects.filter(
                campaign=self.campaign,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class GeneratedImage(models.Model):
    campaign = models.ForeignKey(
        Campaign, 
        on_delete=models.CASCADE, 
        related_name='generated_images'
    )
    frame = models.ForeignKey(
        CampaignFrame,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_images'
    )
    # New 3-layer system
    poster_image = CloudinaryField('image', folder='posters/', blank=True, null=True)  # Background layer
    profile_photo = CloudinaryField('image', folder='profiles/', blank=True, null=True)  # Middle layer (circular)
    generated_image = CloudinaryField('image', folder='generated/')  # Final output
    
    # Profile photo positioning (JSON field for flexibility)
    profile_position = models.JSONField(default=dict, blank=True)  # {x, y, scale, rotation}
    
    # Generation parameters
    output_size = models.CharField(max_length=50, default='square_1080')  # Changed default
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Generated image for {self.campaign.code}"
