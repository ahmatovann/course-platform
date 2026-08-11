"""Экспорт данных в Excel (.xlsx) для админ-панели."""
import io

from openpyxl import Workbook
from openpyxl.styles import Font


def _autosize(ws):
    for col in ws.columns:
        values = [str(c.value) for c in col if c.value is not None]
        length = max((len(v) for v in values), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max(length + 2, 12), 40)


def export_student_progress_xlsx(courses_data):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Прогресс'
    headers = ['Тренинг', 'Модуль', 'Уроков просмотрено', 'Всего уроков', 'Есть тест', 'Балл теста', 'Статус']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for course in courses_data:
        for m in course['modules']:
            if m['completed']:
                mstatus = 'Пройден'
            elif not m['unlocked']:
                mstatus = 'Заблокирован'
            else:
                mstatus = 'В процессе'
            ws.append([
                course['course_title'],
                m['title'],
                m['lessons_watched'],
                m['lessons_total'],
                'Да' if m['has_test'] else 'Нет',
                m['test_best_score'] if m['test_best_score'] is not None else '—',
                mstatus,
            ])

    _autosize(ws)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def export_students_xlsx(students):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Ученики'
    headers = ['Имя', 'Фамилия', 'Email', 'Телефон', 'Статус', 'Дата регистрации', 'Курсы']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for s in students:
        ws.append([
            s.first_name,
            s.last_name,
            s.email,
            s.phone or '—',
            'Активен' if s.is_active_student else 'Не активен',
            s.date_joined.strftime('%d.%m.%Y'),
            ', '.join(e.course.title for e in s.enrollments.all()),
        ])

    _autosize(ws)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
