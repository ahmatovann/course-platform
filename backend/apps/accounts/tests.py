from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class LoginTests(APITestCase):
    def setUp(self):
        self.url = '/api/auth/login/'
        self.password = 'strongpass123'
        self.user = User.objects.create_user(
            username='student@example.com', email='student@example.com',
            password=self.password, first_name='Анна', role=User.Role.STUDENT,
        )

    def test_login_with_correct_credentials_returns_tokens(self):
        response = self.client.post(self.url, {'email': self.user.email, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], self.user.email)
        self.assertEqual(response.data['user']['role'], User.Role.STUDENT)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(self.url, {'email': self.user.email, 'password': 'wrong-password'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_unknown_email_fails(self):
        response = self.client.post(self.url, {'email': 'ghost@example.com', 'password': 'whatever123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RegistrationRemovedTests(APITestCase):
    """Самостоятельная регистрация отключена — доступ выдаёт только администратор."""

    def test_register_endpoint_does_not_exist(self):
        response = self.client.post('/api/auth/register/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
