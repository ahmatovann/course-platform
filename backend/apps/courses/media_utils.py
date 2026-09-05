"""
Перекодирование загруженных видео уроков в универсально совместимый формат
(H.264 видео + AAC аудио в контейнере MP4, с faststart для мгновенного
старта воспроизведения в браузере).

Зачем это нужно: администратор может загрузить видео из любого источника
(экспорт с телефона, скринкаст, конвертированный файл), и его аудиодорожка
или контейнер иногда оказываются в кодеке, который браузер не умеет
декодировать (например, PCM/AC3 в AVI/MOV, или несовместимый профиль
H.265) — в таком случае видео воспроизводится, а звука не слышно.
Перекодирование в H.264+AAC/MP4 гарантированно решает эту проблему для
любого файла, который вообще можно прочитать через ffmpeg.

Ffmpeg-бинарник ищется в двух местах, чтобы это работало «из коробки» даже
на компьютере администратора без отдельной установки ffmpeg:
1. `ffmpeg`/`ffprobe` в PATH системы (если установлены вручную);
2. пакет `imageio-ffmpeg` (добавлен в requirements.txt) — он несёт
   готовый статический ffmpeg-бинарник прямо внутри pip-пакета для
   Windows/macOS/Linux, так что после `pip install -r requirements.txt`
   перекодирование работает без какой-либо ручной настройки PATH.

Если оба варианта недоступны — перекодирование тихо пропускается (файл
сохраняется как есть, без ошибки), чтобы не ломать загрузку видео там,
где ffmpeg в принципе недоступен.
"""
import logging
import os
import re
import shutil
import subprocess
import tempfile

from django.core.files import File
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def _resolve_ffmpeg_bin():
    found = shutil.which('ffmpeg')
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        logger.info('imageio-ffmpeg недоступен — перекодирование видео будет пропускаться', exc_info=True)
        return None


FFMPEG_BIN = _resolve_ffmpeg_bin()
# ffprobe отдельно почти никогда не идёт в комплекте с imageio-ffmpeg —
# если его нет в PATH, длительность определяем через сам ffmpeg (см. ниже).
FFPROBE_BIN = shutil.which('ffprobe')


def ffmpeg_available():
    return bool(FFMPEG_BIN)


def probe_duration_seconds(path):
    """Возвращает длительность файла в секундах (int) или None, если не удалось определить."""
    if FFPROBE_BIN:
        try:
            result = subprocess.run(
                [
                    FFPROBE_BIN, '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', path,
                ],
                capture_output=True, text=True, timeout=60,
            )
            value = (result.stdout or '').strip()
            if value:
                return int(float(value))
        except Exception:
            logger.warning('ffprobe duration failed for %s', path, exc_info=True)

    # Без ffprobe — вытаскиваем длительность из служебного вывода самого
    # ffmpeg (строка вида "Duration: 00:01:23.45, start: ...").
    if not FFMPEG_BIN:
        return None
    try:
        result = subprocess.run(
            [FFMPEG_BIN, '-i', path], capture_output=True, text=True, timeout=60,
        )
        match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', result.stderr or '')
        if match:
            hours, minutes, seconds = match.groups()
            return int(int(hours) * 3600 + int(minutes) * 60 + float(seconds))
    except Exception:
        logger.warning('ffmpeg duration probe failed for %s', path, exc_info=True)
    return None


