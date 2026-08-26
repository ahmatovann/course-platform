import { defineStore } from 'pinia'
import client from '../api/client'
import { downloadBlob } from '../utils/download'

export const useCoursesStore = defineStore('courses', {
  state: () => ({
    courses: [],
    currentCourse: null,
    currentModule: null,
    currentLesson: null,
    currentTest: null,
    lessonComments: [],
    favoriteMaterials: [],
    favoriteLessons: [],
  }),
  actions: {
    async fetchCourses() {
      const { data } = await client.get('/courses/')
      this.courses = data
      return data
    },
    async fetchCourse(slug) {
      const { data } = await client.get(`/courses/${slug}/`)
      this.currentCourse = data
      return data
    },
    async fetchModule(id) {
      const { data } = await client.get(`/courses/modules/${id}/`)
      this.currentModule = data
      return data
    },
    async fetchLesson(id) {
      const { data } = await client.get(`/courses/lessons/${id}/`)
      this.currentLesson = data
      return data
    },
    async markLessonWatched(id) {
      await client.post(`/courses/lessons/${id}/watch/`)
    },
    async fetchComments(lessonId) {
      const { data } = await client.get(`/courses/lessons/${lessonId}/comments/`)
      this.lessonComments = data
      return data
    },
    async postComment(lessonId, text, videoTimestampSeconds = null) {
      const { data } = await client.post(`/courses/lessons/${lessonId}/comments/`, {
        text,
        video_timestamp_seconds: videoTimestampSeconds,
      })
      this.lessonComments.push(data)
      return data
    },
    async fetchTest(id) {
      const { data } = await client.get(`/courses/tests/${id}/`)
      this.currentTest = data
      return data
    },
    async submitTest(id, answers) {
      const { data } = await client.post(`/courses/tests/${id}/submit/`, { answers })
      return data
    },
    // Файлы урока «в избранное» — чтобы ученик мог быстро вернуться к ним
    // позже (конспектировать/разбираться), не ища заново по курсу.
    async toggleMaterialFavorite(material) {
      const { data } = material.is_favorite
        ? await client.delete(`/courses/materials/${material.id}/favorite/`)
        : await client.post(`/courses/materials/${material.id}/favorite/`)
      if (this.currentLesson) {
        const m = this.currentLesson.materials?.find((x) => x.id === material.id)
        if (m) m.is_favorite = data.is_favorite
      }
      return data
    },
    async fetchFavoriteMaterials() {
      const { data } = await client.get('/courses/materials/favorites/')
      this.favoriteMaterials = data
      return data
    },
    // Урок (видео + его аудио-версия) «в избранное» — тем же принципом, что и файлы.
    async toggleLessonFavorite(lesson) {
      const { data } = lesson.is_favorite
        ? await client.delete(`/courses/lessons/${lesson.id}/favorite/`)
        : await client.post(`/courses/lessons/${lesson.id}/favorite/`)
      if (this.currentLesson && this.currentLesson.id === lesson.id) {
        this.currentLesson.is_favorite = data.is_favorite
      }
      return data
    },
    async fetchFavoriteLessons() {
      const { data } = await client.get('/courses/lessons/favorites/')
      this.favoriteLessons = data
      return data
    },
    async downloadCertificate(slug) {
      const res = await client.get(`/courses/${slug}/certificate/`, { responseType: 'blob' })
      downloadBlob(res.data, `certificate-${slug}.pdf`)
    },
  },
})
