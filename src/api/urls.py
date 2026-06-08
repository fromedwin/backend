from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'api'

router = DefaultRouter()
router.register('projects', views.ProjectViewSet, basename='project')
router.register('pages', views.PageViewSet, basename='page')
router.register('page-links', views.PageLinkViewSet, basename='page-link')
router.register('services', views.ServiceViewSet, basename='service')
router.register('incidents', views.IncidentViewSet, basename='incident')
router.register('notifications', views.NotificationViewSet, basename='notification')
router.register('emails', views.EmailViewSet, basename='email')
router.register('reports', views.ReportViewSet, basename='report')
router.register('lighthouse', views.LighthouseReportViewSet, basename='lighthouse')
router.register('favicons', views.FaviconViewSet, basename='favicon')
router.register('logs', views.CeleryTaskLogViewSet, basename='log')
router.register('servers', views.ServerViewSet, basename='server')
router.register('metrics', views.MetricsViewSet, basename='metric')

urlpatterns = [
    path('', include(router.urls)),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('me/', views.MeView.as_view(), name='me'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]
