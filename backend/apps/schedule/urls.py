from django.urls import path

from .views import (
    ScheduleListView, ScheduleCreateView, ScheduleUpdateDeleteView,
    NewsFavoriteView, FavoriteNewsListView,
)

urlpatterns = [
    path('', ScheduleListView.as_view(), name='schedule-list'),
    path('create/', ScheduleCreateView.as_view(), name='schedule-create'),
    path('favorites/', FavoriteNewsListView.as_view(), name='news-favorites'),
    path('<int:pk>/favorite/', NewsFavoriteView.as_view(), name='news-favorite'),
    path('<int:pk>/', ScheduleUpdateDeleteView.as_view(), name='schedule-update-delete'),
]
