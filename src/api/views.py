from urllib.parse import urlparse
import json

from celery import current_app
from django.conf import settings
from django.db.models import Q

from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from availability.models import Service
from favicons.models import Favicon
from incidents.models import Incident
from lighthouse.models import LighthouseReport
from logs.models import CeleryTaskLog
from notifications.models import Emails, Notification
from profile.models import Profile
from projects.models import PageLink, Pages, Project
from projects.tasks.fetch_sitemap import fetch_sitemap
from projects.tasks.scrape_page import scrape_page
from projects.utils.get_project_task_status import get_project_task_status
from reports.models import ProjectReport
from reports.tasks.create_report import create_report
from workers.models import Metrics, Server

from .mixins import ProjectFilterMixin
from .permissions import IsApprovedUser, IsProjectOwner
from .serializers import (
    CeleryTaskLogSerializer,
    EmailSerializer,
    FaviconSerializer,
    IncidentSerializer,
    LighthouseReportSerializer,
    MetricsSerializer,
    NotificationSerializer,
    PageLinkSerializer,
    PageSerializer,
    ProfileSerializer,
    ProjectSerializer,
    ReportSerializer,
    ServerSerializer,
    ServiceCreateSerializer,
    ServiceSerializer,
    UserSerializer,
)


@extend_schema_view(
    list=extend_schema(summary='List projects'),
    retrieve=extend_schema(summary='Get project'),
    create=extend_schema(summary='Create project'),
    update=extend_schema(summary='Update project'),
    partial_update=extend_schema(summary='Partially update project'),
    destroy=extend_schema(summary='Delete project'),
)
class ProjectViewSet(ProjectFilterMixin, viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Project.objects.select_related('favicon_details').all().order_by('title')

    @extend_schema(summary='Refresh project sitemap')
    @action(detail=True, methods=['post'], url_path='refresh-sitemap')
    def refresh_sitemap(self, request, pk=None):
        project = self.get_object()
        fetch_sitemap.delay(project.pk, project.url)
        return Response({
            'detail': f'Sitemap refresh queued for "{project.title}".',
        })

    @extend_schema(summary='Get project task status')
    @action(detail=True, methods=['get'], url_path='task-status')
    def task_status(self, request, pk=None):
        project = self.get_object()
        return Response(get_project_task_status(project))

    @extend_schema(summary='Get Prometheus monitoring stats for project')
    @action(detail=True, methods=['get'], url_path='monitoring')
    def monitoring(self, request, pk=None):
        from datetime import datetime, timezone as dt_timezone

        from availability.utils import get_project_stats, is_project_monitored

        project = self.get_object()
        try:
            duration = int(request.query_params.get('duration', 3600))
        except (TypeError, ValueError):
            duration = 3600
        duration = max(60, min(duration, 604800))

        try:
            stats = get_project_stats(project.id, duration=duration)
            monitored = is_project_monitored(project.id)
        except Exception as exc:
            return Response(
                {
                    'project_id': project.id,
                    'duration': duration,
                    'is_monitored': False,
                    'error': str(exc),
                    'availability': {
                        '1d': project.availability(days=1),
                        '7d': project.availability(days=7),
                        '30d': project.availability(days=30),
                    },
                    'services': [],
                },
                status=status.HTTP_200_OK,
            )

        services_by_id = {
            str(service.id): service
            for service in Service.objects.filter(project=project).select_related(
                'httpcode', 'httpmockedcode',
            )
        }
        now = datetime.now(dt_timezone.utc)
        services_payload = []

        for service_id, probe in (stats.get('services') or {}).items():
            service = services_by_id.get(str(service_id))
            url = None
            is_critical = None
            is_enabled = None
            title = probe.get('title')
            if service:
                title = service.title or title
                is_critical = service.is_critical
                is_enabled = service.is_enabled
                try:
                    url = service.httpcode.url
                except Exception:
                    try:
                        url = service.httpmockedcode.url()
                    except Exception:
                        url = project.url

            expiry_ts = probe.get('probe_ssl_earliest_cert_expiry')
            ssl_expiry_iso = None
            ssl_days_remaining = None
            if expiry_ts:
                try:
                    expiry_dt = datetime.fromtimestamp(float(expiry_ts), tz=dt_timezone.utc)
                    ssl_expiry_iso = expiry_dt.isoformat()
                    ssl_days_remaining = (expiry_dt - now).total_seconds() / 86400
                except (TypeError, ValueError, OSError, OverflowError):
                    pass

            latency = probe.get('duration_seconds') or []
            latest_latency = None
            if latency:
                try:
                    latest_latency = float(latency[-1][1])
                except (TypeError, ValueError, IndexError):
                    latest_latency = None

            services_payload.append({
                'id': int(service_id) if str(service_id).isdigit() else service_id,
                'title': title,
                'url': url,
                'is_critical': is_critical,
                'is_enabled': is_enabled,
                'http_status_code': probe.get('probe_http_status_code'),
                'http_ssl': probe.get('probe_http_ssl'),
                'http_redirects': probe.get('probe_http_redirects'),
                'http_version': probe.get('probe_http_version'),
                'tls_version': probe.get('probe_tls_version_info'),
                'ssl_earliest_cert_expiry': ssl_expiry_iso,
                'ssl_days_remaining': ssl_days_remaining,
                'latency_seconds_latest': latest_latency,
                'latency_seconds': latency,
            })

        # Include ORM services that have no Prometheus samples yet
        seen = {str(item['id']) for item in services_payload}
        for service_id, service in services_by_id.items():
            if service_id in seen:
                continue
            url = None
            try:
                url = service.httpcode.url
            except Exception:
                try:
                    url = service.httpmockedcode.url()
                except Exception:
                    url = project.url
            services_payload.append({
                'id': service.id,
                'title': service.title,
                'url': url,
                'is_critical': service.is_critical,
                'is_enabled': service.is_enabled,
                'http_status_code': None,
                'http_ssl': None,
                'http_redirects': None,
                'http_version': None,
                'tls_version': None,
                'ssl_earliest_cert_expiry': None,
                'ssl_days_remaining': None,
                'latency_seconds_latest': None,
                'latency_seconds': [],
            })

        services_payload.sort(key=lambda item: (item.get('title') or '', item.get('id') or 0))

        return Response({
            'project_id': project.id,
            'duration': duration,
            'is_monitored': monitored,
            'availability': {
                '1d': project.availability(days=1),
                '7d': project.availability(days=7),
                '30d': project.availability(days=30),
            },
            'services': services_payload,
        })

    @extend_schema(summary='Get pages tree for project')
    @action(detail=True, methods=['get'], url_path='pages-tree')
    def pages_tree(self, request, pk=None):
        project = self.get_object()
        pages = Pages.objects.filter(project=project).values('id', 'url', 'title')
        tree = {'name': project.title, 'url': project.url, 'children': []}

        for page in pages:
            parsed = urlparse(page['url'])
            parts = [p for p in parsed.path.split('/') if p]
            current = tree
            for i, part in enumerate(parts):
                if 'children' not in current:
                    current['children'] = []
                found = next((c for c in current['children'] if c.get('name') == part), None)
                if not found:
                    if i == len(parts) - 1:
                        found = {
                            'name': part,
                            'url': page['url'],
                            'title': page.get('title') or part,
                            'page_id': page['id'],
                            'children': [],
                        }
                    else:
                        found = {'name': part, 'children': []}
                    current['children'].append(found)
                current = found

        return Response(tree)


@extend_schema_view(
    list=extend_schema(summary='List pages', description='Filter with ?project=<id>'),
    retrieve=extend_schema(summary='Get page'),
    create=extend_schema(summary='Create page'),
    update=extend_schema(summary='Update page'),
    partial_update=extend_schema(summary='Partially update page'),
    destroy=extend_schema(summary='Delete page'),
)
class PageViewSet(ProjectFilterMixin, viewsets.ModelViewSet):
    serializer_class = PageSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Pages.objects.select_related('project').all().order_by('url')

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    @extend_schema(summary='Refresh page data (scrape + lighthouse)')
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        page = self.get_object()
        task_kwargs = {'id': page.pk, 'url': page.url, 'source': 'api_refresh'}
        current_app.send_task(
            'fetch_lighthouse_report',
            kwargs=task_kwargs,
            queue=settings.CELERY_QUEUE_LIGHTHOUSE,
            task_id=f'performance_{page.pk}',
        )
        scrape_page.delay(page.pk, page.url)
        return Response({
            'detail': f'Refresh queued for "{page.title or page.url}".',
        })


class PageLinkViewSet(ProjectFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PageLinkSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = PageLink.objects.select_related('from_page', 'to_page').all()

    def get_queryset(self):
        qs = super().get_queryset()
        page_id = self.request.query_params.get('page')
        project_id = self.request.query_params.get('project')
        if page_id:
            qs = qs.filter(from_page_id=page_id) | qs.filter(to_page_id=page_id)
        if project_id:
            qs = qs.filter(from_page__project_id=project_id)
        return qs


@extend_schema_view(
    list=extend_schema(summary='List services', description='Filter with ?project=<id>'),
    retrieve=extend_schema(summary='Get service'),
    destroy=extend_schema(summary='Delete service'),
)
class ServiceViewSet(ProjectFilterMixin, viewsets.ModelViewSet):
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Service.objects.select_related(
        'project', 'httpcode', 'httpmockedcode',
    ).all().order_by('title')
    http_method_names = ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceCreateSerializer
        return ServiceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = serializer.save()
        return Response(
            ServiceSerializer(service, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = ServiceSerializer(
            instance, data=request.data, partial=partial, context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ServiceSerializer(instance, context=self.get_serializer_context()).data)


class IncidentViewSet(ProjectFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = IncidentSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Incident.objects.select_related('service', 'service__project').all().order_by('-starts_at')

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        service_id = self.request.query_params.get('service')
        status_filter = self.request.query_params.get('status')
        if project_id:
            qs = qs.filter(service__project_id=project_id)
        if service_id:
            qs = qs.filter(service_id=service_id)
        if status_filter is not None:
            qs = qs.filter(status=status_filter)
        return qs

    @extend_schema(summary='Resolve incident')
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        incident = self.get_object()
        incident.status = 1
        incident.ends_at = timezone.now()
        incident.save(update_fields=['status', 'ends_at'])
        return Response(IncidentSerializer(incident).data)


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Notification.objects.select_related('project', 'service').all().order_by('-date')

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset.filter(
            Q(project__user=user) | Q(service__project__user=user),
        )
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class EmailViewSet(ProjectFilterMixin, viewsets.ModelViewSet):
    serializer_class = EmailSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Emails.objects.select_related('project').all()

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class ReportViewSet(ProjectFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = ProjectReport.objects.select_related('project').all()

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    @extend_schema(summary='Queue report generation')
    @action(detail=False, methods=['post'], url_path='queue')
    def queue(self, request):
        project_id = request.data.get('project')
        if not project_id:
            return Response({'project': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        project = Project.objects.filter(pk=project_id, user=request.user).first()
        if not project:
            raise PermissionDenied('Project not found or access denied.')
        task = create_report.delay(project_id, 'api')
        return Response({
            'detail': f'Report generation queued for "{project.title}".',
            'task_id': task.id,
            'project_id': project_id,
        }, status=status.HTTP_202_ACCEPTED)


class LighthouseReportViewSet(ProjectFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = LighthouseReportSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = LighthouseReport.objects.select_related('page', 'page__project').all()

    def get_queryset(self):
        qs = super().get_queryset()
        page_id = self.request.query_params.get('page')
        project_id = self.request.query_params.get('project')
        if page_id:
            qs = qs.filter(page_id=page_id)
        if project_id:
            qs = qs.filter(page__project_id=project_id)
        return qs

    @extend_schema(summary='Full Lighthouse report JSON (LHR)')
    @action(detail=True, methods=['get'], url_path='json')
    def json_report(self, request, pk=None):
        report = self.get_object()
        if not report.report_json_file:
            return Response(
                {'detail': 'Report JSON file not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            raw = report.report_json_file.read()
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            data = json.loads(raw)
        except Exception as exc:
            return Response(
                {'detail': f'Error loading report: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)

class FaviconViewSet(ProjectFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = FaviconSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Favicon.objects.select_related('project').all()

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class CeleryTaskLogViewSet(ProjectFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CeleryTaskLogSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = CeleryTaskLog.objects.select_related('project').all()

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs


class ServerViewSet(ProjectFilterMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ServerSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Server.objects.prefetch_related('authbasic').all().order_by('-last_seen')


class MetricsViewSet(ProjectFilterMixin, viewsets.ModelViewSet):
    serializer_class = MetricsSerializer
    permission_classes = [IsApprovedUser, IsProjectOwner]
    queryset = Metrics.objects.all().order_by('url')


class ProfileView(APIView):
    permission_classes = [IsApprovedUser]

    @extend_schema(summary='Get current user profile', responses=ProfileSerializer)
    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return Response(ProfileSerializer(profile).data)

    @extend_schema(summary='Update current user profile', request=ProfileSerializer, responses=ProfileSerializer)
    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(profile).data)


class MeView(APIView):
    permission_classes = [IsApprovedUser]

    @extend_schema(summary='Get current authenticated user')
    def get(self, request):
        return Response({
            'user': UserSerializer(request.user).data,
        })


class DashboardView(APIView):
    permission_classes = [IsApprovedUser]

    @extend_schema(summary='Dashboard summary')
    def get(self, request):
        projects = Project.objects.filter(user=request.user)
        return Response({
            'projects_count': projects.count(),
            'pages_count': Pages.objects.filter(project__user=request.user).count(),
            'services_count': Service.objects.filter(project__user=request.user).count(),
            'open_incidents': Incident.objects.filter(
                service__project__user=request.user, status=2,
            ).count(),
            'servers_count': Server.objects.filter(user=request.user).count(),
            'recent_notifications': NotificationSerializer(
                Notification.objects.filter(project__user=request.user).order_by('-date')[:10],
                many=True,
            ).data,
        })
