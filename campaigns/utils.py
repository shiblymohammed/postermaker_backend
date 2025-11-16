"""
Image processing utilities for FrameGen application.
"""
import os
import uuid
import base64
import requests
from io import BytesIO
from PIL import Image, ImageDraw
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


def create_circular_mask(size):
    """
    Create a circular mask for profile photo.
    
    Args:
        size: Tuple of (width, height)
    
    Returns:
        PIL Image mask (L mode)
    """
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    return mask


def create_rounded_rectangle_mask(size, radius):
    """
    Create a rounded rectangle mask for profile photo.
    
    Args:
        size: Tuple of (width, height)
        radius: Corner radius in pixels
    
    Returns:
        PIL Image mask (L mode)
    """
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0) + size, radius=radius, fill=255)
    return mask


def create_three_layer_poster(
    poster_image_path_or_url,
    profile_image_path_or_url,
    frame_path_or_url,
    profile_position,
    output_size='square_1080',
    crop_shape='circle'
):
    """
    Create a 3-layer poster: poster background + profile (with crop shape) + frame overlay.
    
    Args:
        poster_image_path_or_url: Path or URL to poster background
        profile_image_path_or_url: Path or URL to profile photo
        frame_path_or_url: Path or URL to frame overlay
        profile_position: Dict with {x, y, scale, rotation}
        output_size: Output size option
        crop_shape: Shape to crop profile ('circle', 'square', 'rectangle')
    
    Returns:
        ContentFile for Cloudinary or path string for local storage
    """
    try:
        # Load poster background first to get its size
        if isinstance(poster_image_path_or_url, Image.Image):
            poster = poster_image_path_or_url
        elif isinstance(poster_image_path_or_url, str) and (poster_image_path_or_url.startswith('http://') or poster_image_path_or_url.startswith('https://')):
            poster = download_image_from_url(poster_image_path_or_url)
        else:
            poster = Image.open(poster_image_path_or_url)
        
        # Use poster size as target size (output matches poster dimensions exactly)
        # This ensures the output has the same size and aspect ratio as the original poster
        target_size = poster.size

        
        # Convert poster to RGB/RGBA if needed
        if poster.mode not in ('RGB', 'RGBA'):
            poster = poster.convert('RGB')
        
        # Load profile photo
        if isinstance(profile_image_path_or_url, Image.Image):
            profile = profile_image_path_or_url
        elif isinstance(profile_image_path_or_url, str) and (profile_image_path_or_url.startswith('http://') or profile_image_path_or_url.startswith('https://')):
            profile = download_image_from_url(profile_image_path_or_url)
        else:
            profile = Image.open(profile_image_path_or_url)
        
        # Load frame
        if isinstance(frame_path_or_url, Image.Image):
            frame = frame_path_or_url
        elif isinstance(frame_path_or_url, str) and (frame_path_or_url.startswith('http://') or frame_path_or_url.startswith('https://')):
            frame = download_image_from_url(frame_path_or_url)
        else:
            frame = Image.open(frame_path_or_url)

        
        # Create base canvas
        canvas = Image.new('RGBA', target_size)
        if poster.mode == 'RGBA':
            canvas.paste(poster, (0, 0))
        else:
            canvas.paste(poster, (0, 0))
        
        # Process profile photo
        if profile.mode not in ('RGB', 'RGBA'):
            profile = profile.convert('RGBA')
        
        # Get profile position parameters
        x = profile_position.get('x', target_size[0] // 2)
        y = profile_position.get('y', target_size[1] // 2)
        scale = profile_position.get('scale', 1.0)
        rotation = profile_position.get('rotation', 0)
        
        # Calculate profile size based on crop shape
        base_profile_size = int(min(target_size) * 0.3)
        
        if crop_shape == 'rectangle':
            # Portrait rectangle (taller than wide) - reduced height
            profile_width = int(base_profile_size * scale)
            profile_height = int(base_profile_size * scale * 1.3)
        else:
            # For circle and square
            profile_width = int(base_profile_size * scale)
            profile_height = int(base_profile_size * scale)
        
        # Resize profile photo to cover the target dimensions (crop, don't stretch)
        # Calculate scale to cover the target area
        scale_x = profile_width / profile.size[0]
        scale_y = profile_height / profile.size[1]
        scale_factor = max(scale_x, scale_y)  # Use max to cover, not contain
        
        # Calculate new size
        new_width = int(profile.size[0] * scale_factor)
        new_height = int(profile.size[1] * scale_factor)
        
        # Resize profile
        profile_resized = profile.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crop to exact dimensions (center crop)
        left = (new_width - profile_width) // 2
        top = (new_height - profile_height) // 2
        profile_resized = profile_resized.crop((left, top, left + profile_width, top + profile_height))
        
        # Rotate if needed
        if rotation != 0:
            profile_resized = profile_resized.rotate(rotation, expand=False)
        
        # Create mask based on crop shape
        if crop_shape == 'circle':
            mask = create_circular_mask((profile_width, profile_height))
        elif crop_shape == 'square':
            # Square mask with rounded corners (10% radius)
            radius = int(profile_width * 0.1)
            mask = create_rounded_rectangle_mask((profile_width, profile_height), radius)
        elif crop_shape == 'rectangle':
            # Portrait rectangle mask with rounded corners (10% radius)
            radius = int(profile_width * 0.1)
            mask = create_rounded_rectangle_mask((profile_width, profile_height), radius)
        else:
            # Default to circular
            mask = create_circular_mask((profile_width, profile_height))
        
        # Apply mask to profile
        profile_masked = Image.new('RGBA', (profile_width, profile_height), (0, 0, 0, 0))
        profile_masked.paste(profile_resized, (0, 0))
        profile_masked.putalpha(mask)
        
        # Calculate position (x, y are center coordinates)
        paste_x = int(x - profile_width // 2)
        paste_y = int(y - profile_height // 2)
        
        # Paste masked profile onto canvas
        canvas.paste(profile_masked, (paste_x, paste_y), profile_masked)
        
        # Resize and overlay frame to match poster size exactly
        # Frame should be designed at the same aspect ratio as posters
        if frame.mode != 'RGBA':
            frame = frame.convert('RGBA')

        
        if frame.size != target_size:
            # Resize frame to exact poster dimensions
            # Use BILINEAR for faster processing (LANCZOS is slower but higher quality)
            frame = frame.resize(target_size, Image.Resampling.BILINEAR)

        
        # Composite frame on top
        canvas.paste(frame, (0, 0), frame)
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4().hex}.png"
        
        # Check if using Cloudinary
        using_cloudinary = hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE

        
        # Convert to RGB for JPEG (faster than PNG)
        if canvas.mode == 'RGBA':
            # Create white background for transparency
            rgb_canvas = Image.new('RGB', canvas.size, (255, 255, 255))
            rgb_canvas.paste(canvas, mask=canvas.split()[3])  # Use alpha channel as mask
            canvas = rgb_canvas
        
        # Generate unique filename with jpg extension
        unique_filename = f"{uuid.uuid4().hex}.jpg"
        
        if using_cloudinary:
            # Save to BytesIO as JPEG for faster processing
            buffer = BytesIO()
            canvas.save(buffer, 'JPEG', optimize=True, quality=85)
            buffer.seek(0)
            return ContentFile(buffer.getvalue(), name=f"generated/{unique_filename}")
        else:
            # Save to local filesystem as JPEG
            buffer = BytesIO()
            canvas.save(buffer, 'JPEG', optimize=True, quality=85)
            buffer.seek(0)
            return ContentFile(buffer.getvalue(), name=f"generated/{unique_filename}")
        
    except Exception as e:
        raise ValueError(f"Error creating 3-layer poster: {str(e)}")


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
