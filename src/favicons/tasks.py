import logging
import base64
import requests
import time
from celery import shared_task, current_app
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image
from io import BytesIO
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from projects.models import Project
from logs.models import CeleryTaskLog
from .models import Favicon


def _favicon_filename(url):
    """Derive a safe storage filename from a favicon URL."""
    name = urlparse(url).path.rsplit('/', 1)[-1] or 'favicon.ico'
    if '?' in name:
        name = name.split('?', 1)[0]
    return name or 'favicon.ico'


def _persist_favicon_result(pk, largest_favicon, largest_content, duration):
    """Write favicon result directly to the DB (Celery worker has Django + DB access)."""
    project = Project.objects.get(pk=pk)
    favicon, _ = Favicon.objects.get_or_create(project=project)
    favicon.last_edited = timezone.now()

    if not largest_favicon or not largest_content:
        favicon.task_status = 'FAILURE'
        favicon.save(update_fields=['task_status', 'last_edited', 'updated_at'])
        return

    favicon_content = BytesIO(base64.b64decode(largest_content))
    filename = _favicon_filename(largest_favicon['url'])
    favicon.favicon.save(filename, favicon_content, save=False)
    favicon.task_status = 'SUCCESS'

    log = CeleryTaskLog.objects.create(
        project=project,
        task_name='favicon_task',
        duration=timedelta(seconds=duration) if duration else None,
    )
    favicon.celery_task_log = log
    favicon.save()


@shared_task()
def fetch_favicon(pk, url):
    largest_favicon = None
    largest_size = (0, 0)
    largest_content = None
    duration = None
    start_time = time.time()
    try:
        Favicon.objects.update_or_create(
            project_id=pk,
            defaults={'task_status': 'PENDING', 'last_edited': timezone.now()},
        )

        # Get the HTML content of the webpage
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all possible favicon links
        icon_links = soup.find_all("link", rel=lambda rel: rel and 'icon' in rel.lower())

        favicons = []
        for icon in icon_links:
            if 'href' in icon.attrs:
                favicon_url = urljoin(url, icon['href'])
                favicons.append(favicon_url)

        # Add default favicon location as a fallback
        parsed_url = urlparse(url)
        default_favicon = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
        favicons.append(default_favicon)

        # Prefer the largest raster icon
        for favicon_url in favicons:
            try:
                favicon_response = requests.get(favicon_url, timeout=10)
                favicon_response.raise_for_status()

                image = Image.open(BytesIO(favicon_response.content))
                width, height = image.size

                if width * height > largest_size[0] * largest_size[1]:
                    largest_size = (width, height)
                    largest_favicon = {
                        'url': favicon_url,
                        'width': width,
                        'height': height,
                    }
                    largest_content = base64.b64encode(favicon_response.content).decode('utf-8')

            except Exception as e:
                logging.info(f"Error fetching or processing {favicon_url}: {e}")

        # If no image found, try the first SVG
        if not largest_favicon:
            svg_url = next((favicon_url for favicon_url in favicons if favicon_url.endswith('.svg')), None)
            if svg_url:
                try:
                    svg_response = requests.get(svg_url, timeout=10)
                    svg_response.raise_for_status()
                    largest_favicon = {
                        'url': svg_url,
                        'width': 0,
                        'height': 0,
                    }
                    largest_content = base64.b64encode(svg_response.content).decode('utf-8')
                except Exception as e:
                    logging.info(f"Error fetching SVG favicon {svg_url}: {e}")

        if largest_favicon and not largest_content:
            logging.debug(
                f"Largest favicon found: {largest_favicon['url']} "
                f"({largest_favicon['width']}x{largest_favicon['height']})"
            )
            response = requests.get(largest_favicon['url'], timeout=10)
            response.raise_for_status()
            largest_content = base64.b64encode(response.content).decode('utf-8')

    except Exception as e:
        logging.error(f"Error fetching the webpage: {e}")
    finally:
        duration = time.time() - start_time
        try:
            _persist_favicon_result(pk, largest_favicon, largest_content, duration)
        except Exception as e:
            logging.error(f"Error saving favicon result to the database: {e}")
            # Fallback for older worker deployments that still rely on the HTTP callback.
            try:
                requests.post(
                    f'{settings.BACKEND_URL}/api/save_favicon/{settings.SECRET_KEY}/{pk}/',
                    json={
                        'favicon_url': largest_favicon['url'] if largest_favicon else None,
                        'favicon_content': largest_content,
                        'duration': duration,
                    },
                    timeout=30,
                ).raise_for_status()
            except Exception as callback_error:
                logging.error(f"Error sending the result to the backend: {callback_error}")
        logging.info(f"Task completed for project {pk}")


@shared_task(bind=True)
def queue_deprecated_favicons(self):

    # Revoke all tasks with the same name currently queued
    inspector = current_app.control.inspect()
    active_tasks = inspector.active()
    reserved_tasks = inspector.reserved()

    task_name = self.name
    task_id = self.request.id

    # Helper function to revoke tasks
    def revoke_tasks(tasks):
        for worker, tasks_list in tasks.items():
            for task in tasks_list:
                if task['name'] == task_name and task['id'] != task_id:
                    current_app.control.revoke(task['id'], terminate=True)
                    print(f"Revoked task {task['id']} on worker {worker}")

    # Revoke tasks that are currently active
    if active_tasks:
        revoke_tasks(active_tasks)

    # Revoke tasks that are reserved (queued but not started)
    if reserved_tasks:
        revoke_tasks(reserved_tasks)

    six_hours_ago = timezone.now() - timedelta(hours=settings.TIMINGS['FAVICON_INTERVAL_HOURS'])
    projects = Project.objects.filter(
        Q(favicon_details__last_edited__lt=six_hours_ago) | Q(favicon_details__isnull=True)
    )

    for project in projects:
        favicon, created = Favicon.objects.get_or_create(
            project=project,
            defaults={'task_status': 'PENDING'}
        )
        if not created:
            favicon.task_status = 'PENDING'
            favicon.save()

    projects = [{'id': project.pk, 'url': project.url} for project in projects]

    logging.info(f'Found {len(list(projects))} projects to refresh favicon.')
    for project in projects:
        fetch_favicon.delay(project.get('id'), project.get('url'))
