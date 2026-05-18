import { defineStore } from 'pinia'
import { getProjects, createProject, deleteProject, updateProject } from '@/api'

export const useProjectStore = defineStore('project', {
  state: () => ({
    projects: [],
    currentProject: null,
    loading: false
  }),
  actions: {
    async fetchProjects() {
      this.loading = true
      try {
        const res = await getProjects()
        this.projects = res?.data || res || []
      } finally {
        this.loading = false
      }
    },
    async addProject(data) {
      const res = await createProject(data)
      await this.fetchProjects()
      return res?.data || res
    },
    async editProject(id, data) {
      const res = await updateProject(id, data)
      await this.fetchProjects()
      return res?.data || res
    },
    async removeProject(id) {
      await deleteProject(id)
      this.projects = this.projects.filter(p => p.id !== id)
    },
    setCurrentProject(project) {
      this.currentProject = project
    }
  }
})
