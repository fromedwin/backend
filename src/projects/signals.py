from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone

from favicons.models import Favicon
from favicons.tasks import fetch_favicon
from .tasks.fetch_sitemap import fetch_sitemap
from .tasks.scrape_page import scrape_page
from .models import Project, Pages


@receiver(post_save, sender=Project)
def post_save_created(sender, instance, created, **kwargs):
    if not created:
        return

    favicon, _ = Favicon.objects.get_or_create(
        project=instance,
        defaults={
            'task_status': 'PENDING',
            'last_edited': timezone.now(),
        },
    )
    if favicon.task_status != 'PENDING':
        favicon.task_status = 'PENDING'
        favicon.last_edited = timezone.now()
        favicon.save(update_fields=['task_status', 'last_edited', 'updated_at'])

    project_id = instance.pk
    project_url = instance.url

    if instance.sitemap_task_status != 'PENDING':
        Project.objects.filter(pk=project_id).update(sitemap_task_status='PENDING')

    # Queue after commit so workers never race an uncommitted project row.
    transaction.on_commit(lambda: fetch_sitemap.delay(project_id, project_url))
    transaction.on_commit(lambda: fetch_favicon.delay(project_id, project_url))


@receiver(post_save, sender=Pages)
def post_save_created_page(sender, instance, created, **kwargs):
    if not created:
        return

    page_id = instance.pk
    page_url = instance.url
    transaction.on_commit(lambda: scrape_page.delay(page_id, page_url))
