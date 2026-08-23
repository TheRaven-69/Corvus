import { apiRequestWithAuth } from './auth'

export type LocalizedNames = Partial<Record<'en' | 'uk', string>>

export type MuscleGroup = {
  code: string
  names: LocalizedNames
}

export type Exercise = {
  id: string
  code: string | null
  names: LocalizedNames
  muscle_groups: MuscleGroup[]
  created_at: string
  updated_at: string
}

export type ExerciseCreate = {
  name: string
  locale: 'en' | 'uk'
  muscle_group_codes: string[]
}

export function getExercises(accessToken: string) {
  return apiRequestWithAuth<Exercise[]>('/exercises', accessToken)
}

export function getMuscleGroups(accessToken: string) {
  return apiRequestWithAuth<MuscleGroup[]>('/muscle-groups', accessToken)
}

export function createExercise(
  accessToken: string,
  data: ExerciseCreate,
) {
  return apiRequestWithAuth<Exercise>('/exercises', accessToken, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
