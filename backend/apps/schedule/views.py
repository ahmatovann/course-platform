from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.courses.models import Course
from apps.notifications.models import notify_many

from .models import ScheduleEvent
from .serializers import ScheduleEventSerializer, ScheduleEventWriteSerializer


class ScheduleListView(generics.ListAPIView):
    """Ученику показываем события его курсов и общие события; админу — всё.
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
        course_ids = Course.objects.filter(enrollments__user=user).values_list('id', flat=True)
        return qs.filter(Q(course__isnull=True) | Q(course_id__in=course_ids))


class ScheduleCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = ScheduleEventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(created_by=request.user)

        User = request.user.__class__
        if event.course_id:
            recipients = User.objects.filter(enrollments__course_id=event.course_id).distinct()
        else:
            recipients = User.objects.filter(role='student')
        notify_many(list(recipients), f'Новая новость: «{event.title}»', url='/news')

        return Response(ScheduleEventSerializer(event).data, status=status.HTTP_201_CREATED)


class ScheduleUpdateDeleteView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        event = get_object_or_404(ScheduleEvent, pk=pk)
        serializer = ScheduleEventWriteSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ScheduleEventSerializer(event).data)

    def delete(self, request, pk):
        event = get_object_or_404(ScheduleEvent, pk=pk)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
