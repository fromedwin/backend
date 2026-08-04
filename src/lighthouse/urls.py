from django.urls import path

from .api import report_api, report_json_api

urlpatterns = [
    # Worker callback: GET (still needed?) + POST (save report)
    path(
        'api/report/<str:secret_key>/performance/<int:page_id>',
        report_api,
        name='save_report',
    ),
    path(
        'api/report/<str:secret_key>/performance/<int:page_id>/',
        report_api,
        name='save_report_slash',
    ),
    # Authenticated report JSON (API consumers)
    path('api/report/<int:report_id>/json/', report_json_api, name='report_json_api'),
]
