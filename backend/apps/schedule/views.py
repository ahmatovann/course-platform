from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.courses.models import Course
from apps.notifications.models import notify_many

from apps.admin_panel.models import log_action

from .models import ScheduleEvent
from .serializers import ScheduleEventSerializer, ScheduleEventWriteSerializer


def _news_visible_to_student(user, event):
    now = timezone.now()
    if event.publish_at > now:
        return False
    if event.hide_at and event.hide_at <= now:
        return False
    if event.course_id is None:
        return True
    return Course.objects.filter(id=event.course_id, enrollments__user=user).exists()


class ScheduleListView(generics.ListAPIView):
    """Ученику показываем только уже опубликованные новости (дата рассылки
    наступила и, если задана, дата скрытия ещё не наступила) его курсов и
    общие; админу — вообще всё, включая ещё не опубликованные (в статусе
    «запланирована») и уже скрытые, чтобы ими можно было управлять.
    Админ дополнительно может искать по названию/описанию (?search=) и
    фильтровать по тренингу (?course=<id>, course=none — только общие)."""
    serializer_class = ScheduleEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ScheduleEvent.objects.select_related('course')
        if user.role == 'admin':
            search = self.request.query_params.get('search', '').strip()
            if search:
                qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
            course_param = self.request.query_params.get('course')
            if course_param == 'none':
                qs = qs.filter(course__isnull=True)
            elif course_param:
                qs = qs.filter(course_id=course_param)
            return qs.all()

        now = timezone.now()
        qs = qs.filter(publish_at__lte=now).filter(Q(hide_at__isnull=True) | Q(hide_at__gt=now))
        course_ids = Course.objects.filter(enrollments__user=user).values_list('id', flat=True)
        return qs.filter(Q(course__isnull=True) | Q(course_id__in=course_ids))


class ScheduleCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = ScheduleEventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(created_by=request.user)

        # «Дата рассылки» здесь управляет только видимостью (публикацией) —
        # никакой реальной отправки email/push нет. Уведомление в
        # колокольчик отправляем сразу только если новость уже опубликована
        # (момент рассылки уже наступил); для новости, запланированной
        # на будущее, уведомление не шлётся — она просто станет видна сама,
        # когда наступит указанный момент.
        if event.publish_at <= timezone.now():
            User = request.user.__class__
            if event.course_id:
                recipients = User.objects.filter(enrollments__course_id=event.course_id).distinct()
            else:
                recipients = User.objects.filter(role='student')
            notify_many(list(recipients), f'Новая новость: «{event.title}»', url='/news')

        log_action(request, 'created', 'новость', event.title)
        return Response(ScheduleEventSerializer(event, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ScheduleUpdateDeleteView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        event = get_object_or_404(ScheduleEvent, pk=pk)
        serializer = ScheduleEventWriteSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request, 'updated', 'новость', event.title)
        return Response(ScheduleEventSerializer(event, context={'request': request}).data)

    def delete(self, request, pk):
        event = get_object_or_404(ScheduleEvent, pk=pk)
        title = event.title
        event.delete()
        log_action(request, 'deleted', 'новость', title)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NewsFavoriteView(APIView):
    """Добавить/убрать новость из избранного — у каждого ученика своё."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        event = get_object_or_404(ScheduleEvent, pk=pk)
        if request.user.role != 'admin' and not _news_visible_to_student(request.user, event):
            return Response({'detail': 'Нет доступа к этой новости'}, status=status.HTTP_403_FORBIDDEN)
        event.favorited_by.add(request.user)
        return Response(ScheduleEventSerializer(event, context={'request': request}).data)

    def delete(self, request, pk):
        event = get_object_or_404(ScheduleEvent, pk=pk)
        event.favorited_by.remove(request.user)
        return Response(ScheduleEventSerializer(event, context={'request': request}).data)


class FavoriteNewsListView(APIView):
    """Все новости, которые ученик отметил «в избранное»."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        events = ScheduleEvent.objects.filter(favorited_by=request.user).select_related('course')
        return Response(ScheduleEventSerializer(events, many=True, context={'request': request}).data)
