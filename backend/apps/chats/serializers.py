from rest_framework import serializers

from .models import ChatThread, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()
    audio_file = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()
    deleted_at = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'text', 'audio_file', 'file', 'file_name',
            'sender_name', 'is_mine', 'is_favorite', 'deleted_for_everyone', 'deleted_at', 'created_at',
        ]

    def _is_admin(self):
        request = self.context.get('request')
        return bool(request and request.user.role == 'admin')

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.email

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return bool(request and obj.sender_id == request.user.id)

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        return bool(request and obj.favorited_by.filter(pk=request.user.id).exists())

    # «Удалённое у всех» сообщение по-прежнему хранит содержимое в базе (см.
    # ChatMessageActionView) — обычным участникам чата оно всё равно
    # показывается пустым/удалённым, а администратору отдаётся как есть,
    # чтобы модерация могла видеть, что именно было удалено. Ученики об
    # этой особенности не знают — для них поведение не отличается от
    # обычного «сообщение удалено».
    def get_text(self, obj):
        if obj.deleted_for_everyone and not self._is_admin():
            return ''
        return obj.text

    def _absolute(self, file_field):
        if not file_field:
            return None
        request = self.context.get('request')
        url = file_field.url
        return request.build_absolute_uri(url) if request else url

    def get_audio_file(self, obj):
        if obj.deleted_for_everyone and not self._is_admin():
            return None
        return self._absolute(obj.audio_file)

    def get_file(self, obj):
        if obj.deleted_for_everyone and not self._is_admin():
            return None
        return self._absolute(obj.file)

    # Метка времени удаления видна только администратору (используется в
    # модерации, чтобы показать «Удалено · <дата/время>» рядом с исходным
    # содержимым удалённого сообщения).
    def get_deleted_at(self, obj):
        if obj.deleted_for_everyone and self._is_admin():
            return obj.deleted_at
        return None


class ChatThreadSerializer(serializers.ModelSerializer):
    title = serializers.ReadOnlyField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        # student — нужен только админу, чтобы из карточки ученика открыть
        # именно его личный чат (у ученика поле всегда совпадает с ним самим).
        fields = ['id', 'kind', 'course', 'student', 'title', 'last_message']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if not msg:
            return None
        return {
            'text': msg.text or ('Голосовое сообщение' if msg.audio_file else ''),
            'sender_name': msg.sender.get_full_name() or msg.sender.email,
            'created_at': msg.created_at,
        }
