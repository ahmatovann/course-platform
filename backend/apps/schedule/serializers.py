from django.utils import timezone
from rest_framework import serializers

from .models import ScheduleEvent


class ScheduleEventSerializer(serializers.ModelSerializer):
    course_title = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleEvent
        fields = [
            'id', 'title', 'description', 'link_url', 'publish_at', 'hide_at',
            'course', 'course_title', 'status', 'is_favorite',
        ]

    def get_course_title(self, obj):
        return obj.course.title if obj.course_id else None

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        return bool(request and getattr(request.user, 'is_authenticated', False) and obj.favorited_by.filter(pk=request.user.id).exists())

    def get_status(self, obj):
        """Только для отображения в админке: запланирована / опубликована / скрыта."""
        now = timezone.now()
        if obj.publish_at > now:
            return 'scheduled'
        if obj.hide_at and obj.hide_at <= now:
            return 'hidden'
        return 'published'


class ScheduleEventWriteSerializer(serializers.ModelSerializer):
    # Ссылку принимаем и без явной схемы (просто "example.com") — молча
    # дополняем "https://", а не отклоняем как невалидный URL. Так надёжнее
    # для администратора, который может не знать про обязательный http(s)://.
    link_url = serializers.CharField(required=False, allow_blank=True, default='')
    hide_at = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = ScheduleEvent
        fields = ['title', 'description', 'link_url', 'publish_at', 'hide_at', 'course']

    def validate_link_url(self, value):
        value = (value or '').strip()
        if not value:
            return ''
        if not value.lower().startswith(('http://', 'https://')):
            value = f'https://{value}'
        validator = serializers.URLField()
        return validator.run_validation(value)

    def validate(self, attrs):
        hide_at = attrs.get('hide_at')
        publish_at = attrs.get('publish_at', getattr(self.instance, 'publish_at', None))
        if hide_at and publish_at and hide_at <= publish_at:
            raise serializers.ValidationError({'hide_at': 'Дата скрытия должна быть позже даты рассылки'})
        return attrs
