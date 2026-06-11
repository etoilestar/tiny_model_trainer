import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/projects'
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('@/views/Projects.vue'),
    meta: { layout: true }
  },
  {
    path: '/projects/:id/datasets',
    name: 'Datasets',
    component: () => import('@/views/Datasets.vue'),
    meta: { layout: true }
  },
  {
    path: '/projects/:id/canvas',
    name: 'Canvas',
    component: () => import('@/views/Canvas.vue'),
    meta: { layout: true }
  },
  {
    path: '/projects/:id/jobs',
    name: 'TrainingJobs',
    component: () => import('@/views/TrainingJobs.vue'),
    meta: { layout: true }
  },
  {
    path: '/projects/:id/jobs/:jobId',
    name: 'JobDetail',
    component: () => import('@/views/JobDetail.vue'),
    meta: { layout: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
