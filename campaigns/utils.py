"""
Image processing utilities for FrameGen application.
"""
import os
import uuid
import base64
import requests
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile


def process_base64_image(base64_data):
    """
    Decode base64 image data and return PIL Image.
    
    Args:
        base64_data: Base64 encoded image string (with or without data URL prefix)
    
    Returns:
        PIL Image object
    
    Raises:
        ValueError: If base64 data is invalid or cannot be decoded
    """
    try:
        # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
        if ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]
        
        # Decode base64 string
        image_data = base64.b64decode(base64_data)
        
        # Open as PIL Image
        image = Image.open(BytesIO(image_data))
        
        return image
        
    except Exception as e:
        raise ValueError(f"Invalid base64 image data: {str(e)}")


def download_image_from_url(url):
    """
    Download image from URL (for Cloudinary images).
    
    Args:
        url: Image URL
    
    Returns:
        PIL Image object
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))


def overlay_frame_on_photo(user_photo_path, frame_path_or_url, output_size='instagram_post'):
    """
    Overlay a transparent frame PNG on top of a user's photo.
    
    Args:
        user_photo_path: Path to the user's uploaded photo OR PIL Image object
        frame_path_or_url: Path to the campaign frame PNG OR URL (for Cloudinary)
        output_size: Output size option ('instagram_post', 'instagram_story', 'whatsapp_dp')
    
    Returns:
        str: Relative path to the generated image (from MEDIA_ROOT) OR ContentFile for Cloudinary
    
    Raises:
        ValueError: If images cannot be processed
        IOError: If files cannot be read or written
    """
    try:
        # Size mapping with dimensions
        size_map = {
            'instagram_post': (1080, 1080),
            'instagram_story': (1080, 1920),
            'whatsapp_dp': (500, 500)
        }
        
        # Get target dimensions
        target_size = size_map.get(output_size, (1080, 1080))
        
        # Load user photo (support both file path and PIL Image)
        if isinstance(user_photo_path, Image.Image):
            user_photo = user_photo_path
        else:
            user_photo = Image.open(user_photo_path)
        
        # Load frame (support both local path and URL)
        if isinstance(frame_path_or_url, str) and (frame_path_or_url.startswith('http://') or frame_path_or_url.startswith('https://')):
            # Download from URL (Cloudinary)
            frame = download_image_from_url(frame_path_or_url)
        else:
            # Load from local path
            frame = Image.open(frame_path_or_url)
        
        # Convert user photo to RGB if needed (handle RGBA, P, etc.)
        if user_photo.mode not in ('RGB', 'RGBA'):
            user_photo = user_photo.convert('RGB')
        
        # Resize user photo to target size (already cropped by frontend)
        # Use high-quality LANCZOS resampling
        if user_photo.size != target_size:
            user_photo = user_photo.resize(target_size, Image.Resampling.LANCZOS)
        
        # Ensure frame is in RGBA mode for transparency
        if frame.mode != 'RGBA':
            frame = frame.convert('RGBA')
        
        # Resize frame to match target size if needed
        if frame.size != target_size:
            frame = frame.resize(target_size, Image.Resampling.LANCZOS)
        
        # Create final image with user photo as background
        if user_photo.mode == 'RGBA':
            final_image = user_photo
        else:
            final_image = Image.new('RGBA', target_size)
            final_image.paste(user_photo, (0, 0))
        
        # Overlay frame using alpha channel
        final_image.paste(frame, (0, 0), frame)
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4().hex}.png"
        
        # Check if using Cloudinary
        using_cloudinary = hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE
        
        if using_cloudinary:
            # Save to BytesIO and return as ContentFile for Cloudinary
            buffer = BytesIO()
            final_image.save(buffer, 'PNG', optimize=True, quality=95)
            buffer.seek(0)
            return ContentFile(buffer.getvalue(), name=f"generated/{unique_filename}")
        else:
            # Save to local filesystem
            relative_path = os.path.join('generated', unique_filename)
            full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            
            # Ensure generated directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save result as PNG to preserve transparency with high quality
            final_image.save(full_path, 'PNG', optimize=True, quality=95)
            
            return relative_path
        
    except Exception as e:
        raise ValueError(f"Error processing images: {str(e)}")


def resize_and_crop(image, target_size):
    """
    Resize image to target size with center cropping to maintain aspect ratio.
    
    Args:
        image: PIL Image object
        target_size: Tuple of (width, height)
    
    Returns:
        PIL Image object resized and cropped
    """
    target_width, target_height = target_size
    img_width, img_height = image.size
    
    # Calculate aspect ratios
    target_ratio = target_width / target_height
    img_ratio = img_width / img_height
    
    if img_ratio > target_ratio:
        # Image is wider than target, crop width
        new_height = target_height
        new_width = int(new_height * img_ratio)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center crop
        left = (new_width - target_width) // 2
        resized = resized.crop((left, 0, left + target_width, target_height))
    else:
        # Image is taller than target, crop height
        new_width = target_width
        new_height = int(new_width / img_ratio)
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center crop
        top = (new_height - target_height) // 2
        resized = resized.crop((0, top, target_width, top + target_height))
    
    return resized
