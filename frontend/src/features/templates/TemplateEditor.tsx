import {
  BarbellIcon,
  CheckIcon,
  ArrowDownIcon,
  ArrowUpIcon,
  PlusIcon,
  TrashIcon,
} from '@phosphor-icons/react'
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
} from 'react'
import { useTranslation } from 'react-i18next'
import type { Exercise } from '../../api/exercises'
import type { TemplateInput, WorkoutTemplate } from '../../api/workoutTemplates'
import {
  draftInput,
  exerciseName,
  makeDraft,
  newSet,
  templateChanges,
  draftErrors,
  type DraftExercise,
} from './templateDraft'

type Props = {
  template?: WorkoutTemplate
  catalog: Exercise[]
  catalogLoading: boolean
  catalogError: boolean
  onRetryCatalog: () => void
  busy: boolean
  error: string | null
  onSave: (data: Partial<TemplateInput>) => Promise<void>
  onClose: () => void
  onDirtyChange: (dirty: boolean) => void
}

export function TemplateEditor({
  template,
  catalog,
  catalogLoading,
  catalogError,
  onRetryCatalog,
  busy,
  error,
  onSave,
  onClose,
  onDirtyChange,
}: Props) {
  const { t, i18n } = useTranslation()
  const [initial] = useState(() => makeDraft(template))
  const [draft, setDraft] = useState(initial)
  const [query, setQuery] = useState('')
  const [validationAttempt, setValidationAttempt] = useState(0)
  const [announcement, setAnnouncement] = useState('')
  const formRef = useRef<HTMLFormElement>(null)
  const pendingFocus = useRef<string | null>(null)
  const nameRef = useRef<HTMLInputElement>(null)
  const errors = validationAttempt ? draftErrors(draft) : []
  useLayoutEffect(() => {
    if (!pendingFocus.current) return
    const field = formRef.current?.elements.namedItem(pendingFocus.current)
    if (field instanceof HTMLElement) field.focus()
    pendingFocus.current = null
  })
  function errorProps(fieldId: string) {
    const invalid = errors.some((error) => error.fieldId === fieldId)
    return {
      id: fieldId,
      'aria-invalid': invalid || undefined,
      'aria-describedby': invalid ? `${fieldId}-error` : undefined,
    }
  }
  function fieldError(fieldId: string) {
    const error = errors.find((error) => error.fieldId === fieldId)
    return error ? (
      <span className="template-field-error" id={`${fieldId}-error`}>
        {t(error.message)}
      </span>
    ) : null
  }
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial)
  useEffect(() => {
    nameRef.current?.focus()
  }, [])
  useEffect(() => {
    onDirtyChange(dirty)
  }, [dirty, onDirtyChange])
  useEffect(() => () => onDirtyChange(false), [onDirtyChange])

  function changeExercise(
    key: string,
    update: (item: DraftExercise) => DraftExercise,
  ) {
    setDraft((current) => ({
      ...current,
      exercises: current.exercises.map((item) =>
        item.key === key ? update(item) : item,
      ),
    }))
  }
  function moveExercise(index: number, direction: number) {
    pendingFocus.current = `notes-${draft.exercises[index].key}`
    setDraft((current) => {
      const exercises = [...current.exercises]
      ;[exercises[index], exercises[index + direction]] = [
        exercises[index + direction],
        exercises[index],
      ]
      return { ...current, exercises }
    })
  }
  function removeExercise(index: number) {
    const item = draft.exercises[index]
    const next = draft.exercises[index + 1] ?? draft.exercises[index - 1]
    pendingFocus.current = next
      ? `notes-${next.key}`
      : 'template-exercise-search'
    setAnnouncement(
      t('templates.exerciseRemoved', {
        name: exerciseName(item.exercise, i18n.resolvedLanguage ?? 'en'),
      }),
    )
    setDraft((current) => ({
      ...current,
      exercises: current.exercises.filter((ex) => ex.key !== item.key),
    }))
  }
  function removeSet(item: DraftExercise, setIndex: number) {
    const next = item.sets[setIndex + 1] ?? item.sets[setIndex - 1]
    pendingFocus.current = next
      ? `reps-${item.key}-${next.key}`
      : `add-set-${item.key}`
    setAnnouncement(
      t('templates.setRemoved', {
        set: setIndex + 1,
        name: exerciseName(item.exercise, i18n.resolvedLanguage ?? 'en'),
      }),
    )
    changeExercise(item.key, (ex) => ({
      ...ex,
      sets: ex.sets.filter((set) => set.key !== item.sets[setIndex].key),
    }))
  }
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    const issues = draftErrors(draft)
    setValidationAttempt((value) => value + 1)
    if (issues.length) {
      pendingFocus.current = issues[0].fieldId
      return
    }
    const data = template ? templateChanges(initial, draft) : draftInput(draft)
    if (Object.keys(data).length === 0) {
      onClose()
      return
    }
    await onSave(data)
  }
  const language = i18n.resolvedLanguage ?? 'en'
  const options = catalog.filter((item) =>
    Object.values(item.names).some((name) =>
      name?.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()),
    ),
  )

  return (
    <form
      ref={formRef}
      noValidate
      className="template-editor"
      onSubmit={submit}
      aria-labelledby="template-editor-title"
    >
      <div className="template-editor__heading">
        <div>
          <h2 id="template-editor-title">
            {t(template ? 'templates.edit' : 'templates.create')}
          </h2>
          <p>{t('templates.editorHint')}</p>
        </div>
        <button type="button" onClick={onClose} disabled={busy}>
          {t('templates.cancel')}
        </button>
      </div>
      <fieldset disabled={busy} className="template-editor__fields">
        <div className="template-metadata">
          <label>
            {t('templates.name')}
            <input
              {...errorProps('template-name')}
              aria-label={t('templates.name')}
              ref={nameRef}
              value={draft.name}
              maxLength={120}
              required
              onChange={(event) =>
                setDraft({ ...draft, name: event.target.value })
              }
            />
            {fieldError('template-name')}
          </label>
          <label>
            {t('templates.description')}
            <textarea
              rows={2}
              value={draft.description}
              onChange={(event) =>
                setDraft({ ...draft, description: event.target.value })
              }
            />
          </label>
        </div>
        <div className="template-builder">
          <section
            className="template-plan"
            aria-labelledby="template-plan-title"
          >
            <div className="template-plan__heading">
              <h3 id="template-plan-title">{t('templates.exercises')}</h3>
              <span>
                {t('templates.exerciseCount', {
                  count: draft.exercises.length,
                })}
              </span>
            </div>
            {draft.exercises.length === 0 && (
              <div className="template-plan__empty">
                <BarbellIcon size={40} aria-hidden="true" />
                <h4>{t('templates.buildStart')}</h4>
                <p>{t('templates.addHint')}</p>
                <button
                  type="button"
                  onClick={() => {
                    const field = formRef.current?.elements.namedItem(
                      'template-exercise-search',
                    )
                    if (field instanceof HTMLElement) field.focus()
                  }}
                >
                  <PlusIcon size={18} aria-hidden="true" />
                  {t('templates.addExercise')}
                </button>
              </div>
            )}
            <ol className="template-draft-exercises">
              {draft.exercises.map((item, index) => (
                <li key={item.key} className="template-draft-exercise">
                  <div className="template-exercise-heading">
                    <h4>
                      <span>{String(index + 1).padStart(2, '0')}</span>
                      {exerciseName(item.exercise, language)}
                    </h4>
                    <div className="template-order-actions">
                      <button
                        type="button"
                        aria-label={t('templates.moveUp', {
                          name: exerciseName(item.exercise, language),
                        })}
                        disabled={index === 0}
                        onClick={() => moveExercise(index, -1)}
                      >
                        <ArrowUpIcon size={18} />
                      </button>
                      <button
                        type="button"
                        aria-label={t('templates.moveDown', {
                          name: exerciseName(item.exercise, language),
                        })}
                        disabled={index === draft.exercises.length - 1}
                        onClick={() => moveExercise(index, 1)}
                      >
                        <ArrowDownIcon size={18} />
                      </button>
                      <button
                        type="button"
                        aria-label={t('templates.removeExercise', {
                          name: exerciseName(item.exercise, language),
                        })}
                        onClick={() => removeExercise(index)}
                      >
                        <TrashIcon size={18} />
                      </button>
                    </div>
                  </div>
                  <ol className="template-sets">
                    {item.sets.map((set, setIndex) => (
                      <li key={set.key} className="template-set">
                        <span className="template-set__number">
                          {setIndex + 1}
                        </span>
                        <label className="template-set__type">
                          {t('templates.setType')}
                          <select
                            aria-label={t('templates.setTypeLabel', {
                              exercise: index + 1,
                              set: setIndex + 1,
                            })}
                            value={set.type}
                            onChange={(event) =>
                              changeExercise(item.key, (ex) => ({
                                ...ex,
                                sets: ex.sets.map((s) =>
                                  s.key === set.key
                                    ? {
                                        ...s,
                                        type: event.target.value as
                                          'warmup' | 'working',
                                      }
                                    : s,
                                ),
                              }))
                            }
                          >
                            <option value="warmup">
                              {t('templates.warmup')}
                            </option>
                            <option value="working">
                              {t('templates.working')}
                            </option>
                          </select>
                        </label>
                        <label className="template-set__reps">
                          {t('templates.reps')}
                          <input
                            {...errorProps(`reps-${item.key}-${set.key}`)}
                            aria-label={t('templates.repsLabel', {
                              exercise: index + 1,
                              set: setIndex + 1,
                            })}
                            type="number"
                            inputMode="numeric"
                            min="1"
                            step="1"
                            required
                            value={set.reps}
                            onChange={(event) =>
                              changeExercise(item.key, (ex) => ({
                                ...ex,
                                sets: ex.sets.map((s) =>
                                  s.key === set.key
                                    ? { ...s, reps: event.target.value }
                                    : s,
                                ),
                              }))
                            }
                          />
                          {fieldError(`reps-${item.key}-${set.key}`)}
                        </label>
                        <label className="template-set__weight">
                          {t('templates.weight')}
                          <input
                            {...errorProps(`weight-${item.key}-${set.key}`)}
                            aria-label={t('templates.weightLabel', {
                              exercise: index + 1,
                              set: setIndex + 1,
                            })}
                            type="text"
                            inputMode="decimal"
                            placeholder="—"
                            value={set.weight}
                            onChange={(event) =>
                              changeExercise(item.key, (ex) => ({
                                ...ex,
                                sets: ex.sets.map((s) =>
                                  s.key === set.key
                                    ? { ...s, weight: event.target.value }
                                    : s,
                                ),
                              }))
                            }
                          />
                          {fieldError(`weight-${item.key}-${set.key}`)}
                        </label>
                        <button
                          type="button"
                          aria-label={t('templates.removeSet', {
                            exercise: index + 1,
                            set: setIndex + 1,
                          })}
                          disabled={item.sets.length === 1}
                          onClick={() => removeSet(item, setIndex)}
                        >
                          <TrashIcon size={17} />
                        </button>
                      </li>
                    ))}
                  </ol>
                  <button
                    id={`add-set-${item.key}`}
                    type="button"
                    onClick={() =>
                      changeExercise(item.key, (ex) => ({
                        ...ex,
                        sets: [...ex.sets, newSet()],
                      }))
                    }
                  >
                    <PlusIcon size={16} />
                    {t('templates.addSet')}
                  </button>
                  <label className="template-notes">
                    {t('templates.notes')}
                    <input
                      id={`notes-${item.key}`}
                      value={item.notes}
                      onChange={(event) =>
                        changeExercise(item.key, (ex) => ({
                          ...ex,
                          notes: event.target.value,
                        }))
                      }
                    />
                  </label>
                </li>
              ))}
            </ol>
          </section>
          <section
            className="template-picker"
            aria-label={t('templates.addExercise')}
          >
            <h3>{t('templates.catalogTitle')}</h3>
            <p>{t('templates.catalogHint')}</p>
            <label>
              {t('templates.addExercise')}
              <input
                {...errorProps('template-exercise-search')}
                aria-label={t('templates.addExercise')}
                type="search"
                value={query}
                placeholder={t('templates.search')}
                onChange={(event) => setQuery(event.target.value)}
              />
              {fieldError('template-exercise-search')}
            </label>
            {catalogLoading ? (
              <p role="status">{t('templates.loadingExercises')}</p>
            ) : catalogError ? (
              <div role="alert">
                <p>{t('templates.catalogError')}</p>
                <button type="button" onClick={onRetryCatalog}>
                  {t('templates.retry')}
                </button>
              </div>
            ) : (
              <>
                <ul>
                  {options.map((item) => (
                    <li key={item.id}>
                      <button
                        aria-label={t('templates.addNamed', {
                          name: exerciseName(item, language),
                        })}
                        type="button"
                        onClick={() =>
                          setDraft((current) => ({
                            ...current,
                            exercises: [
                              ...current.exercises,
                              {
                                key: crypto.randomUUID(),
                                exercise: item,
                                notes: '',
                                sets: [newSet()],
                              },
                            ],
                          }))
                        }
                      >
                        <span>{exerciseName(item, language)}</span>
                        {draft.exercises.some(
                          (entry) => entry.exercise.id === item.id,
                        ) ? (
                          <CheckIcon size={18} aria-hidden="true" />
                        ) : (
                          <PlusIcon size={18} aria-hidden="true" />
                        )}
                        <span className="sr-only">
                          {' '}
                          {t('templates.addExercise')}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
                {options.length === 0 && (
                  <p>
                    {t(
                      catalog.length === 0
                        ? 'templates.noExercises'
                        : 'templates.noMatches',
                    )}
                  </p>
                )}
              </>
            )}
          </section>
        </div>
        <p className="template-hint">{t('templates.weightHint')}</p>
        {errors.length > 0 && (
          <p role="alert" className="template-error">
            {t('templates.validation.summary')}
          </p>
        )}
        {error && (
          <p role="alert" className="template-error">
            {error}
          </p>
        )}
        <div className="template-save">
          <div className="template-save__summary">
            <strong>{draft.name.trim() || t('templates.create')}</strong>
            <span>
              {t('templates.exerciseCount', { count: draft.exercises.length })}{' '}
              ·{' '}
              {t('templates.setCount', {
                count: draft.exercises.reduce(
                  (total, item) => total + item.sets.length,
                  0,
                ),
              })}
            </span>
          </div>
          <button className="template-button--gold" type="submit">
            {t(busy ? 'templates.saving' : 'templates.save')}
          </button>
        </div>
      </fieldset>
      <p className="sr-only" role="status">
        {announcement}
      </p>
    </form>
  )
}
