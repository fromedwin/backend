from rest_framework.exceptions import PermissionDenied


class ProjectFilterMixin:
    """Filter querysets to resources owned by the authenticated user."""

    project_field = 'project'
    user_field = 'user'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if hasattr(qs.model, self.user_field):
            return qs.filter(**{self.user_field: user})
        if hasattr(qs.model, self.project_field):
            return qs.filter(**{f'{self.project_field}__user': user})
        if hasattr(qs.model, 'page'):
            return qs.filter(page__project__user=user)
        if hasattr(qs.model, 'service'):
            return qs.filter(service__project__user=user)
        return qs

    def _get_owned_project(self, project_id):
        from projects.models import Project
        project = Project.objects.filter(pk=project_id, user=self.request.user).first()
        if not project:
            raise PermissionDenied('Project not found or access denied.')
        return project
