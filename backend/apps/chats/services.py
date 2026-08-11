from django.db.models import Q

from .models import ChatThread


def ensure_group_thread(course):
    thread, _ = ChatThread.objects.get_or_create(kind=ChatThread.Kind.GROUP, course=course)
    return thread


def ensure_direct_thread(student):
    thread, _ = ChatThread.objects.get_or_create(kind=ChatThread.Kind.DIRECT, student=student)
    return thread


def threads_for_user(user):
    """Список чатов, которые видит пользователь."""
    if user.role == 'admin':
        return ChatThread.objects.all().select_related('course', 'student').order_by('-id')

    from apps.courses.models import Course
    course_ids = list(Course.objects.filter(enrollments__user=user).values_list('id', flat=True))
    direct = ensure_direct_thread(user)
    return ChatThread.objects.filter(
        Q(kind=ChatThread.Kind.GROUP, course_id__in=course_ids) | Q(id=direct.id)
    ).select_related('course', 'student').order_by('-id')


def can_access_thread(user, thread):
    if user.role == 'admin':
        return True
    if thread.kind == ChatThread.Kind.DIRECT:
        return thread.student_id == user.id
    if thread.kind == ChatThread.Kind.GROUP:
        from apps.courses.models import Enrollment
        return Enrollment.objects.filter(user=user, course=thread.course).exists()
    return False
