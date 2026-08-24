from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.accounts.utils import generate_password, send_welcome_email
from apps.courses.models import Course, Enrollment

from .serializers import StudentSerializer, CreateStudentSerializer

User = get_user_model()


class StudentListView(generics.ListAPIView):
    """Список учеников с поиском (?search=), фильтром по статусу
    (?status=active|inactive) и по прохождению конкретного модуля
    (?module_completed=<id>) — чтобы увидеть, кто из учеников уже прошёл
    определённый модуль тренинга (и сколько всего)."""
    serializer_class = StudentSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = User.objects.filter(role=User.Role.STUDENT).order_by('-date_joined')
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) | Q(last_name__icontains=search)
                | Q(email__icontains=search) | Q(phone__icontains=search)
            )
        status_param = self.request.query_params.get('status')
        if status_param == 'active':
            qs = qs.filter(is_active_student=True)
        elif status_param == 'inactive':
            qs = qs.filter(is_active_student=False)

        module_id = self.request.query_params.get('module_completed')
        if module_id:
            from apps.courses.models import Module
            from apps.courses.services import module_status

            module = Module.objects.filter(pk=module_id).first()
            if module is None:
                return qs.none()
            enrolled = qs.filter(enrollments__course_id=module.course_id).distinct()
            completed_ids = [s.id for s in enrolled if module_status(s, module)['completed']]
            qs = User.objects.filter(id__in=completed_ids).order_by('-date_joined')
        return qs


class CreateStudentView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = CreateStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        name_parts = data['name'].strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        password = generate_password()
        user = User.objects.create_user(
            username=data['email'], email=data['email'], password=password,
            first_name=first_name, last_name=last_name, phone=data.get('phone', ''),
            role=User.Role.STUDENT, must_change_password=True,
        )
        course = data.get('course_id')
        if course:
            Enrollment.objects.get_or_create(user=user, course=course)

        send_welcome_email(user, password)

        return Response({
            'student': StudentSerializer(user).data,
            'email': user.email,
            'login': user.email,
            'password': password,
        }, status=status.HTTP_201_CREATED)


class ToggleStudentStatusView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        user = User.objects.filter(pk=pk, role=User.Role.STUDENT).first()
        if not user:
            return Response({'detail': 'Не найден'}, status=404)
        user.is_active_student = not user.is_active_student
        user.is_active = user.is_active_student
        user.save(update_fields=['is_active_student', 'is_active'])
        return Response(StudentSerializer(user).data)


class StudentEnrollView(APIView):
    """Записать ученика на дополнительный тренинг или снять с него.
    Без ограничений по количеству — можно одновременно иметь доступ
    сразу к нескольким курсам, ранее выданный доступ не отзывается."""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
        course = get_object_or_404(Course, pk=request.data.get('course_id'))
        Enrollment.objects.get_or_create(user=student, course=course)
        return Response(StudentSerializer(student).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        student = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)
        course_id = request.data.get('course_id')
        Enrollment.objects.filter(user=student, course_id=course_id).delete()
        return Response(StudentSerializer(student).data)


# ===== Конструктор тренинга (курсы/модули/уроки) =====

from django.shortcuts import get_object_or_404  # noqa: E402
from rest_framework import generics as drf_generics  # noqa: E402

from apps.courses.models import Course, Module, Lesson, Test  # noqa: E402
from .serializers import (  # noqa: E402
    AdminCourseSerializer, AdminModuleUpdateSerializer, AdminModuleSerializer,
    AdminLessonWriteSerializer, AdminLessonSerializer,
    AdminTestSerializer, AdminTestWriteSerializer,
)


class AdminCourseListView(drf_generics.ListAPIView):
    """Список тренингов с поиском по названию/описанию (?search=)."""
    serializer_class = AdminCourseSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = Course.objects.all().prefetch_related('modules__lessons', 'modules__test')
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
        return qs


class AdminModuleUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        module = get_object_or_404(Module, pk=pk)
        serializer = AdminModuleUpdateSerializer(module, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminModuleSerializer(module).data)

    def delete(self, request, pk):
        module = get_object_or_404(Module, pk=pk)
        module.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminLessonCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, module_id):
        module = get_object_or_404(Module, pk=module_id)
        count = module.lessons.count()
        serializer = AdminLessonWriteSerializer(data={
            **request.data,
            'order': request.data.get('order', count + 1),
        })
        serializer.is_valid(raise_exception=True)
        lesson = serializer.save(module=module)
        if lesson.video_file:
            from apps.courses.media_utils import transcode_lesson_video
            transcode_lesson_video(lesson)

        from apps.notifications.models import notify_many
        students = User.objects.filter(enrollments__course=module.course).distinct()
        notify_many(list(students), f'Новый урок «{lesson.title}» в курсе «{module.course.title}»', url=f'/lessons/{lesson.id}')

        return Response(AdminLessonSerializer(lesson).data, status=status.HTTP_201_CREATED)


