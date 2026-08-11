from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification

from .models import (
    AnswerOption, Comment, Course, Enrollment, Lesson, Module, Question, Test,
)

User = get_user_model()


class ModuleUnlockTests(APITestCase):
    """Модуль 2 должен оставаться заблокированным, пока модуль 1 не пройден
    (все уроки просмотрены и тест сдан выше порога)."""

    def setUp(self):
        self.course = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')

        self.module1 = Module.objects.create(
            course=self.course, title='Модуль 1', order=1,
            require_test_to_unlock_next=True, pass_threshold_percent=80,
        )
        self.lesson1 = Lesson.objects.create(module=self.module1, title='Урок 1', order=1)
        self.test1 = Test.objects.create(module=self.module1, title='Тест модуля 1')
        self.question1 = Question.objects.create(test=self.test1, text='Вопрос 1', order=1)
        self.correct_option = AnswerOption.objects.create(
            question=self.question1, text='Правильный', is_correct=True, order=1,
        )
        self.wrong_option = AnswerOption.objects.create(
            question=self.question1, text='Неправильный', is_correct=False, order=2,
        )

        self.module2 = Module.objects.create(course=self.course, title='Модуль 2', order=2)
        self.lesson2 = Lesson.objects.create(module=self.module2, title='Урок 2', order=1)

        self.student = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        Enrollment.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)

    def _get_module2_unlocked(self):
        response = self.client.get(f'/api/courses/{self.course.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        module2_data = next(m for m in response.data['modules'] if m['id'] == self.module2.id)
        return module2_data['unlocked']

    def test_module2_locked_before_module1_completed(self):
        self.assertFalse(self._get_module2_unlocked())

    def test_module2_still_locked_if_only_lesson_watched_without_passing_test(self):
        self.client.post(f'/api/courses/lessons/{self.lesson1.id}/watch/')
        self.assertFalse(self._get_module2_unlocked())

    def test_module2_unlocks_after_lesson_watched_and_test_passed(self):
        self.client.post(f'/api/courses/lessons/{self.lesson1.id}/watch/')
        submit = self.client.post(
            f'/api/courses/tests/{self.test1.id}/submit/',
            {'answers': {str(self.question1.id): self.correct_option.id}},
            format='json',
        )
        self.assertEqual(submit.status_code, status.HTTP_201_CREATED)
        self.assertTrue(submit.data['passed'])
        self.assertEqual(submit.data['score_percent'], 100)
        self.assertTrue(self._get_module2_unlocked())

    def test_module2_stays_locked_if_test_failed(self):
        self.client.post(f'/api/courses/lessons/{self.lesson1.id}/watch/')
        submit = self.client.post(
            f'/api/courses/tests/{self.test1.id}/submit/',
            {'answers': {str(self.question1.id): self.wrong_option.id}},
            format='json',
        )
        self.assertEqual(submit.status_code, status.HTTP_201_CREATED)
        self.assertFalse(submit.data['passed'])
        self.assertEqual(submit.data['score_percent'], 0)
        self.assertFalse(self._get_module2_unlocked())


class CertificateDownloadTests(APITestCase):
    def setUp(self):
        self.course = Course.objects.create(
            title='Основы визажа', slug='osnovy-vizazha', certificate_on_completion=True,
        )
        self.module = Module.objects.create(
            course=self.course, title='Модуль 1', order=1, require_test_to_unlock_next=False,
        )
        self.lesson = Lesson.objects.create(module=self.module, title='Урок 1', order=1)

        self.student = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        self.other_student = User.objects.create_user(
            username='other@example.com', email='other@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        Enrollment.objects.create(user=self.student, course=self.course)

    def test_certificate_forbidden_when_not_enrolled(self):
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(f'/api/courses/{self.course.slug}/certificate/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_certificate_returns_400_when_course_not_finished(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/courses/{self.course.slug}/certificate/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_certificate_downloads_pdf_when_course_completed(self):
        self.client.force_authenticate(user=self.student)
        self.client.post(f'/api/courses/lessons/{self.lesson.id}/watch/')

        response = self.client.get(f'/api/courses/{self.course.slug}/certificate/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])


class CourseVisibilityTests(APITestCase):
    """Ученик должен видеть и открывать только те тренинги, на которые
    его записал администратор — остальные не должны быть видны вообще,
    даже если ученик знает их id/slug напрямую."""

    def setUp(self):
        self.course_a = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')
        self.course_b = Course.objects.create(title='Продвинутый визаж', slug='prodvinutyi-vizazh')

        self.module_b = Module.objects.create(course=self.course_b, title='Модуль 1', order=1)
        self.lesson_b = Lesson.objects.create(module=self.module_b, title='Урок 1', order=1)
        self.test_b = Test.objects.create(module=self.module_b, title='Тест модуля 1')

        self.student = User.objects.create_user(
            username='anna@example.com', email='anna@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        # Записана только на курс A.
        Enrollment.objects.create(user=self.student, course=self.course_a)
        self.client.force_authenticate(user=self.student)

    def test_course_list_only_shows_enrolled_courses(self):
        response = self.client.get('/api/courses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [c['slug'] for c in response.data]
        self.assertIn(self.course_a.slug, slugs)
        self.assertNotIn(self.course_b.slug, slugs)

    def test_course_detail_of_unenrolled_course_is_not_found(self):
        response = self.client.get(f'/api/courses/{self.course_b.slug}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_module_of_unenrolled_course_is_not_found(self):
        response = self.client.get(f'/api/courses/modules/{self.module_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lesson_of_unenrolled_course_is_not_found(self):
        response = self.client.get(f'/api/courses/lessons/{self.lesson_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_mark_lesson_watched_without_enrollment(self):
        response = self.client.post(f'/api/courses/lessons/{self.lesson_b.id}/watch/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_test_of_unenrolled_course_is_not_found(self):
        response = self.client.get(f'/api/courses/tests/{self.test_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_submit_test_without_enrollment(self):
        response = self.client.post(f'/api/courses/tests/{self.test_b.id}/submit/', {'answers': {}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sees_all_courses_regardless_of_enrollment(self):
        admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/courses/')
        slugs = [c['slug'] for c in response.data]
        self.assertIn(self.course_a.slug, slugs)
        self.assertIn(self.course_b.slug, slugs)

    def test_enrolling_in_second_course_grants_access_without_losing_first(self):
        Enrollment.objects.create(user=self.student, course=self.course_b)
        response = self.client.get('/api/courses/')
        slugs = [c['slug'] for c in response.data]
        self.assertIn(self.course_a.slug, slugs)
        self.assertIn(self.course_b.slug, slugs)


class LessonCommentTests(APITestCase):
    """Комментарии под видео урока: ученик пишет, администратору приходит
    уведомление с указанием курса/модуля/урока и автора."""

    def setUp(self):
        self.course = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')
        self.module = Module.objects.create(course=self.course, title='Модуль 1', order=1)
        self.lesson = Lesson.objects.create(
            module=self.module, title='Введение в инструменты', order=1,
            description='Короткое описание урока',
        )
        self.student = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password='pass12345', first_name='Анна', role=User.Role.STUDENT,
        )
        Enrollment.objects.create(user=self.student, course=self.course)
        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )

    def test_enrolled_student_can_post_comment(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            f'/api/courses/lessons/{self.lesson.id}/comments/', {'text': 'Отличный урок!'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Comment.objects.filter(lesson=self.lesson, user=self.student).exists())

    def test_comment_notifies_admins_with_course_module_lesson(self):
        self.client.force_authenticate(user=self.student)
        self.client.post(f'/api/courses/lessons/{self.lesson.id}/comments/', {'text': 'Вопрос по уроку'}, format='json')

        notif = Notification.objects.filter(user=self.admin).first()
        self.assertIsNotNone(notif)
        self.assertIn('Анна', notif.text)
        self.assertIn(self.lesson.title, notif.text)
        self.assertIn(self.module.title, notif.text)
        self.assertIn(self.course.title, notif.text)

    def test_not_enrolled_student_cannot_comment(self):
        outsider = User.objects.create_user(
            username='outsider@example.com', email='outsider@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.post(
            f'/api/courses/lessons/{self.lesson.id}/comments/', {'text': 'Попытка'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_empty_comment_rejected(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(f'/api/courses/lessons/{self.lesson.id}/comments/', {'text': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lesson_detail_includes_description(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/courses/lessons/{self.lesson.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Короткое описание урока')


class AutoWatchTests(APITestCase):
    """Урок отмечается просмотренным автоматически (без отдельной кнопки) —
    фронтенд вызывает тот же эндпоинт по событию видео."""

    def setUp(self):
        self.course = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')
        self.module = Module.objects.create(course=self.course, title='Модуль 1', order=1)
        self.lesson = Lesson.objects.create(module=self.module, title='Урок 1', order=1)
        self.student = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        Enrollment.objects.create(user=self.student, course=self.course)

    def test_watch_endpoint_is_idempotent(self):
        self.client.force_authenticate(user=self.student)
        for _ in range(3):
            response = self.client.post(f'/api/courses/lessons/{self.lesson.id}/watch/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        lesson_response = self.client.get(f'/api/courses/lessons/{self.lesson.id}/')
        self.assertTrue(lesson_response.data['watched'])
