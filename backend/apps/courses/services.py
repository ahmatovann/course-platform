"""Логика доступа к модулям: модуль N+1 открыт, если модуль N пройден
(все уроки просмотрены и тест сдан выше порога, либо тест не требуется)."""

from .models import LessonProgress, TestAttempt


def module_status(user, module):
    lessons = list(module.lessons.all())
    total = len(lessons)
    watched = LessonProgress.objects.filter(user=user, lesson__in=lessons, watched=True).count()

    test = getattr(module, 'test', None)
    best_attempt = None
    if test:
        best_attempt = (
            TestAttempt.objects.filter(user=user, test=test).order_by('-score_percent').first()
        )
    test_passed = bool(best_attempt and best_attempt.passed)

    return {
        'lessons_total': total,
        'lessons_watched': watched,
        'has_test': bool(test),
        'test_passed': test_passed,
        'test_best_score': best_attempt.score_percent if best_attempt else None,
        'completed': (watched == total) and (test_passed or not test),
    }


def is_module_unlocked(user, module):
    prev = module.__class__.objects.filter(course=module.course, order__lt=module.order).order_by('-order').first()
    if prev is None:
        return True
    if not prev.require_test_to_unlock_next:
        return True
    status = module_status(user, prev)
    return status['completed']


def course_progress_percent(user, course):
    modules = list(course.modules.all())
    if not modules:
        return 0
    done = sum(1 for m in modules if module_status(user, m)['completed'])
    return round(done / len(modules) * 100)
