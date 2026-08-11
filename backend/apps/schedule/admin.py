from django.contrib import admin

from .models import ScheduleEvent


@admin.register(ScheduleEvent)
class ScheduleEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'starts_at', 'course', 'created_by')
    list_filter = ('course',)
    search_fields = ('title', 'description')
