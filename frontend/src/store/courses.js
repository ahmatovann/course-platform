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
    async downloadCertificate(slug) {
      const res = await client.get(`/courses/${slug}/certificate/`, { responseType: 'blob' })
      downloadBlob(res.data, `certificate-${slug}.pdf`)
    },
  },
})
