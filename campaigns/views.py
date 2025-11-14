import os
import uuid
from django.conf import settings
from django.db import models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer, UserSerializer, CampaignSerializer, CampaignFrameSerializer, GeneratedImageSerializer
from .models import Campaign, CampaignFrame, GeneratedImage
from .utils import overlay_frame_on_photo, process_base64_image, download_image_from_url


class AdminLoginView(APIView):
    """
    Admin login endpoint that returns JWT tokens on successful authentication.
    
    POST /api/admin/login/
    Request body: {"username": "string", "password": "string"}
    Response: {"token": "string", "user": {"id": int, "username": "string"}}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            # Serialize user data
            user_data = UserSerializer(user).data
            
            return Response({
                'token': access_token,
                'user': user_data
            }, status=status.HTTP_200_OK)
        
        # Return 401 for invalid credentials
        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)



class CampaignCreateView(APIView):
    """
    Campaign creation endpoint for admins to upload PNG frames and generate campaign codes.
    
    POST /api/admin/campaign/
    Request: Multipart form data with 'name' (string) and 'frame' file (PNG only)
    Response: {"id": int, "name": "string", "code": "string", "slug": "string", "frame_url": "string", "created_at": "datetime"}
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if name is provided
        name = request.data.get('name', '').strip()
        if not name:
            return Response({
                'error': 'Campaign name is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if frame file is provided
        if 'frame' not in request.FILES:
            return Response({
                'error': 'No frame file provided. Please upload a PNG file.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        frame_file = request.FILES['frame']
        
        # Validate file format (PNG only)
        if not frame_file.name.lower().endswith('.png'):
            return Response({
                'error': 'Invalid file format. Only PNG files are allowed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check content type if available
        if hasattr(frame_file, 'content_type') and frame_file.content_type:
            if frame_file.content_type != 'image/png':
                return Response({
                    'error': 'Invalid file format. Only PNG files are allowed.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Generate unique code
            unique_code = Campaign.generate_unique_code()
            
            # Create campaign instance
            campaign = Campaign(
                name=name,
                code=unique_code,
                frame_image=frame_file  # Keep for backward compatibility
            )
            campaign.save()
            
            # Create default frame
            CampaignFrame.objects.create(
                campaign=campaign,
                frame_image=frame_file,
                name="Default Frame",
                is_default=True,
                order=0
            )
            
            # Serialize and return response
            serializer = CampaignSerializer(campaign, context={'request': request})
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except ValueError as e:
            # Handle code generation failure
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            # Handle any other errors
            return Response({
                'error': f'Failed to create campaign: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CampaignListView(APIView):
    """
    Campaign list endpoint for admins to view all campaigns.
    
    GET /api/admin/campaigns/
    Response: {"campaigns": [{"id": int, "code": "string", "frame_url": "string", "created_at": "datetime", "is_active": bool}]}
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Retrieve all campaigns ordered by created_at descending
        campaigns = Campaign.objects.all().order_by('-created_at')
        
        # Serialize campaigns
        serializer = CampaignSerializer(campaigns, many=True, context={'request': request})
        
        return Response({
            'campaigns': serializer.data
        }, status=status.HTTP_200_OK)


class CampaignManageView(APIView):
    """
    Campaign management endpoint for admins to update or delete campaigns.
    
    GET /api/admin/campaign/<id>/
    Response: {"id": int, "name": "string", "code": "string", "slug": "string", "frame_url": "string", "frames": [...], "created_at": "datetime", "is_active": bool}
    
    PUT /api/admin/campaign/<id>/
    Request: Multipart form data with optional 'name' (string) and 'frame' file (PNG only)
    Response: {"id": int, "name": "string", "code": "string", "slug": "string", "frame_url": "string", "created_at": "datetime", "is_active": bool}
    
    DELETE /api/admin/campaign/<id>/
    Response: {"message": "Campaign deleted successfully"}
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get campaign details"""
        try:
            campaign = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return Response({
                'error': 'Campaign not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize and return campaign data
        serializer = CampaignSerializer(campaign, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, pk):
        """Update campaign name and/or frame"""
        try:
            campaign = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return Response({
                'error': 'Campaign not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update name if provided
        name = request.data.get('name')
        if name:
            campaign.name = name.strip()
        
        # Update frame if provided
        if 'frame' in request.FILES:
            frame_file = request.FILES['frame']
            
            # Validate file format (PNG only)
            if not frame_file.name.lower().endswith('.png'):
                return Response({
                    'error': 'Invalid file format. Only PNG files are allowed.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check content type if available
            if hasattr(frame_file, 'content_type') and frame_file.content_type:
                if frame_file.content_type != 'image/png':
                    return Response({
                        'error': 'Invalid file format. Only PNG files are allowed.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete old frame file
            if campaign.frame_image:
                old_frame_path = campaign.frame_image.path
                if os.path.exists(old_frame_path):
                    os.remove(old_frame_path)
            
            campaign.frame_image = frame_file
        
        try:
            campaign.save()
            
            # Serialize and return response
            serializer = CampaignSerializer(campaign, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': f'Failed to update campaign: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, pk):
        """Delete campaign and all associated files"""
        try:
            campaign = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return Response({
                'error': 'Campaign not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Delete frame file
            if campaign.frame_image:
                frame_path = campaign.frame_image.path
                if os.path.exists(frame_path):
                    os.remove(frame_path)
            
            # Delete all generated images for this campaign
            for generated_image in campaign.generated_images.all():
                # Delete user photo
                if generated_image.user_photo:
                    user_photo_path = generated_image.user_photo.path
                    if os.path.exists(user_photo_path):
                        os.remove(user_photo_path)
                
                # Delete generated image
                if generated_image.generated_image:
                    generated_path = generated_image.generated_image.path
                    if os.path.exists(generated_path):
                        os.remove(generated_path)
            
            # Delete campaign (cascade will delete GeneratedImage records)
            campaign_name = campaign.name
            campaign.delete()
            
            return Response({
                'message': f'Campaign "{campaign_name}" deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': f'Failed to delete campaign: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CampaignDetailView(APIView):
    """
    Campaign retrieval endpoint for users to get campaign information by code.
    No authentication required.
    
    GET /api/campaign/<code>/
    Response: {"name": "string", "code": "string", "slug": "string", "frame_url": "string", "is_active": bool}
    """
    permission_classes = [AllowAny]
    
    def get(self, request, code):
        try:
            # Retrieve campaign by code
            campaign = Campaign.objects.get(code=code)
            
            # Return 404 if campaign is inactive
            if not campaign.is_active:
                return Response({
                    'error': 'Campaign not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Serialize and return campaign data
            serializer = CampaignSerializer(campaign, context={'request': request})
            
            return Response({
                'name': serializer.data['name'],
                'code': serializer.data['code'],
                'slug': serializer.data['slug'],
                'frame_url': serializer.data['frame_url'],
                'is_active': serializer.data['is_active']
            }, status=status.HTTP_200_OK)
        
        except Campaign.DoesNotExist:
            # Return 404 if campaign not found
            return Response({
                'error': 'Campaign not found'
            }, status=status.HTTP_404_NOT_FOUND)


class CampaignBySlugView(APIView):
    """
    Campaign retrieval endpoint for users to get campaign information by slug.
    No authentication required.
    
    GET /api/campaign/slug/<slug>/
    Response: {"name": "string", "code": "string", "slug": "string", "frame_url": "string", "is_active": bool}
    """
    permission_classes = [AllowAny]
    
    def get(self, request, slug):
        try:
            # Extract code from slug (last 6 characters after last hyphen)
            parts = slug.split('-')
            if len(parts) < 2:
                return Response({
                    'error': 'Invalid campaign URL'
                }, status=status.HTTP_404_NOT_FOUND)
            
            code = parts[-1]
            
            # Retrieve campaign by code
            campaign = Campaign.objects.get(code=code)
            
            # Return 404 if campaign is inactive
            if not campaign.is_active:
                return Response({
                    'error': 'Campaign not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify the full slug matches (optional, for URL consistency)
            if campaign.slug != slug:
                # Redirect to correct slug or just accept it
                pass
            
            # Get all frames for this campaign
            frames = campaign.frames.all()
            frames_data = [{
                'id': frame.id,
                'name': frame.name,
                'frame_url': request.build_absolute_uri(frame.frame_image.url) if frame.frame_image else None
            } for frame in frames]
            
            return Response({
                'id': campaign.id,
                'name': campaign.name,
                'code': campaign.code,
                'description': f'Create stunning campaign posters for {campaign.name}',
                'frames': frames_data
            }, status=status.HTTP_200_OK)
        
        except Campaign.DoesNotExist:
            # Return 404 if campaign not found
            return Response({
                'error': 'Campaign not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Invalid campaign URL: {str(e)}'
            }, status=status.HTTP_404_NOT_FOUND)



class GenerateImageView(APIView):
    """
    Image generation endpoint for users to upload photos and generate framed images.
    No authentication required.
    
    POST /api/generate/
    Request: Multipart form data with 'code' (string) and either:
      - 'photo' (file) - traditional file upload
      - 'photo_data' (string) - base64 encoded image data
    Optional: 'size' (string) - output size option
    Response: {"generated_image_url": "string", "message": "Image generated successfully"}
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Validate required fields
        code = request.data.get('code')
        
        if not code:
            return Response({
                'error': 'Campaign code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check for either photo file or photo_data (base64)
        photo_file = request.FILES.get('photo')
        photo_data = request.data.get('photo_data')
        
        if not photo_file and not photo_data:
            return Response({
                'error': 'Photo file or photo_data is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate campaign code exists and is active
        try:
            campaign = Campaign.objects.get(code=code)
            
            if not campaign.is_active:
                return Response({
                    'error': 'Invalid campaign code'
                }, status=status.HTTP_404_NOT_FOUND)
        
        except Campaign.DoesNotExist:
            return Response({
                'error': 'Invalid campaign code'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate file upload if provided
        if photo_file:
            valid_image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            valid_content_types = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp']
            
            file_extension = os.path.splitext(photo_file.name)[1].lower()
            
            if file_extension not in valid_image_extensions:
                return Response({
                    'error': 'Invalid image format. Supported formats: JPG, PNG, GIF, BMP, WEBP'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check content type if available
            if hasattr(photo_file, 'content_type') and photo_file.content_type:
                if photo_file.content_type not in valid_content_types:
                    return Response({
                        'error': 'Invalid image format. Supported formats: JPG, PNG, GIF, BMP, WEBP'
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get optional parameters
        frame_id = request.data.get('frame_id')
        output_size = request.data.get('size', 'instagram_post')
        
        # Validate output size
        valid_sizes = ['instagram_post', 'instagram_story', 'whatsapp_dp']
        if output_size not in valid_sizes:
            return Response({
                'error': f'Invalid size option. Valid options: {", ".join(valid_sizes)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get frame to use
        frame = None
        if frame_id:
            try:
                frame = campaign.frames.get(pk=frame_id)
            except CampaignFrame.DoesNotExist:
                # Fall back to default frame
                frame = campaign.frames.filter(is_default=True).first() or campaign.frames.first()
        else:
            # Use default frame or first frame
            frame = campaign.frames.filter(is_default=True).first() or campaign.frames.first()
        
        if not frame:
            # Fallback to old frame_image field
            if not campaign.frame_image:
                return Response({
                    'error': 'No frame available for this campaign'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Process image based on input type
            if photo_data:
                # Handle base64 image data
                try:
                    user_image = process_base64_image(photo_data)
                except ValueError as e:
                    return Response({
                        'error': f'Invalid image data: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Get frame path or URL
                frame_image = frame.frame_image if frame else campaign.frame_image
                
                # Check if using Cloudinary (URL) or local storage (path)
                if 'cloudinary.com' in frame_image.url:
                    frame_path_or_url = frame_image.url
                else:
                    frame_path_or_url = frame_image.path
                
                # Process image directly (no need to save user photo)
                try:
                    generated_result = overlay_frame_on_photo(
                        user_image, 
                        frame_path_or_url, 
                        output_size
                    )
                except ValueError as e:
                    return Response({
                        'error': f'Image processing failed: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Create GeneratedImage record without user_photo
                generated_image = GeneratedImage(
                    campaign=campaign,
                    frame=frame,
                    output_size=output_size
                )
                
                # Save the generated image (handles both Cloudinary ContentFile and local path)
                if hasattr(generated_result, 'read'):
                    # It's a ContentFile (Cloudinary)
                    generated_image.generated_image.save(
                        f"{uuid.uuid4().hex}.png",
                        generated_result,
                        save=False
                    )
                else:
                    # It's a path string (local storage)
                    generated_image.generated_image = generated_result
                
                generated_image.save()
                
            else:
                # Handle traditional file upload (backward compatibility)
                generated_image = GeneratedImage(
                    campaign=campaign,
                    frame=frame,
                    user_photo=photo_file,
                    output_size=output_size
                )
                generated_image.save()
                
                # Get user photo (handle both Cloudinary URL and local path)
                if 'cloudinary.com' in generated_image.user_photo.url:
                    # Download from Cloudinary
                    user_photo_path = download_image_from_url(generated_image.user_photo.url)
                else:
                    user_photo_path = generated_image.user_photo.path
                
                # Get frame (handle both Cloudinary URL and local path)
                frame_image = frame.frame_image if frame else campaign.frame_image
                if 'cloudinary.com' in frame_image.url:
                    frame_path_or_url = frame_image.url
                else:
                    frame_path_or_url = frame_image.path
                
                # Call overlay_frame_on_photo utility function
                try:
                    generated_result = overlay_frame_on_photo(
                        user_photo_path, 
                        frame_path_or_url, 
                        output_size
                    )
                except ValueError as e:
                    return Response({
                        'error': f'Image processing failed: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Update GeneratedImage record with generated image
                if hasattr(generated_result, 'read'):
                    # It's a ContentFile (Cloudinary)
                    generated_image.generated_image.save(
                        f"{uuid.uuid4().hex}.png",
                        generated_result,
                        save=False
                    )
                else:
                    # It's a path string (local storage)
                    generated_image.generated_image = generated_result
                
                generated_image.save()
            
            # Serialize and return response
            serializer = GeneratedImageSerializer(generated_image, context={'request': request})
            
            return Response({
                'generated_image_url': serializer.data['generated_image_url'],
                'message': 'Image generated successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Handle any other errors
            return Response({
                'error': f'Failed to generate image: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CampaignFramesView(APIView):
    """
    List all frames for a campaign (public endpoint for users)
    
    GET /api/campaign/slug/<slug>/frames/
    Response: {"frames": [{"id": int, "name": "string", "frame_url": "string", "is_default": bool}]}
    """
    permission_classes = [AllowAny]
    
    def get(self, request, slug):
        try:
            # Extract code from slug
            parts = slug.split('-')
            print(f"DEBUG: Slug={slug}, Parts={parts}")  # DEBUG
            if len(parts) < 2:
                return Response({
                    'error': 'Invalid campaign URL'
                }, status=status.HTTP_404_NOT_FOUND)
            
            code = parts[-1]
            print(f"DEBUG: Looking for code={code}")  # DEBUG
            campaign = Campaign.objects.get(code=code)
            print(f"DEBUG: Found campaign={campaign.name}")  # DEBUG
            
            if not campaign.is_active:
                return Response({
                    'error': 'Campaign not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get all frames for this campaign
            frames = campaign.frames.all()
            serializer = CampaignFrameSerializer(frames, many=True, context={'request': request})
            
            return Response({
                'frames': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Campaign.DoesNotExist:
            return Response({
                'error': 'Campaign not found'
            }, status=status.HTTP_404_NOT_FOUND)


class CampaignFrameManageView(APIView):
    """
    Manage frames for a campaign (admin only)
    
    POST /api/admin/campaign/<id>/frames/
    Request: Multipart form data with 'name' and 'frame' file
    Response: Frame data
    
    GET /api/admin/campaign/<id>/frames/
    Response: List of frames
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """List all frames for a campaign"""
        try:
            campaign = Campaign.objects.get(pk=pk)
            frames = campaign.frames.all()
            serializer = CampaignFrameSerializer(frames, many=True, context={'request': request})
            
            return Response({
                'frames': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Campaign.DoesNotExist:
            return Response({
                'error': 'Campaign not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request, pk):
        """Add a new frame to campaign"""
        try:
            campaign = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return Response({
                'error': 'Campaign not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check frame limit (max 10 frames)
        if campaign.frames.count() >= 10:
            return Response({
                'error': 'Maximum 10 frames per campaign'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get frame data
        name = request.data.get('name', 'Frame')
        is_default = request.data.get('is_default', 'false').lower() == 'true'
        
        if 'frame' not in request.FILES:
            return Response({
                'error': 'No frame file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        frame_file = request.FILES['frame']
        
        # Validate PNG
        if not frame_file.name.lower().endswith('.png'):
            return Response({
                'error': 'Only PNG files are allowed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get next order number
            max_order = campaign.frames.aggregate(models.Max('order'))['order__max'] or -1
            
            # Create frame
            frame = CampaignFrame.objects.create(
                campaign=campaign,
                frame_image=frame_file,
                name=name,
                is_default=is_default,
                order=max_order + 1
            )
            
            serializer = CampaignFrameSerializer(frame, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': f'Failed to create frame: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CampaignFrameDetailView(APIView):
    """
    Manage individual frame (admin only)
    
    PUT /api/admin/campaign/<campaign_id>/frames/<frame_id>/
    DELETE /api/admin/campaign/<campaign_id>/frames/<frame_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def put(self, request, pk, frame_id):
        """Update frame"""
        try:
            campaign = Campaign.objects.get(pk=pk)
            frame = campaign.frames.get(pk=frame_id)
        except (Campaign.DoesNotExist, CampaignFrame.DoesNotExist):
            return Response({
                'error': 'Frame not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update name if provided
        if 'name' in request.data:
            frame.name = request.data['name']
        
        # Update is_default if provided
        if 'is_default' in request.data:
            frame.is_default = request.data['is_default'].lower() == 'true'
        
        # Update frame image if provided
        if 'frame' in request.FILES:
            frame_file = request.FILES['frame']
            
            if not frame_file.name.lower().endswith('.png'):
                return Response({
                    'error': 'Only PNG files are allowed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Delete old frame file
            if frame.frame_image:
                old_path = frame.frame_image.path
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            frame.frame_image = frame_file
        
        frame.save()
        
        serializer = CampaignFrameSerializer(frame, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, pk, frame_id):
        """Delete frame"""
        try:
            campaign = Campaign.objects.get(pk=pk)
            frame = campaign.frames.get(pk=frame_id)
        except (Campaign.DoesNotExist, CampaignFrame.DoesNotExist):
            return Response({
                'error': 'Frame not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Don't allow deleting the last frame
        if campaign.frames.count() <= 1:
            return Response({
                'error': 'Cannot delete the last frame'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete frame file
        if frame.frame_image:
            frame_path = frame.frame_image.path
            if os.path.exists(frame_path):
                os.remove(frame_path)
        
        frame.delete()
        
        return Response({
            'message': 'Frame deleted successfully'
        }, status=status.HTTP_200_OK)



class CloudinaryStatusView(APIView):
    """
    Diagnostic endpoint to check Cloudinary configuration
    GET /api/cloudinary-status/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        cloudinary_enabled = False
        cloudinary_config = {}
        
        # Check if Cloudinary is configured
        if hasattr(settings, 'CLOUDINARY_STORAGE'):
            cloudinary_config = {
                'cloud_name': settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', 'NOT SET'),
                'api_key_set': bool(settings.CLOUDINARY_STORAGE.get('API_KEY')),
                'api_secret_set': bool(settings.CLOUDINARY_STORAGE.get('API_SECRET')),
            }
            
            if hasattr(settings, 'DEFAULT_FILE_STORAGE'):
                cloudinary_enabled = 'cloudinary' in settings.DEFAULT_FILE_STORAGE
        
        # Get sample frame URLs
        sample_frames = []
        frames = CampaignFrame.objects.all()[:3]
        for frame in frames:
            if frame.frame_image:
                sample_frames.append({
                    'name': frame.name,
                    'campaign': frame.campaign.name,
                    'url': frame.frame_image.url,
                    'is_cloudinary': 'cloudinary.com' in frame.frame_image.url
                })
        
        return Response({
            'cloudinary_enabled': cloudinary_enabled,
            'cloudinary_config': cloudinary_config,
            'default_file_storage': getattr(settings, 'DEFAULT_FILE_STORAGE', 'NOT SET'),
            'sample_frames': sample_frames,
            'total_frames': CampaignFrame.objects.count()
        })
