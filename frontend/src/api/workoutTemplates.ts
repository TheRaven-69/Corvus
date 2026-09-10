import { apiRequestWithAuth } from './auth'
import type { Exercise } from './exercises'

export type TemplateSetInput = {
  position: number
  set_type: 'warmup' | 'working'
  target_reps: number
  target_weight_kg: string | null
}

export type TemplateExerciseInput = {
  exercise_id: string
  position: number
  notes: string | null
  sets: TemplateSetInput[]
}

export type TemplateInput = {
  name: string
  description: string | null
  exercises: TemplateExerciseInput[]
}

export type WorkoutTemplate = Omit<TemplateInput, 'exercises'> & {
  id: string
  created_at: string
  updated_at: string
  exercises: (Omit<TemplateExerciseInput, 'sets'> & {
    id: string
    exercise: Exercise
    sets: (TemplateSetInput & { id: string })[]
  })[]
}

export function getWorkoutTemplates(token: string) {
  return apiRequestWithAuth<WorkoutTemplate[]>('/workout-templates', token)
}

export function createWorkoutTemplate(token: string, data: TemplateInput) {
  return apiRequestWithAuth<WorkoutTemplate>('/workout-templates', token, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateWorkoutTemplate(
  token: string,
  id: string,
  data: Partial<TemplateInput>,
) {
  return apiRequestWithAuth<WorkoutTemplate>(
    `/workout-templates/${id}`,
    token,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    },
  )
}

export function deleteWorkoutTemplate(token: string, id: string) {
  return apiRequestWithAuth<void>(`/workout-templates/${id}`, token, {
    method: 'DELETE',
  })
}
