import { defineStore } from 'pinia'
import client from '../api/client'
import { downloadBlob } from '../utils/download'

export const useAdminStore = defineStore('admin', {
  state: () => ({
    students: [],
    adminCourses: [],
    tests: [],
    moduleStats: [],
    media: [],
    auditLog: [],
  }),
  actions: {
    async fetchStudents(params = {}) {
      const { data } = await client.get('/admin/students/', { params })
      this.students = data
      return data
    },
    // format: 'xlsx' | 'pdf'. ids: необязательный массив id учеников — если
    // передан (список отмечен галочками), выгружаются только они, иначе все.
    // Параметр на бэкенде называется filetype, а не format — «format» зарезервирован
    // самим DRF (переключает формат ответа рендерера) и конфликтует с нашим смыслом.
    async exportStudents({ format = 'xlsx', ids = [] } = {}) {
      const params = { filetype: format }
      if (ids.length) params.ids = ids.join(',')
      const res = await client.get('/admin/students/export/', { params, responseType: 'blob' })
      downloadBlob(res.data, `students.${format}`)
    },
    async exportStudentProgress(id, email, format = 'xlsx') {
      const res = await client.get(`/admin/students/${id}/progress/export/`, { params: { filetype: format }, responseType: 'blob' })
      downloadBlob(res.data, `progress-${email || id}.${format}`)
    },
    async createStudent(payload) {
      const { data } = await client.post('/admin/students/create/', payload)
      await this.fetchStudents()
      return data
    },
    async toggleStudent(id) {
      const { data } = await client.post(`/admin/students/${id}/toggle/`)
      const idx = this.students.findIndex((s) => s.id === id)
      if (idx !== -1) this.students[idx] = data
      return data
    },
    // Продлить доступ ученика: либо на выбранный период в месяцах, либо
    // до конкретной даты, которую администратор вписал сам (until имеет
    // приоритет, если передано и то, и другое).
    async extendStudentAccess(id, { months = 3, until = '' } = {}) {
      const payload = until ? { until } : { months }
      const { data } = await client.post(`/admin/students/${id}/extend/`, payload)
      const idx = this.students.findIndex((s) => s.id === id)
      if (idx !== -1) this.students[idx] = data
      return data
    },
    async enrollStudent(id, courseId) {
      const { data } = await client.post(`/admin/students/${id}/enroll/`, { course_id: courseId })
      const idx = this.students.findIndex((s) => s.id === id)
      if (idx !== -1) this.students[idx] = data
      return data
    },
    async unenrollStudent(id, courseId) {
      const { data } = await client.delete(`/admin/students/${id}/enroll/`, { data: { course_id: courseId } })
      const idx = this.students.findIndex((s) => s.id === id)
      if (idx !== -1) this.students[idx] = data
      return data
    },
    // ===== Конструктор тренинга =====
    async fetchAdminCourses(params = {}) {
      const { data } = await client.get('/admin/courses/', { params })
      this.adminCourses = data
      return data
    },
    async createCourse(payload) {
      const { data } = await client.post('/admin/courses/create/', payload)
      await this.fetchAdminCourses()
      return data
    },
    async createModule(courseId, payload) {
      const { data } = await client.post(`/admin/courses/${courseId}/modules/`, payload)
      await this.fetchAdminCourses()
      return data
    },
    async updateModule(id, payload) {
      const { data } = await client.patch(`/admin/modules/${id}/`, payload)
      await this.fetchAdminCourses()
      return data
    },
    async deleteModule(id) {
      await client.delete(`/admin/modules/${id}/`)
      await this.fetchAdminCourses()
    },
    async createLesson(moduleId, payload) {
      const { data } = await client.post(`/admin/modules/${moduleId}/lessons/`, payload)
      await this.fetchAdminCourses()
      return data
    },
    async updateLesson(id, payload) {
      const { data } = await client.patch(`/admin/lessons/${id}/`, payload)
      await this.fetchAdminCourses()
      return data
    },
    async deleteLesson(id) {
      await client.delete(`/admin/lessons/${id}/`)
      await this.fetchAdminCourses()
    },
    async uploadLessonVideo(id, file) {
      const form = new FormData()
      form.append('video_file', file)
      const { data } = await client.patch(`/admin/lessons/${id}/`, form)
      await this.fetchAdminCourses()
      return data
    },
    async addMaterial(lessonId, { name, kind, file }) {
      const form = new FormData()
      form.append('name', name)
      form.append('kind', kind)
      form.append('file', file)
      const { data } = await client.post(`/admin/lessons/${lessonId}/materials/`, form)
      await this.fetchAdminCourses()
      return data
    },
    async deleteMaterial(id) {
      await client.delete(`/admin/materials/${id}/`)
      await this.fetchAdminCourses()
    },

    // ===== Библиотека материалов (все видео уроков + файлы уроков) =====
    async fetchMedia(params = {}) {
      const { data } = await client.get('/admin/media/', { params })
      this.media = data
      return data
    },
    async renameMaterial(id, name) {
      const { data } = await client.patch(`/admin/materials/${id}/`, { name })
      return data
    },
    async renameLessonVideo(lessonId, title) {
      const { data } = await client.patch(`/admin/lessons/${lessonId}/`, { title })
      return data
    },
    async deleteLessonVideo(lessonId) {
      await client.delete(`/admin/lessons/${lessonId}/video/`)
    },
    async trimLessonVideo(lessonId, start, end) {
      const { data } = await client.post(`/admin/lessons/${lessonId}/video/trim/`, { start, end })
      return data
    },

    // ===== Тесты =====
    async fetchTests(params = {}) {
      const { data } = await client.get('/admin/tests/', { params })
      this.tests = data
      return data
    },
    async fetchTestDetail(id) {
      const { data } = await client.get(`/admin/tests/${id}/`)
      return data
    },
    async createTest(payload) {
      const { data } = await client.post('/admin/tests/create/', payload)
      await this.fetchTests()
      return data
    },
    async updateTest(id, payload) {
      const { data } = await client.put(`/admin/tests/${id}/update/`, payload)
      await this.fetchTests()
      return data
    },
    async deleteTest(id) {
      await client.delete(`/admin/tests/${id}/update/`)
      await this.fetchTests()
    },

    async fetchStudentProgress(id) {
      const { data } = await client.get(`/admin/students/${id}/progress/`)
      return data
    },
    async fetchModuleStats() {
      const { data } = await client.get('/admin/analytics/modules/')
      this.moduleStats = data
      return data
    },

    // ===== История действий администратора =====
    async fetchAuditLog() {
      const { data } = await client.get('/admin/audit-log/')
      this.auditLog = data
      return data
    },
  },
})
