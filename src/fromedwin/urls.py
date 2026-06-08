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
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.urls import path, include

from .views.redirected import restricted
from .views.health import health_check, healthcheck_database, healthcheck_workers_availability, healthcheck_workers_lighthouse
from incidents.api import webhook
from django.contrib.sitemaps.views import sitemap
from .sitemaps import StaticViewSitemap
from django.conf.urls.static import static

from allauth.account.views import login
from .views.administration import administration, test_email, administration_stats_api
from .views.dashboard import dashboard
from .views.pages import project_pages
from api.views import api_docs

# Note: Using standard Django admin login for staff authentication
# allauth login is available at /login/ for regular users

urlpatterns = [
    # """
    # Project URLs
    # """
    path('', include('projects.urls')),
    path('', include('availability.urls')),
    path('', include('notifications.urls')),
    path('', include('lighthouse.urls')),
    path('', include('status.urls')),
    path('', include('incidents.urls')),
    path('', include('favicons.urls')),
    path('', include('logs.urls')),
    path('', include('reports.urls')),
    # monitor-worker api
    path('clients/', include('workers.urls')),
    # Settings URL
    path('profile/', include('profile.urls')),
    # User dahsboard with feed
    path('dashboard/', dashboard, name='dashboard'),
    # Login page from allauth with github button
    path('login/', login, name='login'),
    # Webhook to receive alerts
    path('alert/<str:secret_key>/', webhook, name='alert'),
    # Display restricted message for user trying to login
    path('restricted/', restricted, name='restricted'),


    path('project/<int:id>/pages/', project_pages, name='project_pages'),

    # """
    # Administration panel for super user in app
    # """
    path('administration/', administration, name='administration'),
    path('test_email/', test_email, name='test_email'),
    path('api/administration/stats/', administration_stats_api, name='administration_stats_api'),

    # Versioned REST API
    path('api/v1/', include('api.urls')),
    path('api/v1/docs/', api_docs, name='api_docs'),

    # """
    # Healthcheck APIs
    # """
    path('health', health_check, name='health_check'),
    path('health/', health_check, name='health_check_slash'), # For monitoring not accepting 301
    path('healthcheck/database/', healthcheck_database, name='healthcheck_database'),
    path('healthcheck/availability/', healthcheck_workers_availability, name='healthcheck_availability'),
    path('healthcheck/lighthouse/', healthcheck_workers_lighthouse, name='healthcheck_lighthouse'),

    # """
    # Public pages presenting features and pricing
    # """
    path('', include('website.urls')),

    # """
    # Dependencies URLs
    # """

    # Django admin
    path('admin/', admin.site.urls),
    # Django allauth accounts
    path('accounts/', include('allauth.urls')),
    # Autentication API for rest_framework
    path('api-auth/', include('rest_framework.urls')),
    # Logout view
    path('logout/', LogoutView.as_view(), {'next_page': settings.LOGOUT_REDIRECT_URL}, name='logout'),
    # Django prometheus, adding /metrics url
    path('', include('django_prometheus.urls')),
    # Tailwind reload event
    path("__reload__/", include("django_browser_reload.urls")),

    path(
        "sitemap.xml",
        sitemap,
        {
            "sitemaps": {
                "static": StaticViewSitemap,
            }
        },
        name="django.contrib.sitemaps.views.sitemap",
    )
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
