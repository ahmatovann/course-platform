"""Экспорт данных в Excel (.xlsx) и PDF для админ-панели."""
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


# ===== PDF-варианты тех же двух отчётов (тот же набор данных, другой формат) =====

_NAVY = None
_GOLD = None
_UNICODE_FONT = None


def _pdf_colors():
    # Ленивый импорт reportlab/colors — держим его рядом с остальным PDF-кодом,
    # чтобы модуль оставался лёгким для тех мест, где нужен только Excel.
    global _NAVY, _GOLD
    from reportlab.lib import colors
    if _NAVY is None:
        _NAVY = colors.HexColor('#121B30')
        _GOLD = colors.HexColor('#C9A66B')
    return colors, _NAVY, _GOLD


def _register_unicode_font():
    """Встроенные шрифты reportlab (Helvetica и т.п.) не содержат кириллицу —
    ФИО, статусы и названия тренингов на русском в PDF не отобразились бы.
    Регистрируем первый найденный системный TTF-шрифт с поддержкой кириллицы;
    если ни одного не нашлось — используем Helvetica (тогда кириллица в PDF
    может отображаться некорректно, но экспорт хотя бы не упадёт с ошибкой)."""
    global _UNICODE_FONT
    if _UNICODE_FONT is not None:
        return _UNICODE_FONT
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf'),
        (r'C:\Windows\Fonts\calibri.ttf', r'C:\Windows\Fonts\calibrib.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
        ('/Library/Fonts/Arial.ttf', '/Library/Fonts/Arial Bold.ttf'),
    ]
    for regular, bold in candidates:
        if os.path.exists(regular):
            try:
                pdfmetrics.registerFont(TTFont('ReportSans', regular))
                pdfmetrics.registerFont(TTFont('ReportSans-Bold', bold if os.path.exists(bold) else regular))
                _UNICODE_FONT = ('ReportSans', 'ReportSans-Bold')
                return _UNICODE_FONT
            except Exception:
                continue
    _UNICODE_FONT = ('Helvetica', 'Helvetica-Bold')
    return _UNICODE_FONT


def _pdf_table_doc(title, headers, rows):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from django.utils import timezone

    colors, navy, gold = _pdf_colors()
    font, font_bold = _register_unicode_font()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    styles['Title'].textColor = navy
    styles['Title'].fontName = font_bold
    styles['Normal'].fontName = font

    elements = [
        Paragraph(title, styles['Title']),
        Paragraph(f'Сформировано: {timezone.localtime():%d.%m.%Y %H:%M}', styles['Normal']),
        Spacer(1, 6 * mm),
    ]

    table = Table([headers, *rows], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), gold),
        ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ('FONTNAME', (0, 1), (-1, -1), font),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f4f4')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def export_students_pdf(students):
    headers = ['Имя', 'Фамилия', 'Email', 'Телефон', 'Статус', 'Дата регистрации', 'Курсы']
    rows = [[
        s.first_name,
        s.last_name,
        s.email,
        s.phone or '—',
        'Активен' if s.is_active_student else 'Не активен',
        s.date_joined.strftime('%d.%m.%Y'),
        ', '.join(e.course.title for e in s.enrollments.all()),
    ] for s in students]
    return _pdf_table_doc('Список учеников', headers, rows)


def export_student_progress_pdf(courses_data, student_name=''):
    headers = ['Тренинг', 'Модуль', 'Уроков просмотрено', 'Всего уроков', 'Есть тест', 'Балл теста', 'Статус']
    rows = []
    for course in courses_data:
        for m in course['modules']:
            if m['completed']:
                mstatus = 'Пройден'
            elif not m['unlocked']:
                mstatus = 'Заблокирован'
            else:
                mstatus = 'В процессе'
            rows.append([
                course['course_title'],
                m['title'],
                m['lessons_watched'],
                m['lessons_total'],
                'Да' if m['has_test'] else 'Нет',
                m['test_best_score'] if m['test_best_score'] is not None else '—',
                mstatus,
            ])
    title = f'Прогресс — {student_name}' if student_name else 'Прогресс ученика'
    return _pdf_table_doc(title, headers, rows)


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
