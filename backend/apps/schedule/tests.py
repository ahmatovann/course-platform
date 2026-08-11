from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.courses.models import Course, Enrollment

from .models import ScheduleEvent

User = get_user_model()


class NewsTests(APITestCase):
    """Раздел «Новости» (бывшее «Расписание»): список, доступ по курсу,
    создание администратором с описанием."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin@example.com', email='admin@example.com',
            password='adminpass123', role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(title='Основы визажа', slug='osnovy-vizazha')
        self.other_course = Course.objects.create(title='Другой курс', slug='drugoi-kurs')
        self.student = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        Enrollment.objects.create(user=self.student, course=self.course)

    def test_student_sees_general_and_own_course_news_only(self):
        ScheduleEvent.objects.create(title='Общая новость', starts_at='2026-09-01T10:00:00Z')
        ScheduleEvent.objects.create(title='Новость моего курса', starts_at='2026-09-02T10:00:00Z', course=self.course)
        ScheduleEvent.objects.create(title='Новость чужого курса', starts_at='2026-09-03T10:00:00Z', course=self.other_course)

        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/news/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {n['title'] for n in response.data}
        self.assertEqual(titles, {'Общая новость', 'Новость моего курса'})

    def test_admin_can_create_news_with_description(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            'title': 'Открытие нового модуля',
            'description': 'Подробное описание новости на несколько предложений.',
            'starts_at': '2026-09-10T12:00:00Z',
            'course': self.course.id,
        }
        response = self.client.post('/api/news/create/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['description'], payload['description'])

        event = ScheduleEvent.objects.get(title='Открытие нового модуля')
        self.assertEqual(event.description, payload['description'])

    def test_admin_can_add_link_url_to_news(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            'title': 'Вебинар по колористике',
            'description': 'Запись доступна по ссылке ниже.',
            'link_url': 'https://example.com/webinar',
            'starts_at': '2026-09-11T12:00:00Z',
        }
        response = self.client.post('/api/news/create/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['link_url'], payload['link_url'])

        list_response = self.client.get('/api/news/')
        item = next(n for n in list_response.data if n['title'] == payload['title'])
        self.assertEqual(item['link_url'], payload['link_url'])

    def test_link_url_without_scheme_gets_https_prepended(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/news/create/',
            {'title': 'Без схемы', 'link_url': 'example.com/webinar', 'starts_at': '2026-09-13T12:00:00Z'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['link_url'], 'https://example.com/webinar')

    def test_news_link_url_is_optional(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/news/create/', {'title': 'Без ссылки', 'starts_at': '2026-09-12T12:00:00Z'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['link_url'], '')

    def test_admin_can_search_and_filter_news(self):
        ScheduleEvent.objects.create(title='Общая новость', starts_at='2026-09-01T10:00:00Z')
        ScheduleEvent.objects.create(title='Открытие курса визажа', starts_at='2026-09-02T10:00:00Z', course=self.course)
        ScheduleEvent.objects.create(title='Новость чужого курса', starts_at='2026-09-03T10:00:00Z', course=self.other_course)

        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/news/', {'search': 'визажа'})
        self.assertEqual({n['title'] for n in response.data}, {'Открытие курса визажа'})

        response = self.client.get('/api/news/', {'course': 'none'})
        self.assertEqual({n['title'] for n in response.data}, {'Общая новость'})

        response = self.client.get('/api/news/', {'course': self.course.id})
        self.assertEqual({n['title'] for n in response.data}, {'Открытие курса визажа'})

    def test_student_cannot_create_news(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/news/create/', {'title': 'X', 'starts_at': '2026-09-10T12:00:00Z'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
