from django.urls import path
from .views import (
    AdminLoginView, CampaignCreateView, CampaignListView, CampaignManageView,
    CampaignDetailView, CampaignBySlugView, GenerateImageView,
    CampaignPostersView, CampaignFramesView, 
    CampaignPosterManageView, CampaignPosterDetailView,
    CampaignFrameManageView, CampaignFrameDetailView,
    CloudinaryStatusView, GenerateThreeLayerPosterView
)

urlpatterns = [
    # Admin endpoints
    path('admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('admin/campaign/', CampaignCreateView.as_view(), name='campaign-create'),
    path('admin/campaigns/', CampaignListView.as_view(), name='campaign-list'),
    path('admin/campaign/<int:pk>/', CampaignManageView.as_view(), name='campaign-manage'),
    path('admin/campaign/<int:pk>/posters/', CampaignPosterManageView.as_view(), name='campaign-posters-manage'),
    path('admin/campaign/<int:pk>/posters/<int:poster_id>/', CampaignPosterDetailView.as_view(), name='campaign-poster-detail'),
    path('admin/campaign/<int:pk>/frames/', CampaignFrameManageView.as_view(), name='campaign-frames-manage'),
    path('admin/campaign/<int:pk>/frames/<int:frame_id>/', CampaignFrameDetailView.as_view(), name='campaign-frame-detail'),
    
    # User-facing endpoints (for new frontend) - Must be before legacy endpoints
    path('campaigns/', CampaignListView.as_view(), name='campaigns-list-public'),
    path('campaigns/<slug:slug>/', CampaignBySlugView.as_view(), name='campaign-by-slug-public'),
    
    # Legacy endpoints (keep for backward compatibility)
    path('campaign/<str:code>/', CampaignDetailView.as_view(), name='campaign-detail'),
    path('campaign/slug/<path:slug>/posters/', CampaignPostersView.as_view(), name='campaign-posters'),
    path('campaign/slug/<path:slug>/frames/', CampaignFramesView.as_view(), name='campaign-frames'),
    path('campaign/slug/<path:slug>/', CampaignBySlugView.as_view(), name='campaign-by-slug'),
    
    # Image generation
    path('generate/', GenerateImageView.as_view(), name='generate-image'),
    path('generate-poster/', GenerateThreeLayerPosterView.as_view(), name='generate-poster'),  # New 3-layer endpoint
    
    # Diagnostic endpoint
    path('cloudinary-status/', CloudinaryStatusView.as_view(), name='cloudinary-status'),
]
