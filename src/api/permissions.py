from django.conf import settings
from rest_framework import permissions


def user_is_approved(user):
    if not user.is_authenticated:
        return False
    if settings.SAAS and not user.is_staff:
        return False
    return True


class IsApprovedUser(permissions.BasePermission):
    """Authenticated user approved for SaaS access when SAAS mode is enabled."""

    def has_permission(self, request, view):
        return user_is_approved(request.user)


class IsProjectOwner(permissions.BasePermission):
    """Object belongs to the authenticated user via project or direct ownership."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
        if hasattr(obj, 'project'):
            return obj.project.user_id == request.user.id
        if hasattr(obj, 'page'):
            return obj.page.project.user_id == request.user.id
        if hasattr(obj, 'service'):
            return obj.service.project.user_id == request.user.id
        if hasattr(obj, 'from_page'):
            return obj.from_page.project.user_id == request.user.id
        return False
