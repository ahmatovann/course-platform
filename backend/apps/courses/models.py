from django.conf import settings
from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, default='')
    certificate_on_completion = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    require_test_to_unlock_next = models.BooleanField(default=True)
    pass_threshold_percent = models.PositiveIntegerField(default=80)
    allow_downloads = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.course.title} · {self.title}'


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, default='')
    video_url = models.CharField(max_length=500, blank=True, default='')
    video_file = models.FileField(upload_to='lessons/videos/', blank=True, null=True)
    # Кадр из видео (превью) и аудио-версия — извлекаются автоматически на
    # сервере при перекодировании видео (см. apps.courses.media_utils).
    video_poster = models.ImageField(upload_to='lessons/posters/', blank=True, null=True)
    video_audio_file = models.FileField(upload_to='lessons/audio/', blank=True, null=True)
    # Длительность определяется автоматически на фронтенде из самого видео-файла
    # при выборе (через HTML5 video-элемент) — вручную администратор её не вводит.
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class Material(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='materials')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='lessons/materials/', blank=True, null=True)
    kind = models.CharField(max_length=20, default='file')
    # Ученик может отметить файл урока «в избранное» — чтобы быстро вернуться
    # к нему позже (конспектировать/разбираться), не ища заново по курсу.
    favorited_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='favorite_materials',
    )

    def __str__(self):
        return self.name


class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_entries')
    watched = models.BooleanField(default=False)
    watched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'lesson')


class Test(models.Model):
    module = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='test')
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text


class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text


class Comment(models.Model):
    """Комментарий ученика (или админа) под видео урока."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_comments')
    text = models.TextField()
    # Необязательная привязка комментария к конкретному моменту видео (в секундах) —
    # ученик может прокомментировать конкретный кадр/момент, а не весь урок целиком.
    video_timestamp_seconds = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user_id} @ {self.lesson_id}: {self.text[:40]}'


class TestAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    score_percent = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
