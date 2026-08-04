"""monitor URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path, include

from .views.health import health_check, healthcheck_database, healthcheck_workers_availability, healthcheck_workers_lighthouse
from incidents.api import webhook
from django.conf.urls.static import static
from .views.home import home

urlpatterns = [
    # Minimal root page
    path('', home, name='home'),
    # Worker API
    path('clients/', include('workers.urls')),
    # Alertmanager webhook
    path('alert/<str:secret_key>/', webhook, name='alert'),
    # Worker callback APIs (lighthouse Node worker + favicon Celery fallback)
    path('', include('lighthouse.urls')),
    path('', include('favicons.urls')),
    # Versioned REST API
    path('api/v1/', include('api.urls')),
    # Healthcheck APIs
    path('health', health_check, name='health_check'),
    path('health/', health_check, name='health_check_slash'),
    path('healthcheck/database/', healthcheck_database, name='healthcheck_database'),
    path('healthcheck/availability/', healthcheck_workers_availability, name='healthcheck_availability'),
    path('healthcheck/lighthouse/', healthcheck_workers_lighthouse, name='healthcheck_lighthouse'),
    # Django admin
    path('admin/', admin.site.urls),
    # Django prometheus, adding /metrics url
    path('', include('django_prometheus.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
