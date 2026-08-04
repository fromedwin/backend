from celery import shared_task
from projects.utils.scrape_url import scrape_url

from datetime import timedelta
from urllib.parse import urlparse, urlunparse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from projects.models import Pages, PageLink
from logs.models import CeleryTaskLog
from django.db import transaction
from lighthouse.utils import request_lighthouse_report


def normalize_page_url(url):
    """Normalize URL for comparisons (ignore fragment, query, trailing slash)."""
    if not url:
        return ''
    parsed = urlparse(url.strip())
    path = parsed.path or '/'
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    return f'{parsed.scheme}://{parsed.netloc}{path}'.lower()


def canonicalize_page_url(url):
    """Stable URL form stored for pages (no fragment; keep path trailing-slash stripped except root)."""
    if not url:
        return url
    parsed = urlparse(url.strip())
    path = parsed.path or '/'
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    return urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))


def same_site(url_a, url_b):
    return urlparse(url_a).netloc.lower() == urlparse(url_b).netloc.lower()


def get_or_create_project_page(project, url):
    """
    Resolve a page by exact URL, then by normalized URL, to avoid duplicates like
    /path vs /path/ that would otherwise create two rows or self-links.
    """
    canonical = canonicalize_page_url(url)
    page = Pages.objects.filter(project=project, url=canonical).first()
    if page:
        return page, False

    # Match an existing row that only differs by trailing slash / case.
    target_norm = normalize_page_url(canonical)
    for candidate in Pages.objects.filter(project=project):
        if normalize_page_url(candidate.url) == target_norm:
            return candidate, False

    return Pages.objects.get_or_create(project=project, url=canonical)


def create_page_link(from_page, to_page):
    """Create a PageLink unless it would be a self-link or duplicate."""
    if from_page.pk == to_page.pk:
        return None
    link, _ = PageLink.objects.get_or_create(from_page=from_page, to_page=to_page)
    return link


@shared_task()
def scrape_page(page_id, url):
    title, description, urls, http_status, redirected_url, duration = scrape_url(url)

    try:
        page = get_object_or_404(Pages, id=page_id)
        page.http_status = http_status if http_status else 0
        page.scraping_last_seen = timezone.now()

        is_redirect = bool(
            redirected_url
            and normalize_page_url(redirected_url) != normalize_page_url(page.url)
        )

        if is_redirect:
            page.title = title or page.title
            page.description = description or page.description
            page.save()

            PageLink.objects.filter(from_page=page).delete()

            if same_site(page.url, redirected_url):
                to_page, created = get_or_create_project_page(page.project, redirected_url)
                create_page_link(page, to_page)
                # Queue scrape for the redirect target when it is a different page
                # and has not been scraped yet.
                if to_page.pk != page.pk and (created or to_page.scraping_last_seen is None):
                    scrape_page.delay(to_page.pk, to_page.url)

        elif http_status == 404:
            page.save()
            PageLink.objects.filter(from_page=page).delete()
        else:
            page.title = title
            page.description = description
            page.save()

            with transaction.atomic():
                PageLink.objects.filter(from_page=page).delete()

                for discovered_url in urls:
                    if not same_site(page.url, discovered_url):
                        continue
                    if normalize_page_url(discovered_url) == normalize_page_url(page.url):
                        continue

                    to_page, created = get_or_create_project_page(page.project, discovered_url)
                    create_page_link(page, to_page)
                    if to_page.pk != page.pk and (created or to_page.scraping_last_seen is None):
                        scrape_page.delay(to_page.pk, to_page.url)

        log = CeleryTaskLog.objects.create(
            project=page.project,
            task_name='scraping_task',
            duration=timedelta(seconds=duration) if duration else None,
        )

        page.scraping_task_log = log
        page.save(update_fields=['scraping_task_log'])

        # Lighthouse only for successful non-redirect responses.
        if (not is_redirect) and page.http_status and page.http_status < 300:
            request_lighthouse_report(page, source='scrape')

    except Pages.DoesNotExist:
        print(f'Page {page_id} does not exist')
        return
