from rest_framework import serializers

from .models import ScheduleEvent


class ScheduleEventSerializer(serializers.ModelSerializer):
    course_title = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleEvent
        fields = ['id', 'title', 'description', 'link_url', 'starts_at', 'course', 'course_title']

    def get_course_title(self, obj):
        return obj.course.title if obj.course_id else None


class ScheduleEventWriteSerializer(serializers.ModelSerializer):
    # Ссылку принимаем и без явной схемы (просто "example.com") — молча
    # дополняем "https://", а не отклоняем как невалидный URL. Так надёжнее
    # для администратора, который может не знать про обязательный http(s)://.
    link_url = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = ScheduleEvent
        fields = ['title', 'description', 'link_url', 'starts_at', 'course']

    def validate_link_url(self, value):
        value = (value or '').strip()
        if not value:
            return ''
        if not value.lower().startswith(('http://', 'https://')):
            value = f'https://{value}'
        validator = serializers.URLField()
        return validator.run_validation(value)
