from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Campaign, CampaignPoster, CampaignFrame, GeneratedImage


class LoginSerializer(serializers.Serializer):
    """Serializer for admin login request"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Validate credentials and authenticate user"""
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError('User account is disabled.')
                data['user'] = user
                return data
            else:
                raise serializers.ValidationError('Invalid credentials.')
        else:
            raise serializers.ValidationError('Must include "username" and "password".')


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information in login response"""
    class Meta:
        model = User
        fields = ['id', 'username']


class CampaignPosterSerializer(serializers.ModelSerializer):
    """Serializer for CampaignPoster model"""
    poster_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignPoster
        fields = ['id', 'name', 'poster_url', 'is_default', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_poster_url(self, obj):
        """Return the full URL for the poster image"""
        if obj.poster_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.poster_image.url)
            return obj.poster_image.url
        return None


class CampaignFrameSerializer(serializers.ModelSerializer):
    """Serializer for CampaignFrame model"""
    frame_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CampaignFrame
        fields = ['id', 'name', 'frame_url', 'is_default', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_frame_url(self, obj):
        """Return the full URL for the frame image"""
        if obj.frame_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.frame_image.url)
            return obj.frame_image.url
        return None


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model with posters, frames and slug fields"""
    frame_url = serializers.SerializerMethodField()  # Backward compatibility
    posters = CampaignPosterSerializer(many=True, read_only=True)
    frames = CampaignFrameSerializer(many=True, read_only=True)
    poster_count = serializers.SerializerMethodField()
    frame_count = serializers.SerializerMethodField()
    slug = serializers.ReadOnlyField()
    
    class Meta:
        model = Campaign
        fields = ['id', 'name', 'code', 'slug', 'frame_url', 'posters', 'frames', 'poster_count', 'frame_count', 'created_at', 'is_active']
        read_only_fields = ['id', 'code', 'slug', 'created_at']
    
    def get_frame_url(self, obj):
        """Return the full URL for the default frame (backward compatibility)"""
        # Try to get default frame first
        default_frame = obj.frames.filter(is_default=True).first()
        if default_frame:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(default_frame.frame_image.url)
            return default_frame.frame_image.url
        
        # Fallback to first frame
        first_frame = obj.frames.first()
        if first_frame:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_frame.frame_image.url)
            return first_frame.frame_image.url
        
        # Fallback to old frame_image field
        if obj.frame_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.frame_image.url)
            return obj.frame_image.url
        
        return None
    
    def get_poster_count(self, obj):
        """Return the number of posters"""
        return obj.posters.count()
    
    def get_frame_count(self, obj):
        """Return the number of frames"""
        return obj.frames.count()


class GeneratedImageSerializer(serializers.ModelSerializer):
    """Serializer for GeneratedImage model with generated_image_url field"""
    generated_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedImage
        fields = ['id', 'generated_image_url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_generated_image_url(self, obj):
        """Return the full URL for the generated image"""
        if obj.generated_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.generated_image.url)
            return obj.generated_image.url
        return None
