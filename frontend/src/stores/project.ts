import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { projectService } from '@/services'
import type { Project } from '@/types'

const CURRENT_KEY = 'flowtina_current_project'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProjectId = ref<string | null>(localStorage.getItem(CURRENT_KEY))
  const loading = ref(false)

  const currentProject = computed(
    () => projects.value.find((p) => p.id === currentProjectId.value) ?? null,
  )

  async function fetchProjects(): Promise<void> {
    loading.value = true
    try {
      projects.value = await projectService.list()
      if (
        (!currentProjectId.value ||
          !projects.value.some((p) => p.id === currentProjectId.value)) &&
        projects.value.length > 0
      ) {
        select(projects.value[0].id)
      }
    } finally {
      loading.value = false
    }
  }

  function select(id: string): void {
    currentProjectId.value = id
    localStorage.setItem(CURRENT_KEY, id)
  }

  async function createProject(name: string, description: string): Promise<Project> {
    const project = await projectService.create({ name, description })
    projects.value.push(project)
    if (!currentProjectId.value) select(project.id)
    return project
  }

  async function updateProject(
    id: string,
    payload: Partial<{ name: string; description: string; active: boolean }>,
  ): Promise<Project> {
    const updated = await projectService.update(id, payload)
    const idx = projects.value.findIndex((p) => p.id === id)
    if (idx !== -1) projects.value[idx] = updated
    return updated
  }

  async function deleteProject(id: string): Promise<void> {
    await projectService.remove(id)
    projects.value = projects.value.filter((p) => p.id !== id)
    if (currentProjectId.value === id) {
      const next = projects.value[0]?.id ?? null
      currentProjectId.value = next
      if (next) localStorage.setItem(CURRENT_KEY, next)
      else localStorage.removeItem(CURRENT_KEY)
    }
  }

  function reset(): void {
    projects.value = []
    currentProjectId.value = null
    localStorage.removeItem(CURRENT_KEY)
  }

  return {
    projects,
    currentProjectId,
    currentProject,
    loading,
    fetchProjects,
    select,
    createProject,
    updateProject,
    deleteProject,
    reset,
  }
})
