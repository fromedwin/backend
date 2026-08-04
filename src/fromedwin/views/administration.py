from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.http import JsonResponse
from workers.models import Server
from availability.models import Service
from fromedwin.prometheus import instant_value


def get_stats_data():
    """Get administration statistics data from Prometheus + Django ORM."""
    lighthouse_queue_name = settings.CELERY_QUEUE_LIGHTHOUSE
    celery_queue_name = settings.CELERY_QUEUE

    lighthouse_worker = instant_value(
        f'rabbitmq_queue_consumers{{queue="{lighthouse_queue_name}"}}'
    )
    celery_worker = instant_value(
        f'rabbitmq_queue_consumers{{queue="{celery_queue_name}"}}'
    )
    lighthouse_queue = instant_value(
        f'rabbitmq_queue_messages{{queue="{lighthouse_queue_name}"}}'
    )
    fromedwin_queue = instant_value(
        f'rabbitmq_queue_messages{{queue="{celery_queue_name}"}}'
    )

    servers = Server.objects.filter(
        last_seen__gte=timezone.now()
        - timezone.timedelta(seconds=settings.HEARTBEAT_INTERVAL + 5)
    ).order_by("-creation_date")

    return {
        "users_count": User.objects.count(),
        "url_count": Service.objects.count(),
        "lighthouse_worker": lighthouse_worker,
        "celery_worker": celery_worker,
        "lighthouse_queue": lighthouse_queue,
        "fromedwin_queue": fromedwin_queue,
        "prometheus_workers": servers.count(),
    }


@staff_member_required
def administration(request):
    """Show administration data."""
    stats = get_stats_data()

    email_success = False
    email_fail = False

    if "email_success" in request.GET:
        email_success = True

    if "email_fail" in request.GET:
        email_fail = True

    servers = Server.objects.filter(
        last_seen__gte=timezone.now()
        - timezone.timedelta(seconds=settings.HEARTBEAT_INTERVAL + 5)
    ).order_by("-creation_date")

    return render(
        request,
        "administration/administration.html",
        {
            "servers": servers,
            "settings": settings,
            "email_success": email_success,
            "email_fail": email_fail,
            "stats": stats,
        },
    )


@staff_member_required
def administration_stats_api(request):
    """Return administration statistics as JSON for AJAX calls."""
    if request.method == "GET":
        return JsonResponse(get_stats_data())
    return JsonResponse({"error": "Method not allowed"}, status=405)


@staff_member_required
def test_email(request):
    success = True
    try:
        send_mail(
            "Test email",
            "This is a test email",
            f"{settings.CONTACT_NAME} <{settings.CONTACT_EMAIL}>",
            [request.user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(e)
        success = False

    return redirect(
        f"{reverse('administration')}{'?email_success' if success else 'email_fail'}"
    )
