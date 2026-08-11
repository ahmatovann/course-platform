from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase

from apps.courses.models import Course, Enrollment, Lesson, Module, Test
from apps.chats.models import ChatThread

User = get_user_model()


class CreateStudentTests(APITestCase):
    """Создание ученика администратором: пароль генерируется автоматически,
    отправляется письмо, ученик может сразу войти новым паролем."""

    def setUp(self):
        self.url = '/api/admin/students/create/'
        self.course = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')
        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_create_student(self):
        payload = {'name': 'Мария Кузнецова', 'email': 'maria@example.com', 'phone': '', 'course_id': self.course.id}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('password', response.data)
        self.assertEqual(response.data['email'], 'maria@example.com')

        student = User.objects.get(email='maria@example.com')
        self.assertEqual(student.role, User.Role.STUDENT)
        self.assertTrue(student.check_password(response.data['password']))
        self.assertTrue(Enrollment.objects.filter(user=student, course=self.course).exists())

        # Приветственное письмо реально отправлено (в тестах Django подменяет
        # email-бэкенд на locmem, письма попадают в mail.outbox).
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('maria@example.com', mail.outbox[0].to)

        # Новый ученик сразу может войти созданным паролем.
        login = self.client.post(
            '/api/auth/login/', {'email': 'maria@example.com', 'password': response.data['password']}, format='json',
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_create_student(self):
        student = User.objects.create_user(
            username='regular@example.com', email='regular@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=student)
        response = self.client.post(self.url, {'name': 'X', 'email': 'x@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ToggleStudentStatusTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )
        self.student = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password='pass12345', role=User.Role.STUDENT, is_active_student=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_toggle_deactivates_and_reactivates_student(self):
        url = f'/api/admin/students/{self.student.id}/toggle/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active_student)

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active_student)


class StudentSearchFilterTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )
        User.objects.create_user(
            username='anna@example.com', email='anna@example.com', first_name='Анна',
            password='pass12345', role=User.Role.STUDENT, is_active_student=True,
        )
        User.objects.create_user(
            username='maria@example.com', email='maria@example.com', first_name='Мария',
            password='pass12345', role=User.Role.STUDENT, is_active_student=False,
        )
        self.client.force_authenticate(user=self.admin)

    def test_search_by_name(self):
        response = self.client.get('/api/admin/students/', {'search': 'Анна'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [s['email'] for s in response.data]
        self.assertEqual(emails, ['anna@example.com'])

    def test_filter_by_status(self):
        response = self.client.get('/api/admin/students/', {'status': 'inactive'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [s['email'] for s in response.data]
        self.assertEqual(emails, ['maria@example.com'])


class ModuleCompletionAnalyticsTests(APITestCase):
    """Прогресс: фильтр списка учеников по прохождению конкретного модуля
    и общая аналитика по модулям (сколько учеников прошли каждый модуль)."""

    def setUp(self):
        from apps.courses.models import TestAttempt

        self.admin = User.objects.create_user(
            username='admin3@example.com', email='admin3@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha-mc')
        self.module1 = Module.objects.create(
            course=self.course, title='Модуль 1', order=1, require_test_to_unlock_next=False,
        )
        self.module2 = Module.objects.create(course=self.course, title='Модуль 2', order=2)
        self.lesson1 = Lesson.objects.create(module=self.module1, title='Урок 1', order=1)

        self.anna = User.objects.create_user(
            username='anna2@example.com', email='anna2@example.com', first_name='Анна',
            password='pass12345', role=User.Role.STUDENT,
        )
        self.maria = User.objects.create_user(
            username='maria2@example.com', email='maria2@example.com', first_name='Мария',
            password='pass12345', role=User.Role.STUDENT,
        )
        Enrollment.objects.create(user=self.anna, course=self.course)
        Enrollment.objects.create(user=self.maria, course=self.course)

        # Анна просмотрела единственный урок модуля 1 — модуль завершён (без теста).
        from apps.courses.models import LessonProgress
        LessonProgress.objects.create(user=self.anna, lesson=self.lesson1, watched=True)
        # Мария урок не смотрела — модуль 1 не завершён.

        self.test_attempt_model = TestAttempt
        self.client.force_authenticate(user=self.admin)

    def test_student_list_filters_by_module_completed(self):
        response = self.client.get('/api/admin/students/', {'module_completed': self.module1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = {s['email'] for s in response.data}
        self.assertEqual(emails, {'anna2@example.com'})

    def test_module_completion_stats_endpoint(self):
        response = self.client.get('/api/admin/analytics/modules/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stats = {row['id']: row for row in response.data}
        self.assertEqual(stats[self.module1.id]['total_enrolled'], 2)
        self.assertEqual(stats[self.module1.id]['completed_count'], 1)
        self.assertEqual(stats[self.module1.id]['completed_percent'], 50)
        # У модуля 2 нет ни уроков, ни теста — он тривиально «пройден» у всех
        # записанных учеников (та же логика, что и в module_status()).
        self.assertEqual(stats[self.module2.id]['completed_count'], 2)

    def test_progress_view_includes_test_attempt_history(self):
        test = Test.objects.create(module=self.module2, title='Тест модуля 2')
        self.test_attempt_model.objects.create(user=self.anna, test=test, score_percent=40, passed=False)
        self.test_attempt_model.objects.create(user=self.anna, test=test, score_percent=90, passed=True)

        response = self.client.get(f'/api/admin/students/{self.anna.id}/progress/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_data = response.data['courses'][0]
        module2_data = next(m for m in course_data['modules'] if m['id'] == self.module2.id)
        self.assertEqual(module2_data['test_attempts_count'], 2)
        # Новейшая попытка — первая в списке.
        self.assertEqual(module2_data['test_attempts'][0]['score_percent'], 90)
        self.assertEqual(module2_data['test_attempts'][1]['score_percent'], 40)
        self.assertIn('completion_percent', course_data)


class ChatMessageTests(APITestCase):
    """Отправка сообщения в чат: сообщение сохраняется в базе и видно
    после повторного запроса (не пропадает при обновлении страницы)."""

    def setUp(self):
        self.course = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')
        self.student = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        Enrollment.objects.create(user=self.student, course=self.course)
        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )

    def test_student_can_send_and_read_group_chat_message(self):
        self.client.force_authenticate(user=self.student)

        threads_response = self.client.get('/api/chats/')
        self.assertEqual(threads_response.status_code, status.HTTP_200_OK)
        group_thread = next(t for t in threads_response.data if t['kind'] == 'group')

        send = self.client.post(
            f"/api/chats/{group_thread['id']}/messages/", {'text': 'Привет всем!'}, format='json',
        )
        self.assertEqual(send.status_code, status.HTTP_201_CREATED)

        messages = self.client.get(f"/api/chats/{group_thread['id']}/messages/")
        self.assertEqual(messages.status_code, status.HTTP_200_OK)
        self.assertTrue(any(m['text'] == 'Привет всем!' for m in messages.data))

    def test_student_cannot_access_group_chat_of_unenrolled_course(self):
        other_course = Course.objects.create(title='Другой курс', slug='drugoi-kurs')
        thread = ChatThread.objects.create(kind=ChatThread.Kind.GROUP, course=other_course)

        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/chats/{thread.id}/messages/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_message_student_direct_thread(self):
        self.client.force_authenticate(user=self.student)
        self.client.get('/api/chats/')  # создаёт личный тред ученика

        self.client.force_authenticate(user=self.admin)
        threads_response = self.client.get('/api/chats/')
        direct_thread = next(t for t in threads_response.data if t['kind'] == 'direct')

        send = self.client.post(
            f"/api/chats/{direct_thread['id']}/messages/", {'text': 'Добро пожаловать!'}, format='json',
        )
        self.assertEqual(send.status_code, status.HTTP_201_CREATED)

    def test_student_can_send_voice_message_without_text(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.student)
        threads_response = self.client.get('/api/chats/')
        group_thread = next(t for t in threads_response.data if t['kind'] == 'group')

        audio = SimpleUploadedFile('voice.webm', b'fake audio bytes', content_type='audio/webm')
        send = self.client.post(
            f"/api/chats/{group_thread['id']}/messages/", {'audio_file': audio}, format='multipart',
        )
        self.assertEqual(send.status_code, status.HTTP_201_CREATED, send.data)
        self.assertEqual(send.data['text'], '')
        self.assertTrue(send.data['audio_file'])

        messages = self.client.get(f"/api/chats/{group_thread['id']}/messages/")
        self.assertTrue(any(m['audio_file'] for m in messages.data))

    def test_message_without_text_or_audio_is_rejected(self):
        self.client.force_authenticate(user=self.student)
        threads_response = self.client.get('/api/chats/')
        group_thread = next(t for t in threads_response.data if t['kind'] == 'group')

        response = self.client.post(f"/api/chats/{group_thread['id']}/messages/", {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DeleteModuleTests(APITestCase):
    """Модуль тренинга можно удалить вместе с его уроками и тестом."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')
        self.module = Module.objects.create(course=self.course, title='Модуль 1', order=1)
        self.lesson = Lesson.objects.create(module=self.module, title='Урок 1', order=1)
        self.test_obj = Test.objects.create(module=self.module, title='Тест модуля 1')

    def test_admin_can_delete_module_with_lessons_and_test(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/admin/modules/{self.module.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Module.objects.filter(id=self.module.id).exists())
        self.assertFalse(Lesson.objects.filter(id=self.lesson.id).exists())
        self.assertFalse(Test.objects.filter(id=self.test_obj.id).exists())

    def test_non_admin_cannot_delete_module(self):
        student = User.objects.create_user(
            username='s3@example.com', email='s3@example.com', password='pass12345', role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=student)
        response = self.client.delete(f'/api/admin/modules/{self.module.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Module.objects.filter(id=self.module.id).exists())


class StudentEnrollTests(APITestCase):
    """Админ может выдавать ученику доступ сразу к нескольким тренингам без
    ограничений — выдача нового курса не отзывает уже имеющийся доступ."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )
        self.course_a = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')
        self.course_b = Course.objects.create(title='Продвинутый визаж', slug='prodvinutyi-vizazh')
        self.student = User.objects.create_user(
            username='anna@example.com', email='anna@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        Enrollment.objects.create(user=self.student, course=self.course_a)
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_enroll_student_in_additional_course(self):
        response = self.client.post(
            f'/api/admin/students/{self.student.id}/enroll/', {'course_id': self.course_b.id}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(response.data['course_ids'], [self.course_a.id, self.course_b.id])
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.course_a).exists())
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.course_b).exists())

    def test_enrolling_twice_does_not_duplicate(self):
        self.client.post(f'/api/admin/students/{self.student.id}/enroll/', {'course_id': self.course_a.id}, format='json')
        self.assertEqual(Enrollment.objects.filter(user=self.student, course=self.course_a).count(), 1)

    def test_admin_can_unenroll_student_from_a_course(self):
        response = self.client.delete(
            f'/api/admin/students/{self.student.id}/enroll/', {'course_id': self.course_a.id}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.course_a.id, response.data['course_ids'])
        self.assertFalse(Enrollment.objects.filter(user=self.student, course=self.course_a).exists())

    def test_non_admin_cannot_enroll_student(self):
        other = User.objects.create_user(
            username='other@example.com', email='other@example.com', password='pass12345', role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=other)
        response = self.client.post(
            f'/api/admin/students/{self.student.id}/enroll/', {'course_id': self.course_b.id}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
