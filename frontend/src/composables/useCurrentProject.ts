import { computed } from 'vue'
import { useProjectStore } from '@/stores/project'

/**
 * Provides the current project id and a guard flag for project-scoped pages.
 */
export function useCurrentProject() {
  const projectStore = useProjectStore()
  const projectId = computed(() => projectStore.currentProjectId)
  const hasProject = computed(() => !!projectStore.currentProjectId)
  return { projectId, hasProject, projectStore }
}
