import {
  BarbellIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  WarningCircleIcon,
} from '@phosphor-icons/react'
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import {
  createExercise,
  getExercises,
  getMuscleGroups,
  type Exercise,
  type LocalizedNames,
  type MuscleGroup,
} from '../../api/exercises'
import { ApiError } from '../../api/http'
import type { SupportedLanguage } from '../../i18n'
import './ExercisesPage.css'

type ExercisesPageProps = {
  accessToken: string
  isFormOpen: boolean
  onAccessTokenChange: (accessToken: string) => void
  onFormOpenChange: (isOpen: boolean) => void
  onSessionExpired: () => void
}

function readableExerciseError(error: unknown, t: TFunction): string {
  if (error instanceof ApiError && error.status === 403) {
    return t('exercises.errors.forbidden')
  }

  if (error instanceof ApiError && error.status === 429) {
    return t('exercises.errors.rateLimited')
  }

  if (error instanceof ApiError && error.status === 422) {
    return t('exercises.errors.invalid')
  }

  if (error instanceof ApiError) {
    return t('exercises.errors.server')
  }

  return t('exercises.errors.connection')
}

function localizedName(
  names: LocalizedNames,
  language: SupportedLanguage,
): string {
  return names[language] ?? names.en ?? names.uk ?? Object.values(names)[0] ?? ''
}

