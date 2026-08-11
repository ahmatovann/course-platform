from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')


class IsEnrolledOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == 'admin':
            return True
        course = obj if obj.__class__.__name__ == 'Course' else obj.course
        return course.enrollments.filter(user=user).exists()
