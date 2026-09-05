from django.urls import path

from .views import (
    StudentListView, CreateStudentView, ToggleStudentStatusView, DeleteStudentView, StudentActivityView, StudentEnrollView,
    StudentExtendAccessView,
    AdminCourseListView, AdminCourseDeleteView, AdminModuleUpdateView,
    AdminLessonCreateView, AdminLessonUpdateDeleteView, AdminLessonVideoDeleteView,
    AdminTestListView, AdminTestDetailView, AdminTestCreateView, AdminTestUpdateDeleteView,
    StudentProgressView, ModuleCompletionStatsView,
    AdminMaterialCreateView, AdminMaterialDeleteView, AdminMaterialAttachView, AdminMaterialLibraryCreateView,
    AdminCourseCreateView, AdminModuleCreateView,
    StudentProgressExportView, StudentProgressPdfExportView, StudentsExportView, StudentsPdfExportView,
    AdminMediaListView,
)

urlpatterns = [
    path('students/', StudentListView.as_view(), name='admin-students'),
    path('students/create/', CreateStudentView.as_view(), name='admin-students-create'),
    path('students/export/', StudentsExportView.as_view(), name='admin-students-export'),
    path('students/export-pdf/', StudentsPdfExportView.as_view(), name='admin-students-export-pdf'),
    path('students/<int:pk>/toggle/', ToggleStudentStatusView.as_view(), name='admin-students-toggle'),
    path('students/<int:pk>/delete/', DeleteStudentView.as_view(), name='admin-students-delete'),
    path('students/<int:pk>/activity/', StudentActivityView.as_view(), name='admin-students-activity'),
    path('students/<int:pk>/enroll/', StudentEnrollView.as_view(), name='admin-students-enroll'),
    path('students/<int:pk>/extend/', StudentExtendAccessView.as_view(), name='admin-students-extend'),
    path('students/<int:pk>/progress/', StudentProgressView.as_view(), name='admin-students-progress'),
    path('students/<int:pk>/progress/export/', StudentProgressExportView.as_view(), name='admin-students-progress-export'),
    path('students/<int:pk>/progress/export-pdf/', StudentProgressPdfExportView.as_view(), name='admin-students-progress-export-pdf'),
    path('analytics/modules/', ModuleCompletionStatsView.as_view(), name='admin-analytics-modules'),

    path('courses/', AdminCourseListView.as_view(), name='admin-courses'),
    path('courses/create/', AdminCourseCreateView.as_view(), name='admin-course-create'),
    path('courses/<int:pk>/', AdminCourseDeleteView.as_view(), name='admin-course-delete'),
    path('courses/<int:course_id>/modules/', AdminModuleCreateView.as_view(), name='admin-module-create'),
    path('modules/<int:pk>/', AdminModuleUpdateView.as_view(), name='admin-module-update'),
    path('modules/<int:module_id>/lessons/', AdminLessonCreateView.as_view(), name='admin-lesson-create'),
    path('lessons/<int:pk>/', AdminLessonUpdateDeleteView.as_view(), name='admin-lesson-update-delete'),
    path('lessons/<int:pk>/video/', AdminLessonVideoDeleteView.as_view(), name='admin-lesson-video-delete'),
    path('lessons/<int:lesson_id>/materials/', AdminMaterialCreateView.as_view(), name='admin-material-create'),
    path('lessons/<int:lesson_id>/materials/attach/', AdminMaterialAttachView.as_view(), name='admin-material-attach'),
    path('materials/upload/', AdminMaterialLibraryCreateView.as_view(), name='admin-material-library-upload'),
    path('materials/<int:pk>/', AdminMaterialDeleteView.as_view(), name='admin-material-delete'),
    path('media/', AdminMediaListView.as_view(), name='admin-media'),

    path('tests/', AdminTestListView.as_view(), name='admin-tests'),
    path('tests/create/', AdminTestCreateView.as_view(), name='admin-tests-create'),
    path('tests/<int:pk>/', AdminTestDetailView.as_view(), name='admin-tests-detail'),
    path('tests/<int:pk>/update/', AdminTestUpdateDeleteView.as_view(), name='admin-tests-update-delete'),
]