function normalizeSearchText(
  value: string,
  language: SupportedLanguage,
): string {
  return value
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLocaleLowerCase(language)
    .replace(/['’ʼ`]/g, '')
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
}

export function ExercisesPage({
  accessToken,
  isFormOpen,
  onAccessTokenChange,
  onFormOpenChange,
  onSessionExpired,
}: ExercisesPageProps) {
  const { i18n, t } = useTranslation()
  const language: SupportedLanguage =
    i18n.resolvedLanguage === 'uk' ? 'uk' : 'en'
  const nameInputRef = useRef<HTMLInputElement>(null)
  const firstMuscleGroupInputRef = useRef<HTMLInputElement>(null)
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [muscleGroups, setMuscleGroups] = useState<MuscleGroup[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [reloadVersion, setReloadVersion] = useState(0)
  const [name, setName] = useState('')
  const [selectedMuscleGroups, setSelectedMuscleGroups] = useState<string[]>([])
  const [formError, setFormError] = useState<string | null>(null)
  const [muscleGroupError, setMuscleGroupError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    let isCancelled = false

    async function loadCatalog() {
      setIsLoading(true)
      setLoadError(null)

      try {
        const [exerciseResult, groupResult] = await Promise.all([
          getExercises(accessToken),
          getMuscleGroups(accessToken),
        ])

        if (isCancelled) {
          return
        }

        const refreshedAccessToken =
          exerciseResult.accessToken !== accessToken
            ? exerciseResult.accessToken
            : groupResult.accessToken
        setExercises(exerciseResult.data)
        setMuscleGroups(groupResult.data)

        if (refreshedAccessToken !== accessToken) {
          onAccessTokenChange(refreshedAccessToken)
        }
      } catch (error) {
        if (isCancelled) {
          return
        }

        if (error instanceof ApiError && error.status === 401) {
          onSessionExpired()
          return
        }

        setLoadError(readableExerciseError(error, t))
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadCatalog()

    return () => {
      isCancelled = true
    }
  }, [
    accessToken,
    onAccessTokenChange,
    onSessionExpired,
    reloadVersion,
    t,
  ])

  useEffect(() => {
    if (isFormOpen) {
      nameInputRef.current?.focus()
    }
  }, [isFormOpen])

  const filteredExercises = useMemo(() => {
    const searchTerms = normalizeSearchText(searchQuery, language)
      .split(/\s+/)
      .filter(Boolean)

    if (searchTerms.length === 0) {
      return exercises
    }

    return exercises.filter((exercise) => {
      const searchableText = normalizeSearchText(
        [
          ...Object.values(exercise.names),
          ...exercise.muscle_groups.flatMap((group) =>
            Object.values(group.names),
          ),
        ].join(' '),
        language,
      )

      return searchTerms.every((term) => searchableText.includes(term))
    })
  }, [exercises, language, searchQuery])
  const hasActiveSearch = searchQuery.trim().length > 0

  function toggleMuscleGroup(code: string) {
    setSelectedMuscleGroups((currentSelection) =>
      currentSelection.includes(code)
        ? currentSelection.filter((selectedCode) => selectedCode !== code)
        : [...currentSelection, code],
    )
    setMuscleGroupError(null)
    setFormError(null)
    setSuccessMessage(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    setMuscleGroupError(null)
    setSuccessMessage(null)

    const normalizedName = name.trim()

    if (!normalizedName) {
      setFormError(t('exercises.form.errors.name'))
      nameInputRef.current?.focus()
      return
    }

    if (selectedMuscleGroups.length === 0) {
      setMuscleGroupError(t('exercises.form.errors.muscleGroup'))
      firstMuscleGroupInputRef.current?.focus()
      return
    }

    setIsSubmitting(true)

    try {
      const result = await createExercise(accessToken, {
        name: normalizedName,
        locale: language,
        muscle_group_codes: selectedMuscleGroups,
      })

      setExercises((currentExercises) => [result.data, ...currentExercises])
      setName('')
      setSelectedMuscleGroups([])
      setSuccessMessage(t('exercises.form.success', { name: normalizedName }))

      if (result.accessToken !== accessToken) {
        onAccessTokenChange(result.accessToken)
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        onSessionExpired()
        return
      }

      setFormError(readableExerciseError(error, t))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className={
        isFormOpen
          ? 'exercise-workspace exercise-workspace--form-open'
          : 'exercise-workspace'
      }
    >
      <section className="exercise-catalog" aria-labelledby="exercise-catalog-title">
        <div className="exercise-toolbar">
          <div>
            <h2 id="exercise-catalog-title">{t('exercises.catalog.title')}</h2>
            <p aria-live="polite">
              {hasActiveSearch
                ? t('exercises.catalog.filteredCount', {
                    count: filteredExercises.length,
                    total: exercises.length,
                  })
                : t('exercises.catalog.count', { count: exercises.length })}
            </p>
          </div>

          <label className="exercise-search">
            <span className="sr-only">{t('exercises.search.label')}</span>
            <MagnifyingGlassIcon size={18} aria-hidden="true" />
            <input
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={t('exercises.search.placeholder')}
            />
          </label>
        </div>

        {isLoading ? (
          <div className="exercise-state" role="status">
            <span className="spinner" aria-hidden="true" />
            <strong>{t('exercises.loading.title')}</strong>
            <p>{t('exercises.loading.hint')}</p>
          </div>
        ) : loadError ? (
          <div className="exercise-state exercise-state--error" role="alert">
            <WarningCircleIcon size={26} aria-hidden="true" />
            <strong>{t('exercises.errors.loadTitle')}</strong>
            <p>{loadError}</p>
            <button type="button" onClick={() => setReloadVersion((value) => value + 1)}>
              {t('exercises.errors.retry')}
            </button>
          </div>
        ) : filteredExercises.length === 0 ? (
          <div className="exercise-state">
            <BarbellIcon size={28} aria-hidden="true" />
            <strong>
              {hasActiveSearch
                ? t('exercises.empty.searchTitle')
                : t('exercises.empty.title')}
            </strong>
            <p>
              {hasActiveSearch
                ? t('exercises.empty.searchHint')
                : t('exercises.empty.hint')}
            </p>
            {hasActiveSearch ? (
              <button type="button" onClick={() => setSearchQuery('')}>
                {t('exercises.empty.clearSearch')}
              </button>
            ) : (
              <button type="button" onClick={() => onFormOpenChange(true)}>
                <PlusIcon size={17} aria-hidden="true" />
                {t('exercises.empty.action')}
              </button>
            )}
          </div>
        ) : (
          <ul className="exercise-list">
            {filteredExercises.map((exercise) => (
              <li key={exercise.id}>
                <article className="exercise-row">
                  <div className="exercise-row__identity">
                    <span className="exercise-row__mark" aria-hidden="true">
                      <BarbellIcon size={19} />
                    </span>
                    <div>
                      <h3>{localizedName(exercise.names, language)}</h3>
                      <span>
                        {exercise.code
                          ? t('exercises.catalog.system')
                          : t('exercises.catalog.custom')}
                      </span>
                    </div>
                  </div>
                  <div className="exercise-row__groups" aria-label={t('exercises.catalog.muscleGroups')}>
                    {exercise.muscle_groups.map((group) => (
                      <span key={group.code}>
                        {localizedName(group.names, language)}
                      </span>
                    ))}
                  </div>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>

      {isFormOpen ? (
        <aside className="exercise-create" id="exercise-create-panel" aria-labelledby="exercise-create-title">
          <div className="exercise-create__heading">
            <div>
              <h2 id="exercise-create-title">{t('exercises.form.title')}</h2>
              <p>{t('exercises.form.hint')}</p>
            </div>
            <button
              className="exercise-create__close"
              type="button"
              onClick={() => onFormOpenChange(false)}
            >
              {t('exercises.form.close')}
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-field">
              <label htmlFor="exercise-name">{t('exercises.form.name')}</label>
              <input
                ref={nameInputRef}
                id="exercise-name"
                name="exerciseName"
                value={name}
                onChange={(event) => {
                  setName(event.target.value)
                  setFormError(null)
                  setSuccessMessage(null)
                }}
                maxLength={120}
                required
                aria-describedby="exercise-name-hint"
              />
              <span className="field-hint" id="exercise-name-hint">
                {t('exercises.form.nameHint', { language: language.toUpperCase() })}
              </span>
            </div>

            <fieldset
              className="muscle-group-fieldset"
              aria-describedby={`exercise-muscle-groups-hint${
                muscleGroupError ? ' exercise-muscle-groups-error' : ''
              }`}
              aria-invalid={muscleGroupError ? 'true' : undefined}
            >
              <legend>{t('exercises.form.muscleGroups')}</legend>
              <p id="exercise-muscle-groups-hint">
                {t('exercises.form.muscleGroupsHint')}
              </p>
              <div className="muscle-group-options">
                {muscleGroups.map((group, index) => (
                  <label key={group.code}>
                    <input
                      ref={index === 0 ? firstMuscleGroupInputRef : undefined}
                      type="checkbox"
                      value={group.code}
                      checked={selectedMuscleGroups.includes(group.code)}
                      onChange={() => toggleMuscleGroup(group.code)}
                    />
                    <span>{localizedName(group.names, language)}</span>
                  </label>
                ))}
              </div>
              {muscleGroupError ? (
                <p
                  className="form-error muscle-group-fieldset__error"
                  id="exercise-muscle-groups-error"
                  role="alert"
                >
                  {muscleGroupError}
                </p>
              ) : null}
            </fieldset>

            {muscleGroups.length === 0 ? (
              <p className="form-error" role="status">
                {t('exercises.form.errors.noMuscleGroups')}
              </p>
            ) : null}

            {formError ? (
              <p className="form-error" role="alert">
                {formError}
              </p>
            ) : null}

            {successMessage ? (
              <p className="form-success" role="status">
                {successMessage}
              </p>
            ) : null}

            <button className="submit-button" type="submit" disabled={isSubmitting || muscleGroups.length === 0}>
              {isSubmitting
                ? t('exercises.form.submitting')
                : t('exercises.form.submit')}
            </button>
          </form>
        </aside>
      ) : null}
    </div>
  )
}
