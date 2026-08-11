from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.courses.models import (
    Course, Module, Lesson, Material, Test, Question, AnswerOption, Enrollment,
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Заполняет базу демо-данными, совпадающими с HTML-прототипом'

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            email='admin@course.local',
            defaults=dict(username='admin@course.local', first_name='Course', last_name='Admin',
                          role=User.Role.ADMIN, is_staff=True, is_superuser=True, must_change_password=False),
        )
        if created:
            admin.set_password('admin12345')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Создан админ: admin@course.local / admin12345'))

        anna, created = User.objects.get_or_create(
            email='anna@mail.com',
            defaults=dict(username='anna@mail.com', first_name='Анна', last_name='Ким',
                          role=User.Role.STUDENT, phone='+996700000000', country='Киргизия', city='Бишкек',
                          must_change_password=False),
        )
        if created:
            anna.set_password('anna12345')
            anna.save()
            self.stdout.write(self.style.SUCCESS('Создана ученица: anna@mail.com / anna12345'))

        course, _ = Course.objects.get_or_create(
            slug='osnovy-vizazha-start',
            defaults=dict(title='Основы визажа: старт',
                          description='6 модулей · 24 урока · сертификат по окончании', order=1),
        )
        Enrollment.objects.get_or_create(user=anna, course=course)

        modules_spec = [
            ('Модуль 1. Инструменты и материалы', [
                'Введение в инструменты', 'Кисти и спонжи', 'Уход за инструментами',
            ], False),
            ('Модуль 2. Тон и коррекция лица', [
                'Праймер и база под тон', 'Средства для коррекции', 'Нанесение тонального средства',
            ], True),
            ('Модуль 3. Глаза и брови', [
                'Форма бровей', 'Основы макияжа глаз',
            ], True),
            ('Модуль 4. Скулы и финальный образ', [
                'Скульптурирование', 'Финальная фиксация образа',
            ], True),
        ]

        prev_module = None
        for order, (title, lessons, require_test) in enumerate(modules_spec, start=1):
            module, _ = Module.objects.get_or_create(
                course=course, order=order,
                defaults=dict(title=title, require_test_to_unlock_next=True,
                              pass_threshold_percent=80, allow_downloads=True),
            )
            for lorder, ltitle in enumerate(lessons, start=1):
                Lesson.objects.get_or_create(
                    module=module, order=lorder,
                    defaults=dict(title=ltitle, video_url='', duration_seconds=600),
                )

            if require_test:
                test, _ = Test.objects.get_or_create(module=module, defaults=dict(title=f'Тест: {title}'))
                if not test.questions.exists():
                    q1 = Question.objects.create(test=test, order=1,
                        text='Какой оттенок корректора нейтрализует синеву под глазами?')
                    AnswerOption.objects.create(question=q1, text='Зелёный', order=1)
                    AnswerOption.objects.create(question=q1, text='Персиковый / оранжевый', is_correct=True, order=2)
                    AnswerOption.objects.create(question=q1, text='Фиолетовый', order=3)

                    q2 = Question.objects.create(test=test, order=2, text='Праймер наносится...')
                    AnswerOption.objects.create(question=q2, text='До тонального средства', is_correct=True, order=1)
                    AnswerOption.objects.create(question=q2, text='После пудры', order=2)

            prev_module = module

        self.stdout.write(self.style.SUCCESS('Демо-данные готовы.'))
