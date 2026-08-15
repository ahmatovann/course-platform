from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import (
    UserSerializer, ProfileUpdateSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
)
from .utils import send_password_reset_email

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['name'] = user.get_full_name() or user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user, context=self.context).data
        return data


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer
    # Ограничиваем частоту попыток входа с одного IP — защита от подбора пароля.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.must_change_password = False
        request.user.save(update_fields=['password', 'must_change_password'])
        return Response({'detail': 'Пароль изменён'})


class PasswordResetRequestView(APIView):
    """Запрос на сброс пароля. Ответ одинаковый независимо от того, найден
    ли email в базе — чтобы нельзя было проверять, кто зарегистрирован."""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data['email']).first()
        if user:
            send_password_reset_email(user)
        return Response({'detail': 'Если такой email зарегистрирован, на него отправлена ссылка для сброса пароля'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])
        return Response({'detail': 'Пароль изменён. Теперь можно войти с новым паролем.'})
