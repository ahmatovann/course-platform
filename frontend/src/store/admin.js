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
  }),
  actions: {
    async fetchStudents(params = {}) {
      const { data } = await client.get('/admin/students/', { params })
      this.students = data
      return data
    },
    async exportStudents() {
      const res = await client.get('/admin/students/export/', { responseType: 'blob' })
      downloadBlob(res.data, 'students.xlsx')
    },
    async exportStudentsPdf() {
      const res = await client.get('/admin/students/export-pdf/', { responseType: 'blob' })
      downloadBlob(res.data, 'students.pdf')
    },
    async exportStudentProgress(id, email) {
      const res = await client.get(`/admin/students/${id}/progress/export/`, { responseType: 'blob' })
      downloadBlob(res.data, `progress-${email || id}.xlsx`)
    },
    async exportStudentProgressPdf(id, email) {
      const res = await client.get(`/admin/students/${id}/progress/export-pdf/`, { responseType: 'blob' })
      downloadBlob(res.data, `progress-${email || id}.pdf`)
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
    async deleteStudent(id) {
      await client.delete(`/admin/students/${id}/delete/`)
      this.students = this.students.filter((student) => student.id !== id)
    },
    async fetchStudentActivity(id) {
      const { data } = await client.get(`/admin/students/${id}/activity/`)
      return data
    },
    async fetchAdminActivity() {
      const { data } = await client.get('/admin/activity/')
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
    // amount + unit ('day'/'week'/'month') — период выбирает администратор.
    async extendStudentAccess(id, amount, unit) {
      const { data } = await client.post(`/admin/students/${id}/extend/`, { amount, unit })
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
    async deleteCourse(id) {
      await client.delete(`/admin/courses/${id}/`)
      await this.fetchAdminCourses()
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
    // Прикрепить к уроку уже существующий материал/видео из раздела
    // «Материалы» вместо повторной загрузки того же файла. mediaId — это
    // item.id из fetchMedia(), например 'material-12' или 'video-5'.
    async attachMaterial(lessonId, mediaId) {
      const { data } = await client.post(`/admin/lessons/${lessonId}/materials/attach/`, { media_id: mediaId })
      await this.fetchAdminCourses()
      return data
    },

    // ===== Раздел «Материалы» (независимая библиотека + видео уроков) =====
    async fetchMedia(params = {}) {
      const { data } = await client.get('/admin/media/', { params })
      this.media = data
      return data
    },
    // Загрузить материал сразу в библиотеку, не привязывая к уроку.
    async uploadLibraryMaterial({ name, kind, file }) {
      const form = new FormData()
      form.append('name', name)
      form.append('kind', kind)
      form.append('file', file)
      const { data } = await client.post('/admin/materials/upload/', form)
      await this.fetchMedia()
      return data
    },
    async renameMaterial(id, name) {
      const { data } = await client.patch(`/admin/materials/${id}/`, { name })
      return data
    },
    // Заменить сам файл материала (и/или переименовать) — используется в
    // разделе «Материалы» для «изменить».
    async updateMaterial(id, { name, file }) {
      const form = new FormData()
      if (name !== undefined) form.append('name', name)
      if (file) form.append('file', file)
      const { data } = await client.patch(`/admin/materials/${id}/`, form)
      return data
    },
    async deleteLibraryMaterial(id) {
      await client.delete(`/admin/materials/${id}/`)
      await this.fetchMedia()
    },
    async renameLessonVideo(lessonId, title) {
      const { data } = await client.patch(`/admin/lessons/${lessonId}/`, { title })
      return data
    },
    async deleteLessonVideo(lessonId) {
      await client.delete(`/admin/lessons/${lessonId}/video/`)
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
  },
})