def _extract_poster(video_path, base_name, duration):
    """Достаёт один кадр из середины видео (или 1-й секунды для коротких
    роликов) как JPEG-превью — показывается под плеером и как обложка."""
    timestamp = min(3, max(0, (duration or 2) // 2)) if duration else 1
    fd, tmp_poster = tempfile.mkstemp(suffix='.jpg')
    os.close(fd)
    try:
        cmd = [
            FFMPEG_BIN, '-y', '-ss', str(timestamp), '-i', video_path,
            '-frames:v', '1', '-q:v', '3', tmp_poster,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0 or not os.path.exists(tmp_poster) or os.path.getsize(tmp_poster) == 0:
            logger.warning('ffmpeg не смог извлечь кадр-превью: %s', (result.stderr or b'').decode(errors='ignore')[-500:])
            return None
        with open(tmp_poster, 'rb') as fh:
            data = fh.read()
        return f'{base_name}_poster.jpg', ContentFile(data, name=f'{base_name}_poster.jpg')
    except subprocess.TimeoutExpired:
        logger.warning('ffmpeg превысил таймаут при извлечении кадра-превью')
        return None
    finally:
        if os.path.exists(tmp_poster):
            os.remove(tmp_poster)


def _extract_audio(video_path, base_name):
    """Достаёт звуковую дорожку видео отдельным MP3-файлом — аудио-версия
    урока для тех, кто хочет просто послушать без видео."""
    fd, tmp_audio = tempfile.mkstemp(suffix='.mp3')
    os.close(fd)
    try:
        cmd = [
            FFMPEG_BIN, '-y', '-i', video_path,
            '-vn', '-c:a', 'libmp3lame', '-b:a', '128k', tmp_audio,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(tmp_audio) or os.path.getsize(tmp_audio) == 0:
            logger.warning('ffmpeg не смог извлечь аудио-версию: %s', (result.stderr or b'').decode(errors='ignore')[-500:])
            return None
        with open(tmp_audio, 'rb') as fh:
            data = fh.read()
        return f'{base_name}_audio.mp3', ContentFile(data, name=f'{base_name}_audio.mp3')
    except subprocess.TimeoutExpired:
        logger.warning('ffmpeg превысил таймаут при извлечении аудио-версии')
        return None
    finally:
        if os.path.exists(tmp_audio):
            os.remove(tmp_audio)


def transcode_lesson_video(lesson):
    """
    Перекодирует lesson.video_file в H.264/AAC MP4 «на месте» (обновляет
    сам объект Lesson: video_file и, если удалось определить, duration_seconds).
    Ничего не делает, если файла нет или ffmpeg недоступен на сервере.
    """
    if not lesson.video_file:
        return
    if not ffmpeg_available():
        logger.info('ffmpeg не найден на сервере — перекодирование видео урока %s пропущено', lesson.id)
        return

    try:
        src_path = lesson.video_file.path
    except (ValueError, NotImplementedError):
        # Нестандартное хранилище файлов (например, облачное) — пропускаем.
        return
    if not os.path.exists(src_path):
        return

    fd, tmp_out = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    old_path = src_path
    old_name = lesson.video_file.name
    try:
        cmd = [
            FFMPEG_BIN, '-y', '-i', src_path,
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k', '-ac', '2',
            '-movflags', '+faststart',
            tmp_out,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=900)
        if result.returncode != 0 or not os.path.exists(tmp_out) or os.path.getsize(tmp_out) == 0:
            logger.warning(
                'ffmpeg не смог перекодировать видео урока %s: %s',
                lesson.id, (result.stderr or b'').decode(errors='ignore')[-1000:],
            )
            return

        duration = probe_duration_seconds(tmp_out)
        base_name = os.path.splitext(os.path.basename(old_name))[0]
        new_filename = f'{base_name}_web.mp4'

        with open(tmp_out, 'rb') as fh:
            lesson.video_file.save(new_filename, File(fh), save=False)

        update_fields = ['video_file']
        if duration:
            lesson.duration_seconds = duration
            update_fields.append('duration_seconds')

        poster_field = _extract_poster(tmp_out, base_name, duration)
        if poster_field:
            lesson.video_poster.save(poster_field[0], poster_field[1], save=False)
            update_fields.append('video_poster')

        audio_field = _extract_audio(tmp_out, base_name)
        if audio_field:
            lesson.video_audio_file.save(audio_field[0], audio_field[1], save=False)
            update_fields.append('video_audio_file')

        lesson.save(update_fields=update_fields)

        # Удаляем исходный файл (уже заменён перекодированной версией), чтобы не копить мусор.
        if old_path and os.path.exists(old_path) and old_path != lesson.video_file.path:
            try:
                os.remove(old_path)
            except OSError:
                logger.warning('Не удалось удалить исходный видеофайл %s', old_path, exc_info=True)
    except subprocess.TimeoutExpired:
        logger.warning('ffmpeg превысил таймаут при перекодировании видео урока %s', lesson.id)
    finally:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)


def trim_lesson_video(lesson, start, end):
    """
    Обрезает lesson.video_file до отрезка [start; end] (в секундах) «на
    месте» — заменяет сам файл, пересчитывает duration_seconds и
    перегенерирует превью-кадр (иначе он мог бы остаться от вырезанной
    части видео). Перекодируем, а не просто копируем поток (-c copy),
    чтобы обрезка была точной по кадрам, а не только по ближайшему
    ключевому кадру, и чтобы результат остался в том же web-совместимом
    формате (H.264+AAC/MP4).

    Возвращает True при успехе, False если обрезать не удалось (в этом
    случае вызывающий код должен вернуть ошибку клиенту, а не тихо
    промолчать — в отличие от transcode_lesson_video, где исходный файл
    остаётся рабочим и без перекодирования).
    """
    if not lesson.video_file:
        return False
    if not ffmpeg_available():
        return False

    try:
        src_path = lesson.video_file.path
    except (ValueError, NotImplementedError):
        return False
    if not os.path.exists(src_path):
        return False

    fd, tmp_out = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    old_path = src_path
    old_name = lesson.video_file.name
    try:
        cmd = [
            FFMPEG_BIN, '-y', '-i', src_path,
            '-ss', str(start), '-to', str(end),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k', '-ac', '2',
            '-movflags', '+faststart',
            tmp_out,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=900)
        if result.returncode != 0 or not os.path.exists(tmp_out) or os.path.getsize(tmp_out) == 0:
            logger.warning(
                'ffmpeg не смог обрезать видео урока %s: %s',
                lesson.id, (result.stderr or b'').decode(errors='ignore')[-1000:],
            )
            return False

        duration = probe_duration_seconds(tmp_out)
        base_name = os.path.splitext(os.path.basename(old_name))[0]
        new_filename = f'{base_name}_trim.mp4'

        with open(tmp_out, 'rb') as fh:
            lesson.video_file.save(new_filename, File(fh), save=False)

        update_fields = ['video_file']
        if duration:
            lesson.duration_seconds = duration
            update_fields.append('duration_seconds')

        # Старое превью могло быть кадром из обрезанной части — перегенерируем.
        if lesson.video_poster:
            lesson.video_poster.delete(save=False)
        poster_field = _extract_poster(tmp_out, base_name, duration)
        if poster_field:
            lesson.video_poster.save(poster_field[0], poster_field[1], save=False)
            update_fields.append('video_poster')
        else:
            lesson.video_poster = None
            update_fields.append('video_poster')

        # Старая аудио-версия соответствовала полному ролику — после
        # обрезки она рассинхронизирована с новой длительностью, поэтому
        # тоже перегенерируется из обрезанного видео.
        if lesson.video_audio_file:
            lesson.video_audio_file.delete(save=False)
        audio_field = _extract_audio(tmp_out, base_name)
        if audio_field:
            lesson.video_audio_file.save(audio_field[0], audio_field[1], save=False)
            update_fields.append('video_audio_file')
        else:
            lesson.video_audio_file = None
            update_fields.append('video_audio_file')

        lesson.save(update_fields=update_fields)

        if old_path and os.path.exists(old_path) and old_path != lesson.video_file.path:
            try:
                os.remove(old_path)
            except OSError:
                logger.warning('Не удалось удалить исходный видеофайл %s', old_path, exc_info=True)
        return True
    except subprocess.TimeoutExpired:
        logger.warning('ffmpeg превысил таймаут при обрезке видео урока %s', lesson.id)
        return False
    finally:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)

def ensure_lesson_audio(lesson):
    """Создаёт аудио-версию уже существующего видео без копирования видео."""
    if not lesson.video_file or not ffmpeg_available():
        return
    try:
        video_path = lesson.video_file.path
    except (ValueError, NotImplementedError):
        return
    if not os.path.exists(video_path):
        return

    base_name = os.path.splitext(os.path.basename(lesson.video_file.name))[0]
    audio_field = _extract_audio(video_path, base_name)
    if audio_field:
        lesson.video_audio_file.save(audio_field[0], audio_field[1], save=False)
        lesson.save(update_fields=['video_audio_file'])
