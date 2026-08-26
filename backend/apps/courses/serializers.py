from rest_framework import serializers

from .models import (
    Course, Module, Lesson, Material, Test, Question, AnswerOption, TestAttempt, Comment,
)
from .services import module_status, is_module_unlocked, course_progress_percent


class MaterialSerializer(serializers.ModelSerializer):
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = ['id', 'name', 'file', 'kind', 'is_favorite']

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.favorited_by.filter(pk=request.user.id).exists())


class LessonListSerializer(serializers.ModelSerializer):
    watched = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'order', 'duration_seconds', 'watched']

    def get_watched(self, obj):
        user = self.context['request'].user
        return obj.progress_entries.filter(user=user, watched=True).exists()


class LessonDetailSerializer(LessonListSerializer):
    materials = MaterialSerializer(many=True, read_only=True)

    class Meta(LessonListSerializer.Meta):
        fields = LessonListSerializer.Meta.fields + [
            'description', 'video_url', 'video_file', 'video_poster', 'video_audio_file',
            'materials', 'module',
        ]


class FavoriteMaterialSerializer(serializers.ModelSerializer):
    """Файл урока, отмеченный учеником «в избранное» — с указанием, в каком
    курсе/модуле/уроке он находится, чтобы ученик мог быстро вернуться туда."""
    lesson_id = serializers.IntegerField(source='lesson.id', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    module_title = serializers.CharField(source='lesson.module.title', read_only=True)
    course_title = serializers.CharField(source='lesson.module.course.title', read_only=True)

    class Meta:
        model = Material
        fields = ['id', 'name', 'file', 'kind', 'lesson_id', 'lesson_title', 'module_title', 'course_title']


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'text', 'video_timestamp_seconds', 'user_name', 'is_mine', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return bool(request and obj.user_id == request.user.id)


class AnswerOptionPublicSerializer(serializers.ModelSerializer):
    """Не отдаём is_correct ученику."""
    class Meta:
        model = AnswerOption
        fields = ['id', 'text']


class QuestionPublicSerializer(serializers.ModelSerializer):
    options = AnswerOptionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'options']


class TestPublicSerializer(serializers.ModelSerializer):
    questions = QuestionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = ['id', 'title', 'questions']


class ModuleListSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    unlocked = serializers.SerializerMethodField()
    has_test = serializers.SerializerMethodField()
    test_id = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'title', 'order', 'status', 'unlocked', 'has_test', 'test_id', 'pass_threshold_percent']

    def get_status(self, obj):
        return module_status(self.context['request'].user, obj)

    def get_unlocked(self, obj):
        return is_module_unlocked(self.context['request'].user, obj)

    def get_has_test(self, obj):
        return hasattr(obj, 'test')

    def get_test_id(self, obj):
        return obj.test.id if hasattr(obj, 'test') else None


class ModuleDetailSerializer(ModuleListSerializer):
    lessons = LessonListSerializer(many=True, read_only=True)

    class Meta(ModuleListSerializer.Meta):
        fields = ModuleListSerializer.Meta.fields + ['lessons']


class CourseListSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()
    modules_count = serializers.SerializerMethodField()
    enrolled = serializers.SerializerMethodField()
    certificate_available = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'description', 'modules_count', 'progress_percent',
            'enrolled', 'certificate_available',
        ]

    def get_progress_percent(self, obj):
        return course_progress_percent(self.context['request'].user, obj)

    def get_modules_count(self, obj):
        return obj.modules.count()

    def get_enrolled(self, obj):
        return obj.enrollments.filter(user=self.context['request'].user).exists()

    def get_certificate_available(self, obj):
        return bool(obj.certificate_on_completion) and self.get_progress_percent(obj) >= 100


class CourseDetailSerializer(CourseListSerializer):
    modules = ModuleListSerializer(many=True, read_only=True)

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + ['modules']


class TestSubmitSerializer(serializers.Serializer):
    # { question_id: option_id }
    answers = serializers.DictField(child=serializers.IntegerField())

    def save(self, **kwargs):
        test = self.context['test']
        user = self.context['request'].user
        answers = self.validated_data['answers']
        questions = list(test.questions.all())
        correct = 0
        for q in questions:
            chosen_id = answers.get(str(q.id)) or answers.get(q.id)
            if chosen_id is not None and q.options.filter(id=chosen_id, is_correct=True).exists():
                correct += 1
        total = len(questions) or 1
        score = round(correct / total * 100)
        passed = score >= test.module.pass_threshold_percent
        return TestAttempt.objects.create(user=user, test=test, score_percent=score, passed=passed)


class TestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAttempt
        fields = ['id', 'score_percent', 'passed', 'submitted_at']
