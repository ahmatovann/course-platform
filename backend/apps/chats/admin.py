from django.contrib import admin

from .models import ChatThread, ChatMessage


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'course', 'student', 'created_at')
    list_filter = ('kind',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('thread', 'sender', 'text', 'created_at')
    search_fields = ('text',)
