import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue'), meta: { public: true } },
  { path: '/forgot-password', name: 'forgot-password', component: () => import('../views/auth/ForgotPasswordView.vue'), meta: { public: true } },
  { path: '/reset-password', name: 'reset-password', component: () => import('../views/auth/ResetPasswordView.vue'), meta: { public: true } },

  { path: '/', name: 'dashboard', component: () => import('../views/learner/DashboardView.vue'), meta: { role: 'student' } },
  { path: '/courses/:slug', name: 'course', component: () => import('../views/learner/CourseView.vue'), meta: { role: 'student' } },
  { path: '/modules/:id', name: 'module', component: () => import('../views/learner/ModuleView.vue'), meta: { role: 'student' } },
  { path: '/lessons/:id', name: 'lesson', component: () => import('../views/learner/LessonView.vue'), meta: { role: 'student' } },
  { path: '/tests/:id', name: 'test', component: () => import('../views/learner/TestView.vue'), meta: { role: 'student' } },
  { path: '/profile', name: 'profile', component: () => import('../views/learner/ProfileView.vue'), meta: { role: 'student' } },
  { path: '/my-tests', name: 'my-tests', component: () => import('../views/learner/MyTestsView.vue'), meta: { role: 'student' } },
  { path: '/chats', name: 'chats', component: () => import('../views/learner/ChatsView.vue'), meta: { role: 'student' } },
  { path: '/news', name: 'news', component: () => import('../views/learner/NewsView.vue'), meta: { role: 'student' } },

  { path: '/admin', redirect: '/admin/students' },
  { path: '/admin/students', name: 'admin-students', component: () => import('../views/admin/StudentsView.vue'), meta: { role: 'admin' } },
  { path: '/admin/courses', name: 'admin-courses', component: () => import('../views/admin/CoursesView.vue'), meta: { role: 'admin' } },
  { path: '/admin/materials', name: 'admin-materials', component: () => import('../views/admin/MediaLibraryView.vue'), meta: { role: 'admin' } },
  { path: '/admin/tests', name: 'admin-tests', component: () => import('../views/admin/TestsView.vue'), meta: { role: 'admin' } },
  { path: '/admin/progress', name: 'admin-progress', component: () => import('../views/admin/ProgressView.vue'), meta: { role: 'admin' } },
  { path: '/admin/chats', name: 'admin-chats', component: () => import('../views/admin/AdminChatsView.vue'), meta: { role: 'admin' } },
  { path: '/admin/news', name: 'admin-news', component: () => import('../views/admin/AdminNewsView.vue'), meta: { role: 'admin' } },
  { path: '/admin/settings', name: 'admin-settings', component: () => import('../views/admin/AdminSettingsView.vue'), meta: { role: 'admin' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.isAuthenticated) return auth.isAdmin ? '/admin/students' : '/'
    return true
  }
  if (!auth.isAuthenticated) return '/login'
  if (to.meta.role === 'admin' && !auth.isAdmin) return '/'
  if (to.meta.role === 'student' && auth.isAdmin) return '/admin/students'
  return true
})

export default router
