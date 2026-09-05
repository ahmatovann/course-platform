from django.contrib import admin

from .models import (
    Course, Module, Lesson, Material, LessonProgress, Test, Question,
    AnswerOption, TestAttempt, Enrollment,
)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 2


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'order')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'require_test_to_unlock_next', 'pass_threshold_percent')
    list_filter = ('course',)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order', 'duration_seconds')
    list_filter = ('module__course', 'module')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'lesson')
    list_filter = ('lesson__module__course',)


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'module')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'test')
    inlines = [AnswerOptionInline]


admin.site.register(LessonProgress)
admin.site.register(TestAttempt)
admin.site.register(Enrollment)
