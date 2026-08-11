from rest_framework import serializers

from .models import ChatThread, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()
    audio_file = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'text', 'audio_file', 'file', 'file_name',
            'sender_name', 'is_mine', 'is_favorite', 'deleted_for_everyone', 'created_at',
        ]

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.email

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return bool(request and obj.sender_id == request.user.id)

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        return bool(request and obj.favorited_by.filter(pk=request.user.id).exists())

    def get_text(self, obj):
        return '' if obj.deleted_for_everyone else obj.text

    def _absolute(self, file_field):
        if not file_field:
            return None
        request = self.context.get('request')
        url = file_field.url
        return request.build_absolute_uri(url) if request else url

    def get_audio_file(self, obj):
        if obj.deleted_for_everyone:
            return None
        return self._absolute(obj.audio_file)

    def get_file(self, obj):
        if obj.deleted_for_everyone:
            return None
        return self._absolute(obj.file)


class ChatThreadSerializer(serializers.ModelSerializer):
    title = serializers.ReadOnlyField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = ['id', 'kind', 'course', 'title', 'last_message']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if not msg:
            return None
        return {
            'text': msg.text or ('Голосовое сообщение' if msg.audio_file else ''),
            'sender_name': msg.sender.get_full_name() or msg.sender.email,
            'created_at': msg.created_at,
        }
