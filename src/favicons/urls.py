from django.urls import path

from .api import save_favicon

urlpatterns = [
    # Worker callback for favicon results
    path('api/save_favicon/<str:secret_key>/<int:project_id>/', save_favicon, name='save_favicon'),
    path('api/save_favicon/<str:secret_key>/<int:project_id>', save_favicon, name='save_favicon_no_slash'),
]
