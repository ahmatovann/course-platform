export function embedVideoUrl(url) {
  if (!url) return null

  try {
    const parsedUrl = new URL(url)
    const host = parsedUrl.hostname.replace(/^www\./, '')

    if (host === 'youtu.be') {
      const id = parsedUrl.pathname.slice(1)
      return id ? `https://www.youtube.com/embed/${id}` : null
    }

    if (host === 'youtube.com' || host === 'm.youtube.com') {
      if (parsedUrl.pathname === '/watch') {
        const id = parsedUrl.searchParams.get('v')
        return id ? `https://www.youtube.com/embed/${id}` : null
      }
      if (parsedUrl.pathname.startsWith('/embed/')) return url
      if (parsedUrl.pathname.startsWith('/shorts/')) {
        const id = parsedUrl.pathname.split('/')[2]
        return id ? `https://www.youtube.com/embed/${id}` : null
      }
    }

    if (host === 'vimeo.com') {
      const id = parsedUrl.pathname.split('/').filter(Boolean)[0]
      return id && /^\d+$/.test(id) ? `https://player.vimeo.com/video/${id}` : null
    }
    if (host === 'player.vimeo.com') return url
  } catch {
    return null
  }

  return null
}
