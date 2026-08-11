from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import notify_many

from .models import ChatThread, ChatMessage
from .serializers import ChatThreadSerializer, ChatMessageSerializer
from .services import threads_for_user, can_access_thread


class ChatThreadListView(APIView):
    """Список чатов, доступных текущему пользователю."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        threads = threads_for_user(request.user)
        return Response(ChatThreadSerializer(threads, many=True, context={'request': request}).data)


class ChatMessageListView(APIView):
    """Сообщения одного чата: список и отправка. Сообщения реально
    сохраняются в базе (не пропадают при обновлении страницы)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        thread = get_object_or_404(ChatThread, pk=pk)
        if not can_access_thread(request.user, thread):
            return Response({'detail': 'Нет доступа к этому чату'}, status=status.HTTP_403_FORBIDDEN)
        messages = thread.messages.select_related('sender').exclude(deleted_for=request.user)
        return Response(ChatMessageSerializer(messages, many=True, context={'request': request}).data)

    def post(self, request, pk):
        thread = get_object_or_404(ChatThread, pk=pk)
        if not can_access_thread(request.user, thread):
            return Response({'detail': 'Нет доступа к этому чату'}, status=status.HTTP_403_FORBIDDEN)

        text = (request.data.get('text') or '').strip()
        audio_file = request.FILES.get('audio_file')
        attached_file = request.FILES.get('file')
        if not text and not audio_file and not attached_file:
            return Response({'text': ['Сообщение не может быть пустым']}, status=status.HTTP_400_BAD_REQUEST)

        message = ChatMessage.objects.create(
            thread=thread, sender=request.user, text=text, audio_file=audio_file,
            file=attached_file, file_name=attached_file.name if attached_file else '',
        )
        self._notify_others(request, thread)

        return Response(
            ChatMessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def _notify_others(self, request, thread):
        User = request.user.__class__
        if thread.kind == ChatThread.Kind.GROUP:
            recipients = User.objects.filter(
                Q(role='admin') | Q(enrollments__course=thread.course)
            ).exclude(pk=request.user.pk).distinct()
        elif request.user.role == 'admin':
            recipients = User.objects.filter(pk=thread.student_id) if thread.student_id else User.objects.none()
        else:
            recipients = User.objects.filter(role='admin')
        notify_many(list(recipients), f'Новое сообщение в «{thread.title}»', url='/chats')


class ChatMessageActionView(APIView):
    """Удаление сообщения — у себя (скрыть только для меня) или у всех
    (полное «удаление» видно всем участникам, содержимое стирается)."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        message = get_object_or_404(ChatMessage, pk=pk)
        if not can_access_thread(request.user, message.thread):
            return Response({'detail': 'Нет доступа к этому чату'}, status=status.HTTP_403_FORBIDDEN)

        scope = request.query_params.get('for', 'me')
        if scope == 'everyone':
            if message.sender_id != request.user.id and request.user.role != 'admin':
                return Response(
                    {'detail': 'Удалить у всех может только автор сообщения'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            message.deleted_for_everyone = True
            message.text = ''
            message.audio_file = None
            message.file = None
            message.file_name = ''
            message.save(update_fields=['deleted_for_everyone', 'text', 'audio_file', 'file', 'file_name'])
        else:
            message.deleted_for.add(request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatMessageFavoriteView(APIView):
    """Добавить/убрать сообщение из избранного (у каждого пользователя своё)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        message = get_object_or_404(ChatMessage, pk=pk)
        if not can_access_thread(request.user, message.thread):
            return Response({'detail': 'Нет доступа к этому чату'}, status=status.HTTP_403_FORBIDDEN)
        message.favorited_by.add(request.user)
        return Response(ChatMessageSerializer(message, context={'request': request}).data)

    def delete(self, request, pk):
        message = get_object_or_404(ChatMessage, pk=pk)
        if not can_access_thread(request.user, message.thread):
            return Response({'detail': 'Нет доступа к этому чату'}, status=status.HTTP_403_FORBIDDEN)
        message.favorited_by.remove(request.user)
        return Response(ChatMessageSerializer(message, context={'request': request}).data)
