#!/bin/sh
set -e

echo "Ожидаем базу данных..."
python - <<'PYEOF'
import os
import time
import sys

database_url = os.environ.get("DATABASE_URL", "")
if database_url:
    import dj_database_url
    import psycopg2

    cfg = dj_database_url.parse(database_url)
    for attempt in range(30):
        try:
            conn = psycopg2.connect(
                dbname=cfg["NAME"], user=cfg["USER"], password=cfg["PASSWORD"],
                host=cfg["HOST"], port=cfg["PORT"],
            )
            conn.close()
            print("База данных доступна.")
            break
        except Exception as e:
            print(f"БД ещё не готова ({e}), повтор через 1с...")
            time.sleep(1)
    else:
        print("Не удалось дождаться базы данных.", file=sys.stderr)
        sys.exit(1)
PYEOF

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$SEED_DEMO" = "True" ]; then
  python manage.py seed_demo || true
fi

exec gunicorn my_course_project.wsgi:application --bind 0.0.0.0:8000 --workers 3
