from django.contrib.auth.models import User
from rest_framework import serializers

from availability.models import HTTPCodeService, HTTPMockedCodeService, Service
from favicons.models import Favicon
from incidents.models import Incident
from lighthouse.models import LighthouseReport
from logs.models import CeleryTaskLog
from notifications.models import Emails, Notification
from profile.models import Profile
from projects.models import PageLink, Pages, Project
from reports.models import ProjectReport
from workers.models import AuthBasic, Metrics, Server


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    # CharField avoids drf-spectacular failing on TimeZoneField ZoneInfo choices
    timezone = serializers.CharField(allow_null=True, required=False)

    class Meta:
        model = Profile
        fields = ['user', 'disable_auto_redirect', 'timezone']


class ProjectSerializer(serializers.ModelSerializer):
    is_offline = serializers.SerializerMethodField()
    is_degraded = serializers.SerializerMethodField()
    is_warning = serializers.SerializerMethodField()
    availability_30d = serializers.SerializerMethodField()
    performance_score = serializers.SerializerMethodField()
    incidents_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'url', 'is_favorite', 'enable_public_page',
            'sitemap_task_status', 'sitemap_last_edited', 'created_at',
            'is_offline', 'is_degraded', 'is_warning',
            'availability_30d', 'performance_score', 'incidents_count',
        ]
        read_only_fields = [
            'sitemap_task_status', 'sitemap_last_edited', 'created_at',
            'is_offline', 'is_degraded', 'is_warning',
            'availability_30d', 'performance_score', 'incidents_count',
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_is_offline(self, obj):
        return bool(obj.is_offline())

    def get_is_degraded(self, obj):
        return bool(obj.is_degraded())

    def get_is_warning(self, obj):
        return bool(obj.is_warning())

    def get_availability_30d(self, obj):
        return obj.availability(days=30)

    def get_performance_score(self, obj):
        return obj.performance_score()


class PageSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    next_lighthouse_run = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Pages
        fields = [
            'id', 'project', 'project_title', 'url', 'title', 'description',
            'http_status', 'created_at', 'sitemap_last_seen', 'scraping_last_seen',
            'lighthouse_last_request', 'next_lighthouse_run', 'scraping_task_log',
        ]
        read_only_fields = [
            'created_at', 'sitemap_last_seen', 'scraping_last_seen',
            'lighthouse_last_request', 'next_lighthouse_run', 'scraping_task_log',
        ]

    def validate_project(self, project):
        if project.user != self.context['request'].user:
            raise serializers.ValidationError('Project not found or access denied.')
        return project


class PageLinkSerializer(serializers.ModelSerializer):
    from_page_url = serializers.URLField(source='from_page.url', read_only=True)
    to_page_url = serializers.URLField(source='to_page.url', read_only=True)

    class Meta:
        model = PageLink
        fields = [
            'id', 'from_page', 'to_page', 'from_page_url', 'to_page_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class HTTPCodeServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HTTPCodeService
        fields = ['id', 'url', 'tls_skip_verify']


class HTTPMockedCodeServiceSerializer(serializers.ModelSerializer):
    mocked_url = serializers.SerializerMethodField()

    class Meta:
        model = HTTPMockedCodeService
        fields = ['id', 'code', 'mocked_url']

    def get_mocked_url(self, obj):
        return obj.url()


class ServiceSerializer(serializers.ModelSerializer):
    service_type = serializers.SerializerMethodField()
    http_code = HTTPCodeServiceSerializer(source='httpcode', read_only=True)
    http_mocked_code = HTTPMockedCodeServiceSerializer(source='httpmockedcode', read_only=True)
    availability_30d = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'project', 'title', 'is_public', 'is_enabled', 'is_critical',
            'creation_date', 'service_type', 'http_code', 'http_mocked_code',
            'availability_30d',
        ]
        read_only_fields = ['creation_date', 'service_type', 'http_code', 'http_mocked_code', 'availability_30d']

    def get_service_type(self, obj):
        try:
            obj.httpcode
            return 'http_code'
        except HTTPCodeService.DoesNotExist:
            pass
        try:
            obj.httpmockedcode
            return 'http_mocked'
        except HTTPMockedCodeService.DoesNotExist:
            pass
        return None

    def get_availability_30d(self, obj):
        return obj.availability(days=30)

    def validate_project(self, project):
        if project.user != self.context['request'].user:
            raise serializers.ValidationError('Project not found or access denied.')
        return project


class ServiceCreateSerializer(serializers.Serializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    title = serializers.CharField(max_length=128)
    is_public = serializers.BooleanField(default=True)
    is_enabled = serializers.BooleanField(default=True)
    is_critical = serializers.BooleanField(default=True)
    type = serializers.ChoiceField(choices=['http_code', 'http_mocked'])
    url = serializers.URLField(required=False)
    tls_skip_verify = serializers.BooleanField(default=False, required=False)
    code = serializers.IntegerField(required=False)

    def validate_project(self, project):
        if project.user != self.context['request'].user:
            raise serializers.ValidationError('Project not found or access denied.')
        return project

    def validate(self, data):
        service_type = data['type']
        if service_type == 'http_code' and not data.get('url'):
            raise serializers.ValidationError({'url': 'Required for http_code services.'})
        if service_type == 'http_mocked' and data.get('code') is None:
            raise serializers.ValidationError({'code': 'Required for http_mocked services.'})
        return data

    def create(self, validated_data):
        service_type = validated_data.pop('type')
        url = validated_data.pop('url', None)
        tls_skip_verify = validated_data.pop('tls_skip_verify', False)
        code = validated_data.pop('code', None)

        service = Service.objects.create(**validated_data)
        if service_type == 'http_code':
            HTTPCodeService.objects.create(
                service=service, url=url, tls_skip_verify=tls_skip_verify,
            )
        else:
            HTTPMockedCodeService.objects.create(service=service, code=code)
        return service


class IncidentSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source='service.project_id', read_only=True)
    service_title = serializers.CharField(source='service.title', read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = [
            'id', 'alert_name', 'starts_at', 'ends_at', 'status', 'severity',
            'summary', 'description', 'creation_date', 'service', 'project_id',
            'service_title', 'duration_seconds',
        ]
        read_only_fields = [
            'alert_name', 'starts_at', 'creation_date', 'service',
            'project_id', 'service_title', 'duration_seconds',
        ]

    def get_duration_seconds(self, obj):
        return int(obj.duration.total_seconds())


class NotificationSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True, allow_null=True)
    service_title = serializers.CharField(source='service.title', read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'date', 'message', 'severity', 'project', 'service',
            'project_title', 'service_title',
        ]
        read_only_fields = fields


class EmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emails
        fields = ['id', 'project', 'email']

    def validate_project(self, project):
        if project.user != self.context['request'].user:
            raise serializers.ValidationError('Project not found or access denied.')
        return project


class ReportSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = ProjectReport
        fields = [
            'id', 'project', 'project_title', 'data', 'creation_date', 'celery_task_log',
        ]
        read_only_fields = fields


class LighthouseReportSerializer(serializers.ModelSerializer):
    page_url = serializers.URLField(source='page.url', read_only=True)
    screenshot_url = serializers.SerializerMethodField()
    report_json_url = serializers.SerializerMethodField()

    class Meta:
        model = LighthouseReport
        fields = [
            'id', 'page', 'page_url', 'form_factor', 'score_performance',
            'score_accessibility', 'score_best_practices', 'score_seo', 'score_pwa',
            'screenshot_url', 'report_json_url', 'creation_date', 'celery_task_log',
        ]
        read_only_fields = fields

    def get_screenshot_url(self, obj):
        if obj.screenshot:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.screenshot.url)
            return obj.screenshot.url
        return None

    def get_report_json_url(self, obj):
        if obj.report_json_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.report_json_file.url)
            return obj.report_json_file.url
        return None


class FaviconSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    favicon_url = serializers.SerializerMethodField()

    class Meta:
        model = Favicon
        fields = [
            'id', 'project', 'project_title', 'favicon_url', 'task_status',
            'last_edited', 'created_at', 'updated_at', 'celery_task_log',
        ]
        read_only_fields = fields

    def get_favicon_url(self, obj):
        if obj.favicon:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.favicon.url)
            return obj.favicon.url
        return None


class CeleryTaskLogSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = CeleryTaskLog
        fields = [
            'id', 'project', 'project_title', 'task_name', 'duration', 'created_at',
        ]
        read_only_fields = fields


class AuthBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthBasic
        fields = ['id', 'username', 'password']
        read_only_fields = fields


class ServerSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)
    is_public = serializers.BooleanField(read_only=True)
    last_seen_from = serializers.CharField(read_only=True)
    auth_credentials = AuthBasicSerializer(source='authbasic', many=True, read_only=True)

    class Meta:
        model = Server
        fields = [
            'id', 'ip', 'uuid', 'creation_date', 'last_modified_setup', 'last_seen',
            'monitoring', 'performance', 'is_active', 'is_public', 'last_seen_from',
            'auth_credentials',
        ]
        read_only_fields = fields


class MetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metrics
        fields = ['id', 'url', 'is_enabled']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
