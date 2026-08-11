from pathlib import Path

from django.core.management.base import BaseCommand

from apps.courses.media_utils import transcode_lesson_video
from apps.courses.models import Lesson


class Command(BaseCommand):
    help = "Switch lessons to existing *_web.mp4 files or transcode uploaded videos."

    def handle(self, *args, **options):
        updated = 0
        transcoded = 0
        skipped = 0

        for lesson in Lesson.objects.exclude(video_file=""):
            if not lesson.video_file:
                skipped += 1
                continue

            try:
                current_path = Path(lesson.video_file.path)
            except (ValueError, NotImplementedError):
                skipped += 1
                continue

            if current_path.stem.endswith("_web"):
                skipped += 1
                continue

            web_path = current_path.with_name(f"{current_path.stem}_web.mp4")
            if web_path.exists():
                media_root = Path(lesson.video_file.storage.location)
                lesson.video_file.name = web_path.relative_to(media_root).as_posix()
                lesson.save(update_fields=["video_file"])
                updated += 1
                self.stdout.write(f"updated lesson {lesson.id}: {lesson.video_file.name}")
                continue

            transcode_lesson_video(lesson)
            lesson.refresh_from_db(fields=["video_file"])
            if lesson.video_file and Path(lesson.video_file.name).stem.endswith("_web"):
                transcoded += 1
                self.stdout.write(f"transcoded lesson {lesson.id}: {lesson.video_file.name}")
            else:
                skipped += 1
                self.stdout.write(f"skipped lesson {lesson.id}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. updated={updated}, transcoded={transcoded}, skipped={skipped}"
            )
        )
