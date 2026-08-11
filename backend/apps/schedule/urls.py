from django.urls import path

from .views import ScheduleListView, ScheduleCreateView, ScheduleUpdateDeleteView

urlpatterns = [
    path('', ScheduleListView.as_view(), name='schedule-list'),
    path('create/', ScheduleCreateView.as_view(), name='schedule-create'),
    path('<int:pk>/', ScheduleUpdateDeleteView.as_view(), name='schedule-update-delete'),
]