class AdminLessonUpdateDeleteView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        serializer = AdminLessonWriteSerializer(lesson, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Перекодируем видео в совместимый формат (H.264+AAC/MP4) только когда
        # в этом запросе реально пришёл новый файл — чтобы звук гарантированно
        # воспроизводился в любом браузере независимо от исходного кодека.
        if 'video_file' in request.data:
            from apps.courses.media_utils import transcode_lesson_video
            transcode_lesson_video(lesson)
        return Response(AdminLessonSerializer(lesson).data)

    def delete(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        lesson.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ===== Тесты =====

class AdminTestListView(drf_generics.ListAPIView):
    """Список тестов с поиском по названию теста/модуля (?search=)."""
    serializer_class = AdminTestSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = Test.objects.all().select_related('module').prefetch_related('questions__options')
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(module__title__icontains=search))
        return qs


class AdminTestDetailView(drf_generics.RetrieveAPIView):
    serializer_class = AdminTestSerializer
    permission_classes = [IsAdmin]
    queryset = Test.objects.all().select_related('module').prefetch_related('questions__options')


class AdminTestCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = AdminTestWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.save()

        from apps.notifications.models import notify_many
        students = User.objects.filter(enrollments__course=test.module.course).distinct()
        notify_many(list(students), f'Новый тест «{test.title}» в курсе «{test.module.course.title}»', url=f'/tests/{test.id}')

        return Response(AdminTestSerializer(test).data, status=status.HTTP_201_CREATED)


class AdminTestUpdateDeleteView(APIView):
    permission_classes = [IsAdmin]

    def put(self, request, pk):
        test = get_object_or_404(Test, pk=pk)
        serializer = AdminTestWriteSerializer(test, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminTestSerializer(test).data)

    def delete(self, request, pk):
        test = get_object_or_404(Test, pk=pk)
        test.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ===== Прогресс ученика (для админа) =====

from apps.courses.models import Course as _Course  # noqa: E402
from apps.courses.services import module_status, is_module_unlocked  # noqa: E402


class StudentProgressView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        from apps.courses.models import TestAttempt

        student = get_object_or_404(User, pk=pk, role='student')
        courses = _Course.objects.filter(enrollments__user=student).prefetch_related(
            'modules__lessons', 'modules__test'
        ).distinct()

        result = []
        for course in courses:
            modules_data = []
            for m in course.modules.all().order_by('order'):
                st = module_status(student, m)
                test = getattr(m, 'test', None)
                # Полная история попыток теста (не только лучший результат) —
                # ученик может пересдавать тест с другими ответами, и админу
                # важно видеть, сколько раз и как он его сдавал.
                attempts = []
                if test:
                    attempts = [
                        {
                            'id': a.id,
                            'score_percent': a.score_percent,
                            'passed': a.passed,
                            'submitted_at': a.submitted_at,
                        }
                        for a in TestAttempt.objects.filter(user=student, test=test).order_by('-submitted_at')
                    ]
                modules_data.append({
                    'id': m.id,
                    'title': m.title,
                    'order': m.order,
                    'unlocked': is_module_unlocked(student, m),
                    'test_attempts': attempts,
                    'test_attempts_count': len(attempts),
                    **st,
                })
            course_modules_completed = sum(1 for md in modules_data if md['completed'])
            result.append({
                'course_id': course.id,
                'course_title': course.title,
                'modules': modules_data,
                'modules_total': len(modules_data),
                'modules_completed': course_modules_completed,
                'completion_percent': (
                    round(course_modules_completed / len(modules_data) * 100) if modules_data else 0
                ),
            })

        return Response({
            'student': {
                'id': student.id,
                'name': f'{student.first_name} {student.last_name}'.strip() or student.email,
                'email': student.email,
            },
            'courses': result,
        })


class ModuleCompletionStatsView(APIView):
    """Аналитика по модулям: сколько учеников записано на курс модуля и
    сколько из них уже прошли этот конкретный модуль — используется на
    странице «Прогресс», чтобы быстро увидеть охват по каждому модулю и
    отфильтровать список учеников по прохождению выбранного модуля."""
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.courses.models import Module
        from apps.courses.services import module_status

        result = []
        modules = Module.objects.select_related('course').order_by('course__title', 'order')
        for m in modules:
            enrolled_students = list(User.objects.filter(role='student', enrollments__course_id=m.course_id).distinct())
            completed_count = sum(1 for s in enrolled_students if module_status(s, m)['completed'])
            total = len(enrolled_students)
            result.append({
                'id': m.id,
                'title': m.title,
                'order': m.order,
                'course_id': m.course_id,
                'course_title': m.course.title,
                'total_enrolled': total,
                'completed_count': completed_count,
                'completed_percent': round(completed_count / total * 100) if total else 0,
            })
        return Response(result)


# ===== Экспорт в Excel =====

from django.http import FileResponse  # noqa: E402

from .exports import export_student_progress_xlsx, export_students_xlsx  # noqa: E402

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class StudentProgressExportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        student = get_object_or_404(User, pk=pk, role='student')
        courses = _Course.objects.filter(enrollments__user=student).prefetch_related(
            'modules__lessons', 'modules__test'
        ).distinct()

        courses_data = []
        for course in courses:
            modules_data = []
            for m in course.modules.all().order_by('order'):
                st = module_status(student, m)
                modules_data.append({'title': m.title, 'unlocked': is_module_unlocked(student, m), **st})
            courses_data.append({'course_title': course.title, 'modules': modules_data})

        buffer = export_student_progress_xlsx(courses_data)
        filename = f'progress-{student.email}.xlsx'
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type=XLSX_CONTENT_TYPE)


class StudentsExportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        students = User.objects.filter(role=User.Role.STUDENT).order_by('-date_joined').prefetch_related(
            'enrollments__course'
        )
        buffer = export_students_xlsx(students)
        return FileResponse(buffer, as_attachment=True, filename='students.xlsx', content_type=XLSX_CONTENT_TYPE)


# ===== Материалы урока (слайды, аудио, PDF и т.д.) =====

from apps.courses.models import Material  # noqa: E402
from .serializers import AdminMaterialSerializer, AdminMaterialWriteSerializer  # noqa: E402


class AdminMaterialCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        serializer = AdminMaterialWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        material = serializer.save(lesson=lesson)
        return Response(AdminMaterialSerializer(material).data, status=status.HTTP_201_CREATED)


class AdminMaterialDeleteView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        """Переименовать материал (и/или заменить сам файл) — используется
        из библиотеки материалов в админке."""
        material = get_object_or_404(Material, pk=pk)
        serializer = AdminMaterialWriteSerializer(material, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminMaterialSerializer(material).data)

    def delete(self, request, pk):
        material = get_object_or_404(Material, pk=pk)
        material.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminLessonVideoDeleteView(APIView):
    """Убрать только видео (и связанные с ним превью/аудио-версию) урока,
    не удаляя сам урок — отдельно от полного удаления урока, для
    библиотеки материалов в админке."""
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        lesson.video_file.delete(save=False)
        lesson.video_poster.delete(save=False)
        lesson.video_audio_file.delete(save=False)
        lesson.video_file = None
        lesson.video_poster = None
        lesson.video_audio_file = None
        lesson.duration_seconds = 0
        lesson.save(update_fields=['video_file', 'video_poster', 'video_audio_file', 'duration_seconds'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminLessonVideoTrimView(APIView):
    """Обрезать уже загруженное видео урока по началу/концу (в секундах) —
    без повторной загрузки файла. Используется и из конструктора тренинга,
    и из библиотеки материалов в админке."""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        from apps.courses.media_utils import trim_lesson_video

        lesson = get_object_or_404(Lesson, pk=pk)
        if not lesson.video_file:
            return Response({'detail': 'У урока нет видео'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start = float(request.data.get('start'))
            end = float(request.data.get('end'))
        except (TypeError, ValueError):
            return Response({'detail': 'Некорректные начало/конец'}, status=status.HTTP_400_BAD_REQUEST)

        if start < 0 or end <= start:
            return Response({'detail': 'Конец должен быть позже начала'}, status=status.HTTP_400_BAD_REQUEST)
        if lesson.duration_seconds and end > lesson.duration_seconds + 1:
            return Response({'detail': 'Конец не может быть длиннее видео'}, status=status.HTTP_400_BAD_REQUEST)

        ok = trim_lesson_video(lesson, start, end)
        if not ok:
            return Response(
                {'detail': 'Не удалось обрезать видео — попробуйте ещё раз'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(AdminLessonSerializer(lesson).data)


# ===== Создание курсов и модулей =====

from .serializers import AdminCourseWriteSerializer, AdminModuleWriteSerializer  # noqa: E402


class AdminCourseCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = AdminCourseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        return Response(AdminCourseSerializer(course).data, status=status.HTTP_201_CREATED)


class AdminModuleCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, course_id):
        course = get_object_or_404(Course, pk=course_id)
        count = course.modules.count()
        serializer = AdminModuleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        module = serializer.save(
            course=course, order=count + 1,
            require_test_to_unlock_next=True, pass_threshold_percent=80, allow_downloads=True,
        )
        return Response(AdminModuleSerializer(module).data, status=status.HTTP_201_CREATED)


# ===== Библиотека материалов (все загруженные видео уроков + материалы) =====
# Единый список для админки: кадр/превью, размер, что это, где используется
# (курс → модуль → урок), название — с переименованием и удалением на месте,
# без необходимости заходить в конструктор тренинга ради каждого файла.

MEDIA_KIND_LABELS = {
    'image': 'Изображение', 'audio': 'Аудио', 'video': 'Видео',
    'presentation': 'Презентация', 'pdf': 'PDF-документ', 'file': 'Файл',
    'document': 'Документ Word', 'spreadsheet': 'Таблица Excel', 'archive': 'Архив', 'text': 'Текстовый файл',
}


def _file_size(field):
    if not field:
        return None
    try:
        return field.size
    except (OSError, ValueError):
        return None


class AdminMediaListView(APIView):
    """Список всех загруженных файлов (видео уроков + материалы уроков) с
    поиском (?search=) по названию/месту использования и сортировкой
    (?sort=name_asc|name_desc|size_asc|size_desc|used_in_asc|used_in_desc)."""
    permission_classes = [IsAdmin]

    def get(self, request):
        search = request.query_params.get('search', '').strip().lower()
        sort = request.query_params.get('sort', 'name_asc')

        items = []

        lessons = (
            Lesson.objects.exclude(video_file='').filter(video_file__isnull=False)
            .select_related('module__course')
        )
        for lesson in lessons:
            module = lesson.module
            course = module.course
            items.append({
                'id': f'video-{lesson.id}',
                'type': 'video',
                'kind_label': 'Видео',
                'name': lesson.title,
                'thumb': request.build_absolute_uri(lesson.video_poster.url) if lesson.video_poster else None,
                'size_bytes': _file_size(lesson.video_file),
                'used_in': f'{course.title} → {module.title} → {lesson.title}',
                'course_id': course.id,
                'module_id': module.id,
                'lesson_id': lesson.id,
                'url': request.build_absolute_uri(lesson.video_file.url),
                'duration_seconds': lesson.duration_seconds,
            })

        materials = (
            Material.objects.exclude(file='').filter(file__isnull=False)
            .select_related('lesson__module__course')
        )
        for material in materials:
            lesson = material.lesson
            module = lesson.module
            course = module.course
            items.append({
                'id': f'material-{material.id}',
                'type': 'material',
                'kind_label': MEDIA_KIND_LABELS.get(material.kind, 'Файл'),
                'name': material.name,
                'thumb': request.build_absolute_uri(material.file.url) if material.kind == 'image' else None,
                'size_bytes': _file_size(material.file),
                'used_in': f'{course.title} → {module.title} → {lesson.title}',
                'course_id': course.id,
                'module_id': module.id,
                'lesson_id': lesson.id,
                'material_id': material.id,
                'url': request.build_absolute_uri(material.file.url),
                'file_kind': material.kind,
            })

        if search:
            items = [
                item for item in items
                if search in item['name'].lower() or search in item['used_in'].lower()
            ]

        reverse = sort.endswith('_desc')
        key_name = sort.rsplit('_', 1)[0] if sort.endswith(('_asc', '_desc')) else sort
        key_funcs = {
            'name': lambda i: i['name'].lower(),
            'size': lambda i: i['size_bytes'] or 0,
            'used_in': lambda i: i['used_in'].lower(),
            'type': lambda i: i['type'],
        }
        items.sort(key=key_funcs.get(key_name, key_funcs['name']), reverse=reverse)

        return Response(items)
