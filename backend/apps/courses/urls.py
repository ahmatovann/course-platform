from django.urls import path

from .views import (
    CourseListView, CourseDetailView, ModuleDetailView, LessonDetailView,
    MarkLessonWatchedView, TestDetailView, TestSubmitView, EnrollView,
    CertificateDownloadView, LessonCommentsView,
    MaterialFavoriteView, FavoriteMaterialsListView,
)

urlpatterns = [
    path('', CourseListView.as_view(), name='course-list'),
    path('modules/<int:pk>/', ModuleDetailView.as_view(), name='module-detail'),
    path('lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('lessons/<int:pk>/watch/', MarkLessonWatchedView.as_view(), name='lesson-watch'),
    path('lessons/<int:pk>/comments/', LessonCommentsView.as_view(), name='lesson-comments'),
    path('materials/favorites/', FavoriteMaterialsListView.as_view(), name='materials-favorites'),
    path('materials/<int:pk>/favorite/', MaterialFavoriteView.as_view(), name='material-favorite'),
    path('tests/<int:pk>/', TestDetailView.as_view(), name='test-detail'),
    path('tests/<int:pk>/submit/', TestSubmitView.as_view(), name='test-submit'),
    path('<int:pk>/enroll/', EnrollView.as_view(), name='course-enroll'),
    path('<slug:slug>/certificate/', CertificateDownloadView.as_view(), name='course-certificate'),
    path('<slug:slug>/', CourseDetailView.as_view(), name='course-detail'),
]
