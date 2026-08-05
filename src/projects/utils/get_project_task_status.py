from typing import Dict, Optional
from availability.utils import is_project_monitored
from logs.models import CeleryTaskLog
from reports.models import ProjectReport
from workers.models import Server
import logging
from projects.models import Project, Pages

def get_project_task_status(project: Project) -> Dict:
    """Compute task status overview for a project.

    Mirrors the logic used by the public API endpoint but returns a plain dict
    for reuse within the codebase.
    """

    # If at least one ProjectReport exists, consider all complete (fast-path)
    if ProjectReport.objects.filter(project=project).exists():
        return {
            'favicon_status': 'SUCCESS',
            'sitemap_status': 'SUCCESS',
            'prometheus_status': 'SUCCESS',
            'scraping_status': 'SUCCESS',
            'scraping_progress': None,
            'lighthouse_status': 'SUCCESS',
            'lighthouse_progress': None,
            'reports_status': 'SUCCESS',
            'reports_progress': None,
            'all_complete': True,
            'project_id': project.id,
        }

    pages = Pages.objects.filter(project=project)

    # Favicon status — prefer Favicon.task_status (PENDING while worker runs),
    # fall back to CeleryTaskLog written on completion.
    favicon_status = 'UNKNOWN'
    favicon = None
    try:
        favicon = project.favicon_details
        if favicon.task_status in ('PENDING', 'SUCCESS', 'FAILURE'):
            favicon_status = favicon.task_status
        if favicon_status == 'SUCCESS' and not favicon.favicon:
            favicon_status = 'FAILURE'
    except Exception:
        favicon = None

    if favicon_status == 'UNKNOWN':
        recent_favicon_log = (
            CeleryTaskLog.objects
            .filter(project=project, task_name='favicon_task')
            .order_by('-created_at')
            .first()
        )
        has_stored_favicon = bool(favicon and favicon.favicon)
        favicon_status = 'SUCCESS' if recent_favicon_log and has_stored_favicon else 'UNKNOWN'

    # Sitemap status (prefer concrete evidence via logs)
    recent_sitemap_log = (
        CeleryTaskLog.objects
        .filter(project=project, task_name='sitemap_task')
        .order_by('-created_at')
        .first()
    )
    if recent_sitemap_log:
        sitemap_status = 'SUCCESS'
    elif project.sitemap_task_status == 'PENDING':
        sitemap_status = 'PENDING'
    else:
        sitemap_status = project.sitemap_task_status if project.sitemap_task_status in ('FAILURE',) else 'UNKNOWN'

    # Scraping status/progress
    scraping_status = 'UNKNOWN'
    scraping_progress: Optional[Dict[str, int]] = None
    if pages.exists():
        pages_without_scraping = pages.filter(scraping_last_seen__isnull=True)
        pages_with_status = pages.filter(http_status__isnull=False)
        total_pages = pages.count()
        completed_pages = pages_with_status.count()

        if pages_without_scraping.exists():
            scraping_status = 'PENDING'
            scraping_progress = {
                'total': total_pages,
                'completed': completed_pages,
            }
            if total_pages == completed_pages:
                scraping_status = 'SUCCESS'
        else:
            pages_without_status = pages.filter(http_status__isnull=True)
            if pages_without_status.exists():
                scraping_status = 'PENDING'
            else:
                scraping_status = 'SUCCESS'
                scraping_progress = {
                    'total': total_pages,
                    'completed': completed_pages,
                }

    # Lighthouse status/progress
    lighthouse_status = 'UNKNOWN'
    lighthouse_progress: Optional[Dict[str, int]] = None
    if pages.exists():
        from lighthouse.models import LighthouseReport

        pages_http_200 = pages.filter(http_status__lt=300)
        pages_without_lighthouse = pages_http_200.filter(lighthouse_last_request__isnull=True)

        pages_with_reports = []
        pages_done = []
        for page in pages_http_200:
            if LighthouseReport.objects.filter(page=page).exists():
                pages_with_reports.append(page)
            elif page.http_status and page.http_status >= 300:
                pages_done.append(page)

        total_pages = pages_http_200.count()
        completed_pages = len(pages_with_reports) + len(pages_done)

        if pages_without_lighthouse.exists():
            lighthouse_status = 'PENDING'
            lighthouse_progress = {
                'total': total_pages,
                'completed': completed_pages,
            }
            if total_pages == completed_pages:
                lighthouse_status = 'SUCCESS'
        else:
            pages_without_reports = []
            for page in pages:
                if (
                    not LighthouseReport.objects.filter(page=page).exists()
                    and (not page.http_status or page.http_status < 300)
                ):
                    pages_without_reports.append(page)
            if pages_without_reports:
                lighthouse_status = 'PENDING'
                lighthouse_progress = {
                    'total': total_pages,
                    'completed': completed_pages,
                }
            else:
                lighthouse_status = 'SUCCESS'
                lighthouse_progress = {
                    'total': total_pages,
                    'completed': completed_pages,
                }

    # Prometheus status
    project_date = project.created_at
    server = Server.objects.last()
    last_seen = server.last_seen if server else None
    prometheus_status = 'UNKNOWN'

    try:
        if project_date and last_seen:
            project_before_last_report = project_date < last_seen
            if project_before_last_report:
                prometheus_status = 'SUCCESS' if is_project_monitored(project.id) else 'PENDING'
            else:
                prometheus_status = 'DEPLOYING'
        else:
            prometheus_status = 'SUCCESS' if is_project_monitored(project.id) else 'PENDING'
    except Exception as e:
        logging.error(f"Error getting prometheus status for project {project.id}: {e}")
        prometheus_status = 'FAILED'

    # Reports status gates on other statuses being complete
    reports_status = 'WAITING'
    reports_progress = None
    if (
        favicon_status == 'SUCCESS'
        and sitemap_status == 'SUCCESS'
        and scraping_status == 'SUCCESS'
        and lighthouse_status == 'SUCCESS'
        and prometheus_status == 'SUCCESS'
    ):
        reports_status = 'PENDING'

    all_complete = (
        favicon_status == 'SUCCESS'
        and sitemap_status == 'SUCCESS'
        and scraping_status == 'SUCCESS'
        and lighthouse_status == 'SUCCESS'
        and prometheus_status == 'SUCCESS'
        and reports_status == 'SUCCESS'
    )

    return {
        'favicon_status': favicon_status,
        'sitemap_status': sitemap_status,
        'prometheus_status': prometheus_status,
        'scraping_status': scraping_status,
        'scraping_progress': scraping_progress,
        'lighthouse_status': lighthouse_status,
        'lighthouse_progress': lighthouse_progress,
        'reports_status': reports_status,
        'reports_progress': reports_progress,
        'all_complete': all_complete,
        'project_id': project.id,
    }

