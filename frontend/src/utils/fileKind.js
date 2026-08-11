// Автоопределение типа прикреплённого файла по его MIME-типу/расширению —
// администратору не нужно вручную выбирать тип из списка.

export function detectKind(file) {
  if (!file) return 'file'
  const name = (file.name || '').toLowerCase()
  const type = file.type || ''
  if (type.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg|bmp)$/.test(name)) return 'image'
  if (type.startsWith('audio/') || /\.(mp3|wav|ogg|m4a|aac|weba)$/.test(name)) return 'audio'
  if (type.startsWith('video/') || /\.(mp4|mov|webm|avi|mkv)$/.test(name)) return 'video'
  if (/\.(ppt|pptx|key)$/.test(name)) return 'presentation'
  if (/\.(pdf)$/.test(name)) return 'pdf'
  if (/\.(doc|docx|odt|rtf)$/.test(name)) return 'document'
  if (/\.(xls|xlsx|ods|csv)$/.test(name)) return 'spreadsheet'
  if (/\.(zip|rar|7z|tar|gz)$/.test(name)) return 'archive'
  if (type.startsWith('text/') || /\.(txt|md)$/.test(name)) return 'text'
  // Любой другой тип файла всё равно принимается — просто без узнаваемой иконки.
  return 'file'
}

const LABELS = {
  image: 'Изображение', audio: 'Аудио', video: 'Видео',
  presentation: 'Презентация', pdf: 'PDF-документ', file: 'Файл',
  document: 'Документ Word', spreadsheet: 'Таблица Excel', archive: 'Архив', text: 'Текстовый файл',
}
export function labelForKind(kind) {
  return LABELS[kind] || LABELS.file
}

// Простые геометрические значки — без пиктографических эмодзи, в стиле
// остального интерфейса (см. nav.js).
const ICONS = {
  image: '▨', audio: '♪', video: '▶', presentation: '▥', pdf: '▤', file: '▤',
  document: '▤', spreadsheet: '▦', archive: '▧', text: '▤',
}
export function iconForKind(kind) {
  return ICONS[kind] || ICONS.file
}
