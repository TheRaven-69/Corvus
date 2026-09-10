import type { Exercise } from '../../api/exercises'
import type { TemplateInput, WorkoutTemplate } from '../../api/workoutTemplates'

export type DraftSet = {
  key: string
  type: 'warmup' | 'working'
  reps: string
  weight: string
}
export type DraftExercise = {
  key: string
  exercise: Exercise
  notes: string
  sets: DraftSet[]
}
export type TemplateDraft = {
  name: string
  description: string
  exercises: DraftExercise[]
}

export function newSet(): DraftSet {
  return { key: crypto.randomUUID(), type: 'working', reps: '8', weight: '' }
}

export function makeDraft(template?: WorkoutTemplate): TemplateDraft {
  return {
    name: template?.name ?? '',
    description: template?.description ?? '',
    exercises:
      template?.exercises
        .toSorted((a, b) => a.position - b.position)
        .map((item) => ({
          key: item.id,
          exercise: item.exercise,
          notes: item.notes ?? '',
          sets: item.sets
            .toSorted((a, b) => a.position - b.position)
            .map((set) => ({
              key: set.id,
              type: set.set_type,
              reps: String(set.target_reps),
              weight: set.target_weight_kg ?? '',
            })),
        })) ?? [],
  }
}

export function draftInput(draft: TemplateDraft): TemplateInput {
  return {
    name: draft.name.trim(),
    description: draft.description.trim() || null,
    exercises: draft.exercises.map((item, position) => ({
      exercise_id: item.exercise.id,
      position,
      notes: item.notes.trim() || null,
      sets: item.sets.map((set, index) => ({
        position: index,
        set_type: set.type,
        target_reps: Number(set.reps),
        target_weight_kg: set.weight.trim()
          ? set.weight.trim().replace(',', '.')
          : null,
      })),
    })),
  }
}

export type DraftError = { fieldId: string; message: string }

export function draftErrors(draft: TemplateDraft): DraftError[] {
  const errors: DraftError[] = []
  if (!draft.name.trim() || draft.name.trim().length > 120) {
    errors.push({
      fieldId: 'template-name',
      message: 'templates.validation.name',
    })
  }
  if (!draft.exercises.length) {
    errors.push({
      fieldId: 'template-exercise-search',
      message: 'templates.validation.exercises',
    })
  }
  for (const item of draft.exercises) {
    for (const set of item.sets) {
      if (
        !/^\d+$/.test(set.reps) ||
        !Number.isSafeInteger(Number(set.reps)) ||
        Number(set.reps) <= 0
      ) {
        errors.push({
          fieldId: `reps-${item.key}-${set.key}`,
          message: 'templates.validation.reps',
        })
      }
      const weight = set.weight.trim().replace(',', '.')
      if (
        weight &&
        (!/^\d+(\.\d{1,2})?$/.test(weight) || Number(weight) > 999999.99)
      ) {
        errors.push({
          fieldId: `weight-${item.key}-${set.key}`,
          message: 'templates.validation.weight',
        })
      }
    }
  }
  return errors
}

export function templateChanges(
  initial: TemplateDraft,
  next: TemplateDraft,
): Partial<TemplateInput> {
  const before = draftInput(initial)
  const after = draftInput(next)
  const changes: Partial<TemplateInput> = {}
  if (before.name !== after.name) changes.name = after.name
  if (before.description !== after.description)
    changes.description = after.description
  if (JSON.stringify(before.exercises) !== JSON.stringify(after.exercises))
    changes.exercises = after.exercises
  return changes
}

export function exerciseName(exercise: Exercise, language: string): string {
  return (
    exercise.names[language === 'uk' ? 'uk' : 'en'] ??
    exercise.names.en ??
    exercise.names.uk ??
    ''
  )
}
