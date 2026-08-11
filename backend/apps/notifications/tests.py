from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Notification

User = get_user_model()


class NotificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        self.other = User.objects.create_user(
            username='other@example.com', email='other@example.com',
            password='pass12345', role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=self.user)

    def test_list_returns_only_own_notifications(self):
        Notification.objects.create(user=self.user, text='для меня')
        Notification.objects.create(user=self.other, text='не для меня')
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        texts = [n['text'] for n in response.data]
        self.assertEqual(texts, ['для меня'])

    def test_mark_single_read(self):
        n = Notification.objects.create(user=self.user, text='n1')
        response = self.client.post(f'/api/notifications/{n.id}/read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_mark_all_read(self):
        Notification.objects.create(user=self.user, text='n1')
        Notification.objects.create(user=self.user, text='n2')
        Notification.objects.create(user=self.other, text='n3')

        response = self.client.post('/api/notifications/read-all/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)
        # Уведомления другого пользователя не затронуты.
        self.assertEqual(Notification.objects.filter(user=self.other, is_read=False).count(), 1)

    def test_cannot_mark_other_users_notification_read(self):
        n = Notification.objects.create(user=self.other, text='чужое')
        response = self.client.post(f'/api/notifications/{n.id}/read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        n.refresh_from_db()
        self.assertFalse(n.is_read)
