from django.db import models
from django.utils import timezone


def favicon_upload_path(instance, filename):
    """Upload path for favicon files"""
    return f'user_{instance.project.user.pk}/prjct_{instance.project.pk}/favicons/{filename}'


# List of status for favicon task
FAVICON_TASK_STATUS = (
    ('PENDING', 'Pending'),
    ('SUCCESS', 'Success'),
    ('FAILURE', 'Failure'),
    ('UNKNOWN', 'Unknown'),
)


class Favicon(models.Model):
    """
    Favicon model to store favicon-related data for projects
    """
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='favicon_details',
        help_text="Project this favicon belongs to"
    )
    favicon = models.FileField(
        upload_to=favicon_upload_path,
        blank=True,
        null=True,
        help_text="Application's favicon",
    )
    task_status = models.CharField(
        max_length=16,
        choices=FAVICON_TASK_STATUS,
        default='UNKNOWN',
        help_text="Favicon task status"
    )
    last_edited = models.DateTimeField(
        default=timezone.now,
        help_text="Last time favicon was edited"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    celery_task_log = models.ForeignKey(
        'logs.CeleryTaskLog',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='favicons',
        help_text="Celery task log associated with this favicon (optional)"
    )

    class Meta:
        verbose_name = "Favicon"
        verbose_name_plural = "Favicons"

    def __str__(self):
        return f"Favicon for {self.project.title}"
