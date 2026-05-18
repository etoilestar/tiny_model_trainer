import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = (data) => api.post('/auth/login', data)
export const register = (data) => api.post('/auth/register', data)
export const getMe = () => api.get('/auth/me')

// Projects
export const getProjects = () => api.get('/projects')
export const createProject = (data) => api.post('/projects', data)
export const updateProject = (id, data) => api.put(`/projects/${id}`, data)
export const deleteProject = (id) => api.delete(`/projects/${id}`)

// Datasets
export const getDatasets = (projectId) => api.get(`/datasets?project_id=${projectId}`)
export const uploadDataset = (formData) => api.post('/datasets', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
export const deleteDataset = (id) => api.delete(`/datasets/${id}`)

// Workflows
export const getWorkflows = (projectId) => api.get(`/workflows?project_id=${projectId}`)
export const createWorkflow = (data) => api.post('/workflows', data)
export const getWorkflow = (id) => api.get(`/workflows/${id}`)
export const updateWorkflow = (id, data) => api.put(`/workflows/${id}`, data)

// Training
export const getJobs = (projectId) => api.get(`/training/jobs?project_id=${projectId}`)
export const createJob = (data) => api.post('/training/jobs', data)
export const getJob = (id) => api.get(`/training/jobs/${id}`)
export const stopJob = (id) => api.post(`/training/jobs/${id}/stop`)
export const getJobLogs = (id) => api.get(`/training/jobs/${id}/logs`)

// Metrics
export const getMetrics = (jobId) => api.get(`/metrics?job_id=${jobId}`)

export default api
