"""
Тесты перекодирования видео уроков (apps.courses.media_utils).

Один тест реально гоняет ffmpeg (если он установлен на машине, где
запускаются тесты — иначе аккуратно пропускается через skipUnless),
остальные проверяют, что при отсутствии ffmpeg на сервере функция
безопасно ничего не делает (не роняет запрос загрузки видео).
"""
import shutil
import subprocess
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APITestCase

from . import media_utils
from .models import Course, Lesson, Module

User = get_user_model()

FFMPEG_AVAILABLE = bool(shutil.which('ffmpeg')) and bool(shutil.which('ffprobe'))


def _make_test_clip(path, audio_codec='ac3'):
    subprocess.run(
        [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'testsrc=size=64x64:duration=1:rate=5',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
            '-c:v', 'libx264', '-c:a', audio_codec, '-shortest', path,
        ],
        capture_output=True, timeout=60, check=True,
    )


class TranscodeNoopWithoutFfmpegTests(TestCase):
    """Если ffmpeg не установлен на сервере — загрузка видео не должна падать."""

    def setUp(self):
        self.course = Course.objects.create(title='Курс', slug='kurs')
        self.module = Module.objects.create(course=self.course, title='Модуль', order=1)
        self.lesson = Lesson.objects.create(
            module=self.module, title='Урок', order=1,
            video_file=SimpleUploadedFile('clip.mp4', b'not a real video, just bytes'),
        )

    def test_noop_when_ffmpeg_missing(self):
        original_name = self.lesson.video_file.name
        with mock.patch.object(media_utils, 'FFMPEG_BIN', None):
            media_utils.transcode_lesson_video(self.lesson)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.video_file.name, original_name)

    def test_noop_when_no_video_file(self):
        self.lesson.video_file = None
        self.lesson.save()
        # Не должно бросать исключений.
        media_utils.transcode_lesson_video(self.lesson)


class ImageioFfmpegFallbackTests(TestCase):
    """
    Если на компьютере администратора не установлен системный ffmpeg
    (обычная ситуация на «чистом» Windows) — модуль должен сам найти
    статический ffmpeg-бинарник из пакета imageio-ffmpeg, без какой-либо
    ручной настройки PATH.
    """

    def test_falls_back_to_imageio_ffmpeg_when_system_ffmpeg_missing(self):
        with mock.patch.object(media_utils.shutil, 'which', return_value=None):
            resolved = media_utils._resolve_ffmpeg_bin()
        self.assertIsNotNone(resolved)
        self.assertTrue(shutil.which('true') or True)  # no-op sanity guard
        result = subprocess.run([resolved, '-version'], capture_output=True, text=True, timeout=20)
        self.assertIn('ffmpeg version', result.stdout)

    def test_duration_falls_back_to_ffmpeg_stderr_when_ffprobe_missing(self):
        if not shutil.which('ffmpeg'):
            self.skipTest('ffmpeg недоступен в этом окружении')
        with tempfile.NamedTemporaryFile(suffix='.mp4') as tmp:
            _make_test_clip(tmp.name, audio_codec='aac')
            with mock.patch.object(media_utils, 'FFPROBE_BIN', None):
                duration = media_utils.probe_duration_seconds(tmp.name)
        self.assertIsNotNone(duration)
        self.assertGreaterEqual(duration, 1)


class TranscodeIntegrationTests(APITestCase):
    """
    Реальная перекодировка: загружаем видео с аудиодорожкой в кодеке (AC3),
    который браузеры не умеют декодировать — характерная причина «видео
    смотрится, а звука не слышно». После перекодирования аудиодорожка
    должна стать AAC (универсально поддерживаемый браузерами кодек).
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin2@example.com', email='admin2@example.com',
            password='pass12345', role=User.Role.ADMIN,
        )
        self.course = Course.objects.create(title='Курс', slug='kurs2')
        self.module = Module.objects.create(course=self.course, title='Модуль', order=1)
        self.lesson = Lesson.objects.create(module=self.module, title='Урок', order=1)

    def _probe_audio_codec(self, path):
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
             '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip()

    def test_upload_with_incompatible_audio_codec_gets_transcoded_to_aac(self):
        if not FFMPEG_AVAILABLE:
            self.skipTest('ffmpeg/ffprobe не установлены в этом окружении')

        with tempfile.NamedTemporaryFile(suffix='.mp4') as tmp:
            _make_test_clip(tmp.name, audio_codec='ac3')
            tmp.seek(0)
            self.assertEqual(self._probe_audio_codec(tmp.name), 'ac3')

            self.client.force_authenticate(user=self.admin)
            upload = SimpleUploadedFile('clip.mp4', tmp.read(), content_type='video/mp4')
            response = self.client.patch(
                f'/api/admin/lessons/{self.lesson.id}/', {'video_file': upload}, format='multipart',
            )
            self.assertEqual(response.status_code, 200, response.data)

        self.lesson.refresh_from_db()
        self.assertTrue(self.lesson.video_file.name.endswith('.mp4'))
        codec = self._probe_audio_codec(self.lesson.video_file.path)
        self.assertEqual(codec, 'aac')
        # Длительность должна была определиться автоматически (~1 секунда).
        self.assertGreaterEqual(self.lesson.duration_seconds, 1)
