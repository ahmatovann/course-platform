"""Генерация PDF-сертификата об окончании курса."""
import io

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def generate_certificate_pdf(user, course):
    buffer = io.BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    navy = colors.HexColor('#121B30')
    gold = colors.HexColor('#C9A66B')

    c.setFillColor(navy)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setStrokeColor(gold)
    c.setLineWidth(2)
    c.rect(20 * mm, 15 * mm, width - 40 * mm, height - 30 * mm, fill=0, stroke=1)

    c.setFillColor(gold)
    c.setFont('Helvetica-Bold', 30)
    c.drawCentredString(width / 2, height - 55 * mm, 'СЕРТИФИКАТ')

    c.setFillColor(colors.white)
    c.setFont('Helvetica', 14)
    c.drawCentredString(width / 2, height - 70 * mm, 'подтверждает, что')

    name = user.get_full_name() or user.email
    c.setFillColor(gold)
    c.setFont('Helvetica-Bold', 24)
    c.drawCentredString(width / 2, height - 85 * mm, name)

    c.setFillColor(colors.white)
    c.setFont('Helvetica', 14)
    c.drawCentredString(width / 2, height - 100 * mm, 'успешно завершил(а) курс')

    c.setFillColor(gold)
    c.setFont('Helvetica-Bold', 20)
    c.drawCentredString(width / 2, height - 115 * mm, course.title)

    c.setFillColor(colors.white)
    c.setFont('Helvetica', 11)
    c.drawCentredString(width / 2, 30 * mm, f'Дата: {timezone.now():%d.%m.%Y}   ·   COURSE')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
