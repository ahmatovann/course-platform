from django.urls import path

from .views import (
    StudentListView, CreateStudentView, ToggleStudentStatusView, StudentEnrollView,
    AdminCourseListView, AdminModuleUpdateView,
    AdminLessonCreateView, AdminLessonUpdateDeleteView, AdminVideoListView,
    AdminTestListView, AdminTestDetailView, AdminTestCreateView, AdminTestUpdateDeleteView,
    StudentProgressView, ModuleCompletionStatsView,
    AdminMaterialCreateView, AdminMaterialDeleteView,
    AdminCourseCreateView, AdminModuleCreateView,
    StudentProgressExportView, StudentsExportView,
)

urlpatterns = [
    path('students/', StudentListView.as_view(), name='admin-students'),
    path('students/create/', CreateStudentView.as_view(), name='admin-students-create'),
    path('students/export/', StudentsExportView.as_view(), name='admin-students-export'),
    path('students/<int:pk>/toggle/', ToggleStudentStatusView.as_view(), name='admin-students-toggle'),
    path('students/<int:pk>/enroll/', StudentEnrollView.as_view(), name='admin-students-enroll'),
    path('students/<int:pk>/progress/', StudentProgressView.as_view(), name='admin-students-progress'),
    path('students/<int:pk>/progress/export/', StudentProgressExportView.as_view(), name='admin-students-progress-export'),
    path('analytics/modules/', ModuleCompletionStatsView.as_view(), name='admin-analytics-modules'),

    path('courses/', AdminCourseListView.as_view(), name='admin-courses'),
    path('courses/create/', AdminCourseCreateView.as_view(), name='admin-course-create'),
    path('courses/<int:course_id>/modules/', AdminModuleCreateView.as_view(), name='admin-module-create'),
    path('modules/<int:pk>/', AdminModuleUpdateView.as_view(), name='admin-module-update'),
    path('modules/<int:module_id>/lessons/', AdminLessonCreateView.as_view(), name='admin-lesson-create'),
    path('lessons/<int:pk>/', AdminLessonUpdateDeleteView.as_view(), name='admin-lesson-update-delete'),
    path('videos/', AdminVideoListView.as_view(), name='admin-videos'),
    path('lessons/<int:lesson_id>/materials/', AdminMaterialCreateView.as_view(), name='admin-material-create'),
    path('materials/<int:pk>/', AdminMaterialDeleteView.as_view(), name='admin-material-delete'),

    path('tests/', AdminTestListView.as_view(), name='admin-tests'),
    path('tests/create/', AdminTestCreateView.as_view(), name='admin-tests-create'),
    path('tests/<int:pk>/', AdminTestDetailView.as_view(), name='admin-tests-detail'),
    path('tests/<int:pk>/update/', AdminTestUpdateDeleteView.as_view(), name='admin-tests-update-delete'),
]
