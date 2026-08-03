from io import BytesIO
import json
import base64
import logging
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Q
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from projects.models import Project
from .models import Favicon
from logs.models import CeleryTaskLog

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def save_favicon(request, secret_key, project_id):

    # Use django settings secret_key to authenticate django worker
    if secret_key != settings.SECRET_KEY:
        # return http unauthorized
        return JsonResponse({}, status=401)

    # Get performance to update
    project = get_object_or_404(Project, id=project_id)

    # Load data from body as json
    data = json.loads(request.body.decode("utf-8"))
    favicon_url = data.get('favicon_url')
    duration = data.get('duration')

    # Create celery task log
    CeleryTaskLog.objects.create(
        project=project,
        task_name='favicon_task',
        duration=timedelta(seconds=duration) if duration else None
    )

    # Get or create favicon record
    favicon, created = Favicon.objects.get_or_create(project=project)
    # If favicon_url is null or undefined, it means worker couldn't find a favicon
    # We then set the status to FAILURE so we can react and retry if needed
    if not favicon_url:
        favicon.task_status = 'FAILURE'
        favicon.last_edited = timezone.now()
        favicon.save()
        return JsonResponse({})
    
    # Generate data for the favicon
    favicon_content_base64 = data.get('favicon_content')
    favicon_content = base64.b64decode(favicon_content_base64)
    favicon_content = BytesIO(favicon_content)

    favicon.favicon.save(data.get('favicon_url').split('/')[-1], favicon_content)
    favicon.task_status = 'SUCCESS'
    favicon.last_edited = timezone.now()
    favicon.save()

    return JsonResponse({}) 