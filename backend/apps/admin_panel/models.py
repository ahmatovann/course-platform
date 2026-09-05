from django.db import models
from django.conf import settings


class StudentActivity(models.Model):
	student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='activity_log')
	actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_student_activity')
	action = models.CharField(max_length=80)
	description = models.TextField()
	entity_type = models.CharField(max_length=40, blank=True, default='')
	entity_id = models.PositiveIntegerField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at', '-id']


def record_student_activity(student, action, description, actor=None, entity_type='', entity_id=None):
	return StudentActivity.objects.create(
		student=student, actor=actor, action=action, description=description,
		entity_type=entity_type, entity_id=entity_id,
	)


def record_admin_activity(actor, action, description, entity_type='', entity_id=None):
	return record_student_activity(
		None, action, description, actor, entity_type, entity_id,
	)
