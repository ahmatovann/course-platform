from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.courses.models import Course
from .models import AuditLogEntry

User = get_user_model()


class AuditLogEntrySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLogEntry
        fields = ['id', 'actor_name', 'action', 'target_type', 'target_repr', 'created_at']

    def get_actor_name(self, obj):
        if not obj.actor:
            return 'Удалённый пользователь'
        return obj.actor.get_full_name() or obj.actor.email


class StudentSerializer(serializers.ModelSerializer):
    course_titles = serializers.SerializerMethodField()
    course_ids = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone',
            'is_active_student', 'date_joined', 'access_expires_at', 'course_titles', 'course_ids',
        ]

    def get_course_titles(self, obj):
        return [e.course.title for e in obj.enrollments.select_related('course').all()]

    def get_course_ids(self, obj):
        return [e.course_id for e in obj.enrollments.all()]


class CreateStudentSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), required=False, allow_null=True)
    # Срок доступа ученика — администратор сам выбирает количество и единицу
    # (день/неделя/месяц) вместо фиксированных 3 месяцев.
    access_amount = serializers.IntegerField(required=False, default=3, min_value=1, max_value=3650)
    access_unit = serializers.ChoiceField(choices=['day', 'week', 'month'], required=False, default='month')

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Этот email уже зарегистрирован')
        return value

    def validate_phone(self, value):
        if value and User.objects.filter(phone=value).exclude(phone='').exists():
            raise serializers.ValidationError('Этот телефон уже используется')
        return value


# ===== Конструктор тренинга (курсы/модули/уроки) =====

from apps.courses.models import Module, Lesson, Test, Question, AnswerOption, Material  # noqa: E402


class AdminMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ['id', 'name', 'file', 'kind']


class AdminLessonSerializer(serializers.ModelSerializer):
    materials = AdminMaterialSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'order', 'description', 'video_url', 'video_file',
            'video_poster', 'video_audio_file', 'duration_seconds', 'materials',
        ]


class AdminModuleSerializer(serializers.ModelSerializer):
    lessons = AdminLessonSerializer(many=True, read_only=True)
    has_test = serializers.SerializerMethodField()
    test_id = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = [
            'id', 'title', 'order', 'require_test_to_unlock_next',
            'pass_threshold_percent', 'allow_downloads', 'lessons',
            'has_test', 'test_id',
        ]

    def get_has_test(self, obj):
        return hasattr(obj, 'test')

    def get_test_id(self, obj):
        return obj.test.id if hasattr(obj, 'test') else None


class AdminModuleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['title', 'require_test_to_unlock_next', 'pass_threshold_percent', 'allow_downloads']


class AdminCourseWriteSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Course
        fields = ['title', 'slug', 'description']

    def validate_slug(self, value):
        if value and Course.objects.filter(slug=value).exists():
            raise serializers.ValidationError('Курс с таким slug уже существует')
        return value

    def create(self, validated_data):
        import secrets
        from django.utils.text import slugify
        if not validated_data.get('slug'):
            base = slugify(validated_data['title'])
            if not base:
                # заголовок не в латинице (например, кириллица) — используем короткий случайный slug
                base = 'course-' + secrets.token_hex(3)
            slug = base
            i = 1
            while Course.objects.filter(slug=slug).exists():
                i += 1
                slug = f'{base}-{i}'
            validated_data['slug'] = slug
        return Course.objects.create(**validated_data)


class AdminModuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['title']


class AdminCourseSerializer(serializers.ModelSerializer):
    modules = AdminModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'description', 'modules']


class AdminLessonWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['title', 'order', 'description', 'video_url', 'video_file', 'duration_seconds']


class AdminMaterialWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ['name', 'file', 'kind']


# ===== Тесты =====

class AdminAnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ['id', 'text', 'is_correct', 'order']


class AdminQuestionSerializer(serializers.ModelSerializer):
    options = AdminAnswerOptionSerializer(many=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'options']


class AdminTestSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)
    questions = AdminQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = [
            'id', 'title', 'module', 'module_title', 'questions',
            'require_lessons_watched', 'max_attempts',
        ]


class AdminTestWriteSerializer(serializers.Serializer):
    """Создание/полная замена теста и его вопросов одним запросом."""
    title = serializers.CharField(max_length=200)
    module = serializers.PrimaryKeyRelatedField(queryset=Module.objects.all())
    questions = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    require_lessons_watched = serializers.BooleanField(required=False, default=True)
    max_attempts = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1000)

    def validate_questions(self, value):
        for q in value:
            if not q.get('text', '').strip():
                raise serializers.ValidationError('У каждого вопроса должен быть текст')
            options = q.get('options') or []
            if len(options) < 2:
                raise serializers.ValidationError('У вопроса должно быть минимум 2 варианта ответа')
            if not any(o.get('is_correct') for o in options):
                raise serializers.ValidationError('У каждого вопроса должен быть отмечен правильный вариант')
        return value

    def create(self, validated_data):
        test = Test.objects.create(
            title=validated_data['title'], module=validated_data['module'],
            require_lessons_watched=validated_data['require_lessons_watched'],
            max_attempts=validated_data['max_attempts'],
        )
        self._write_questions(test, validated_data['questions'])
        return test

    def update(self, instance, validated_data):
        instance.title = validated_data['title']
        instance.require_lessons_watched = validated_data['require_lessons_watched']
        instance.max_attempts = validated_data['max_attempts']
        instance.save(update_fields=['title', 'require_lessons_watched', 'max_attempts'])
        instance.questions.all().delete()
        self._write_questions(instance, validated_data['questions'])
        return instance

    def _write_questions(self, test, questions):
        for qi, q in enumerate(questions, start=1):
            question = Question.objects.create(test=test, text=q['text'], order=qi)
            for oi, o in enumerate(q.get('options', []), start=1):
                AnswerOption.objects.create(
                    question=question, text=o.get('text', ''),
                    is_correct=bool(o.get('is_correct')), order=oi,
                )
