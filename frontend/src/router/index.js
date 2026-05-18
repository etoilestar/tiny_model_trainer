import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/projects'
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('@/views/Projects.vue'),
    meta: { requiresAuth: true, layout: true }
  },
  {
    path: '/projects/:id/datasets',
    name: 'Datasets',
    component: () => import('@/views/Datasets.vue'),
    meta: { requiresAuth: true, layout: true }
  },
  {
    path: '/projects/:id/canvas',
    name: 'Canvas',
    component: () => import('@/views/Canvas.vue'),
    meta: { requiresAuth: true, layout: true }
  },
  {
    path: '/projects/:id/jobs',
    name: 'TrainingJobs',
    component: () => import('@/views/TrainingJobs.vue'),
    meta: { requiresAuth: true, layout: true }
  },
  {
    path: '/projects/:id/jobs/:jobId',
    name: 'JobDetail',
    component: () => import('@/views/JobDetail.vue'),
    meta: { requiresAuth: true, layout: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (!to.meta.requiresAuth && token && (to.name === 'Login' || to.name === 'Register')) {
    next('/projects')
  } else {
    next()
  }
})

export default router
