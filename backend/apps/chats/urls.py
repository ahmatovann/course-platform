from django.urls import path

from .views import (
    ChatThreadListView, ChatMessageListView, ChatMessageActionView, ChatMessageFavoriteView,
    AdminDirectThreadView,
)

urlpatterns = [
    path('', ChatThreadListView.as_view(), name='chat-threads'),
    path('direct/<int:student_id>/', AdminDirectThreadView.as_view(), name='chat-direct'),
    path('<int:pk>/messages/', ChatMessageListView.as_view(), name='chat-messages'),
    path('messages/<int:pk>/', ChatMessageActionView.as_view(), name='chat-message-action'),
    path('messages/<int:pk>/favorite/', ChatMessageFavoriteView.as_view(), name='chat-message-favorite'),
]
