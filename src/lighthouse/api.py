from datetime import timedelta
import json
import base64
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import Q

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

from projects.models import Pages
from logs.models import CeleryTaskLog
from .models import LighthouseReport
from fromedwin.decorators import waiting_list_approved_only
from constants import LIGHTHOUSE_FORMFACTOR_CHOICES

@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def report_api(request, secret_key, page_id):

    if request.method == "GET":
        # Use django settings secret_key to authenticate django worker
        if secret_key != settings.SECRET_KEY:
            # return http unauthorized if secret key doesn't match
            return JsonResponse({}, status=401)

        page = get_object_or_404(Pages, pk=page_id)
        last_report = page.lighthouse_report.first()

        return JsonResponse({
            # List of ids and urls to fetch
            'id': page.pk,
            'url': page.url,
            'last_report_date': last_report.creation_date if last_report else None,
            'LIGHTHOUSE_INTERVAL_HOURS': settings.TIMINGS['LIGHTHOUSE_INTERVAL_HOURS'] * 60
        })

    # Use django settings secret_key to authenticate django worker
    if secret_key != settings.SECRET_KEY:
        # return http unauthorized if secret key doesn't match
        return JsonResponse({}, status=401)
    
    # Get performance to update
    page = get_object_or_404(Pages, pk=page_id)
    # Load data from body as json
    data = json.loads(request.body.decode("utf-8"))
    
    # Parse the report JSON string if it's a string (lighthouse returns JSON as string)
    if isinstance(data['report'], str):
        data['report'] = json.loads(data['report'])

    # Generate metadata used for file storage
    path = page.project.directory_path()
    try:
        filename = f'{data["report"]["audits"]["final-screenshot"]["details"]["timestamp"]}'
    except:
        filename = f'{timezone.now().timestamp()}'

    # Generate report.json file
    json_file = json.dumps(data['report'])
    json_file = json_file.encode('utf-8')
    report_json_file = default_storage.save(f'{path}/{filename}.json', ContentFile(json_file))

    # Generate screenshot.jpg from report json base64 value
    try:
        screenshot_as_a_string = data['report']['audits']['final-screenshot']['details']['data']
        screenshot_as_a_string = screenshot_as_a_string.replace('data:image/jpeg;base64,', '')
        screenshot = default_storage.save(f'{path}/{filename}.jpg', ContentFile(base64.b64decode(screenshot_as_a_string)))
    except:
        screenshot = None

    # Look for form factor as `desktop` or `mobile`
    formFactor = LIGHTHOUSE_FORMFACTOR_CHOICES[0][0]
    if data['report']['configSettings']['formFactor'] == 'mobile':
        formFactor = LIGHTHOUSE_FORMFACTOR_CHOICES[1][0]

    celery_task_log = CeleryTaskLog.objects.create(
        project = page.project,
        task_name = 'lighthouse',
        duration = timedelta(milliseconds=data['duration']) if data['duration'] else None
    )

    categories = data['report'].get('categories') or {}

    def category_score(key):
        category = categories.get(key) or {}
        return category.get('score')

    report = LighthouseReport.objects.create(
        page = page,
        form_factor = formFactor,
        score_performance = category_score('performance'),
        score_accessibility = category_score('accessibility'),
        score_best_practices = category_score('best-practices'),
        score_seo = category_score('seo'),
        score_pwa = category_score('pwa'),
        screenshot = screenshot,
        report_json_file = report_json_file,
        celery_task_log = celery_task_log
    )
    report.save()

    return JsonResponse({})

@login_required
@waiting_list_approved_only()
@api_view(["GET"])
def report_json_api(request, report_id):
    """
    Return lighthouse report JSON data for authenticated users
    """
    try:
        report = get_object_or_404(LighthouseReport, pk=report_id)
        
        # Check if user has access to the project that owns this report
        if report.page.project.user != request.user:
            return JsonResponse({'error': 'Unauthorized access to this report'}, status=403)
        
        # Read and return the JSON data from the report file
        if report.report_json_file:
            report_json_content = report.report_json_file.read()
            return JsonResponse(json.loads(report_json_content.decode('utf-8')), safe=False)
        else:
            return JsonResponse({'error': 'Report JSON file not found'}, status=404)
            
    except LighthouseReport.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error loading report: {str(e)}'}, status=500)
