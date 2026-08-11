import { describe, expect, it } from 'vitest'
import { detectKind, iconForKind, labelForKind } from './fileKind'

function fakeFile(name, type) {
  return { name, type }
}

describe('detectKind', () => {
  it('detects images by extension when MIME type is missing', () => {
    expect(detectKind(fakeFile('slide.png', ''))).toBe('image')
    expect(detectKind(fakeFile('photo.JPG', ''))).toBe('image')
  })

  it('detects images by MIME type', () => {
    expect(detectKind(fakeFile('upload', 'image/webp'))).toBe('image')
  })

  it('detects audio files', () => {
    expect(detectKind(fakeFile('lecture.mp3', ''))).toBe('audio')
    expect(detectKind(fakeFile('voice', 'audio/wav'))).toBe('audio')
  })

  it('detects video files', () => {
    expect(detectKind(fakeFile('lesson.mp4', ''))).toBe('video')
  })

  it('detects presentations', () => {
    expect(detectKind(fakeFile('deck.pptx', ''))).toBe('presentation')
  })

  it('detects PDF documents', () => {
    expect(detectKind(fakeFile('handout.pdf', ''))).toBe('pdf')
  })

  it('detects Word documents', () => {
    expect(detectKind(fakeFile('lecture.docx', ''))).toBe('document')
    expect(detectKind(fakeFile('notes.doc', ''))).toBe('document')
  })

  it('detects Excel spreadsheets', () => {
    expect(detectKind(fakeFile('grades.xlsx', ''))).toBe('spreadsheet')
    expect(detectKind(fakeFile('data.csv', ''))).toBe('spreadsheet')
  })

  it('detects archives', () => {
    expect(detectKind(fakeFile('materials.zip', ''))).toBe('archive')
  })

  it('detects plain text files', () => {
    expect(detectKind(fakeFile('readme.txt', ''))).toBe('text')
  })

  it('falls back to generic file for unknown types', () => {
    expect(detectKind(fakeFile('data.xyz', ''))).toBe('file')
  })

  it('handles a missing file gracefully', () => {
    expect(detectKind(null)).toBe('file')
  })
})

describe('labelForKind / iconForKind', () => {
  it('returns a Russian label for every known kind', () => {
    expect(labelForKind('image')).toBe('Изображение')
    expect(labelForKind('pdf')).toBe('PDF-документ')
    expect(labelForKind('unknown-kind')).toBe('Файл')
  })

  it('returns a non-empty icon for every known kind', () => {
    for (const kind of ['image', 'audio', 'video', 'presentation', 'pdf', 'file', 'document', 'spreadsheet', 'archive', 'text']) {
      expect(iconForKind(kind)).toBeTruthy()
    }
  })
})
