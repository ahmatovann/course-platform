// Подписи-разделители дат в духе WhatsApp/Telegram: «Сегодня», «Вчера»,
// иначе — полная дата.

export function dayKey(iso) {
  const d = new Date(iso)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

export function dayLabel(iso) {
  const d = new Date(iso)
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)
  if (dayKey(iso) === dayKey(today.toISOString())) return 'Сегодня'
  if (dayKey(iso) === dayKey(yesterday.toISOString())) return 'Вчера'
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: d.getFullYear() !== today.getFullYear() ? 'numeric' : undefined })
}

export function timeLabel(iso) {
  return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}
