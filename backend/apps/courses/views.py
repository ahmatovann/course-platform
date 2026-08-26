from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .certificates import generate_certificate_pdf
from .models import Course, Module, Lesson, Material, Test, LessonProgress, Enrollment, Comment
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, ModuleDetailSerializer,
    LessonDetailSerializer, TestPublicSerializer, TestSubmitSerializer,
    TestAttemptSerializer, CommentSerializer,
    MaterialSerializer, FavoriteMaterialSerializer,
)
from .services import course_progress_percent


def _is_enrolled(user, course):
    return Enrollment.objects.filter(user=user, course=course).exists()


class CourseListView(generics.ListAPIView):
    """Ученик видит только те тренинги, на которые записан администратором —
    остальные (в т.ч. недавно добавленные) не показываются вовсе."""
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Course.objects.filter(is_published=True)
        if self.request.user.role != 'admin':
            qs = qs.filter(enrollments__user=self.request.user)
        return qs.distinct()


class CourseDetailView(generics.RetrieveAPIView):
    serializer_class = CourseDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        qs = Course.objects.filter(is_published=True)
        if self.request.user.role != 'admin':
            qs = qs.filter(enrollments__user=self.request.user)
        return qs.distinct()


class ModuleDetailView(generics.RetrieveAPIView):
    serializer_class = ModuleDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Module.objects.all()
        if self.request.user.role != 'admin':
            qs = qs.filter(course__enrollments__user=self.request.user)
        return qs.distinct()


class LessonDetailView(generics.RetrieveAPIView):
    serializer_class = LessonDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Lesson.objects.all()
        if self.request.user.role != 'admin':
            qs = qs.filter(module__course__enrollments__user=self.request.user)
        return qs.distinct()


class MaterialFavoriteView(APIView):
    """Добавить/убрать файл урока из избранного — у каждого ученика своё."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        material = get_object_or_404(Material, pk=pk)
        if request.user.role != 'admin' and not _is_enrolled(request.user, material.lesson.module.course):
            return Response({'detail': 'Нет доступа к этому уроку'}, status=status.HTTP_403_FORBIDDEN)
        material.favorited_by.add(request.user)
        return Response(MaterialSerializer(material, context={'request': request}).data)

    def delete(self, request, pk):
        material = get_object_or_404(Material, pk=pk)
        material.favorited_by.remove(request.user)
        return Response(MaterialSerializer(material, context={'request': request}).data)


class FavoriteMaterialsListView(APIView):
    """Все файлы, которые ученик отметил «в избранное» — по всем тренингам
    сразу, с указанием курса/модуля/урока, где файл находится."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        materials = Material.objects.filter(favorited_by=request.user).select_related('lesson__module__course')
        return Response(FavoriteMaterialSerializer(materials, many=True, context={'request': request}).data)


class MarkLessonWatchedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        if request.user.role != 'admin' and not _is_enrolled(request.user, lesson.module.course):
            return Response({'detail': 'Нет доступа к этому тренингу'}, status=status.HTTP_403_FORBIDDEN)
        from django.utils import timezone
        progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        progress.watched = True
        progress.watched_at = timezone.now()
        progress.save()
        return Response({'detail': 'Урок отмечен просмотренным'})


class LessonCommentsView(APIView):
    """Комментарии под видео урока: список и добавление. Автору-ученику
    комментарий виден сразу, администратору приходит уведомление с указанием
    курса/модуля/урока и того, кто написал."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        if request.user.role != 'admin' and not _is_enrolled(request.user, lesson.module.course):
            return Response({'detail': 'Нет доступа к этому уроку'}, status=status.HTTP_403_FORBIDDEN)
        comments = lesson.comments.select_related('user').all()
        return Response(CommentSerializer(comments, many=True, context={'request': request}).data)

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        if request.user.role != 'admin' and not _is_enrolled(request.user, lesson.module.course):
            return Response({'detail': 'Нет доступа к этому уроку'}, status=status.HTTP_403_FORBIDDEN)
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'text': ['Комментарий не может быть пустым']}, status=status.HTTP_400_BAD_REQUEST)

        timestamp = request.data.get('video_timestamp_seconds')
        try:
            timestamp = int(timestamp) if timestamp not in (None, '') else None
        except (TypeError, ValueError):
            timestamp = None

        comment = Comment.objects.create(
            lesson=lesson, user=request.user, text=text, video_timestamp_seconds=timestamp,
        )
        self._notify(request, lesson, comment)
        return Response(
            CommentSerializer(comment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def _notify(self, request, lesson, comment):
        from apps.notifications.models import notify_many
        if request.user.role == 'admin':
            return  # уведомляем только когда пишет ученик
        User = request.user.__class__
        admins = User.objects.filter(role='admin')
        author = request.user.get_full_name() or request.user.email
        module = lesson.module
        text = (
            f'{author} оставил(а) комментарий к уроку «{lesson.title}» '
            f'(модуль «{module.title}», курс «{module.course.title}»)'
        )
        notify_many(list(admins), text, url=f'/lessons/{lesson.id}')


class TestDetailView(generics.RetrieveAPIView):
    serializer_class = TestPublicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Test.objects.all()
        if self.request.user.role != 'admin':
            qs = qs.filter(module__course__enrollments__user=self.request.user)
        return qs.distinct()


class TestSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        test = get_object_or_404(Test, pk=pk)
        if request.user.role != 'admin' and not _is_enrolled(request.user, test.module.course):
            return Response({'detail': 'Нет доступа к этому тренингу'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TestSubmitSerializer(data=request.data, context={'request': request, 'test': test})
        serializer.is_valid(raise_exception=True)
        attempt = serializer.save()
        return Response(TestAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)


class EnrollView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        Enrollment.objects.get_or_create(user=request.user, course=course)
        return Response({'detail': 'Записан на курс'})


class CertificateDownloadView(APIView):
    """Сертификат PDF выдаётся, только если курс пройден на 100%
    и у курса включена опция certificate_on_completion."""
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug, is_published=True)
        if not course.certificate_on_completion:
            return Response({'detail': 'Для этого курса сертификат не предусмотрен'}, status=status.HTTP_400_BAD_REQUEST)
        if not Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response({'detail': 'Вы не записаны на этот курс'}, status=status.HTTP_403_FORBIDDEN)
        percent = course_progress_percent(request.user, course)
        if percent < 100:
            return Response({'detail': 'Курс ещё не пройден полностью'}, status=status.HTTP_400_BAD_REQUEST)

        buffer = generate_certificate_pdf(request.user, course)
        filename = f'certificate-{course.slug}.pdf'
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')
