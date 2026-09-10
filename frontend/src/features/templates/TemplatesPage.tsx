import {
  PencilSimpleIcon,
  PlusIcon,
  TrashIcon,
  ArrowRightIcon,
} from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getExercises, type Exercise } from '../../api/exercises'
import { ApiError } from '../../api/http'
import {
  createWorkoutTemplate,
  deleteWorkoutTemplate,
  getWorkoutTemplates,
  updateWorkoutTemplate,
  type TemplateInput,
  type WorkoutTemplate,
} from '../../api/workoutTemplates'
import { TemplateEditor } from './TemplateEditor'
import { exerciseName } from './templateDraft'
import './TemplatesPage.css'

type Props = {
  accessToken: string
  onAccessTokenChange: (token: string) => void
  onSessionExpired: () => void
  onDirtyChange: (dirty: boolean) => void
  onBusyChange: (busy: boolean) => void
}

export function TemplatesPage({
  accessToken,
  onAccessTokenChange,
  onSessionExpired,
  onDirtyChange,
  onBusyChange,
}: Props) {
  const { t, i18n } = useTranslation()
  const [templates, setTemplates] = useState<WorkoutTemplate[]>([])
  const [catalog, setCatalog] = useState<Exercise[]>([])
  const [loading, setLoading] = useState(true)
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState(false)
  const [loadError, setLoadError] = useState(false)
  const [errorKey, setErrorKey] = useState<string | null>(null)
  const [messageKey, setMessageKey] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const [catalogReload, setCatalogReload] = useState(0)
  const [editor, setEditor] = useState<WorkoutTemplate | 'new' | null>(null)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const createButton = useRef<HTMLButtonElement>(null)
  const mutationPending = useRef(false)
  const returnFocus = useRef(false)
  const language = i18n.resolvedLanguage ?? 'en'

  useEffect(() => {
    if (returnFocus.current && !editor && !busy && !loading) {
      createButton.current?.focus()
      returnFocus.current = false
    }
  }, [editor, busy, loading])

  useEffect(() => {
    onDirtyChange(dirty)
  }, [dirty, onDirtyChange])
  useEffect(() => {
    onBusyChange(busy)
  }, [busy, onBusyChange])
  useEffect(
    () => () => {
      onDirtyChange(false)
      onBusyChange(false)
    },
    [onDirtyChange, onBusyChange],
  )

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setLoadError(false)
    void getWorkoutTemplates(accessToken)
      .then((result) => {
        if (cancelled) return
        setTemplates(result.data)
        if (result.accessToken !== accessToken)
          onAccessTokenChange(result.accessToken)
      })
      .catch((error) => {
        if (cancelled) return
        if (error instanceof ApiError && error.status === 401)
          onSessionExpired()
        else setLoadError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [accessToken, onAccessTokenChange, onSessionExpired, reload])

  useEffect(() => {
    let cancelled = false
    setCatalogLoading(true)
    setCatalogError(false)
    void getExercises(accessToken)
      .then((result) => {
        if (cancelled) return
        setCatalog(result.data)
        if (result.accessToken !== accessToken)
          onAccessTokenChange(result.accessToken)
      })
      .catch((error) => {
        if (cancelled) return
        if (error instanceof ApiError && error.status === 401)
          onSessionExpired()
        else setCatalogError(true)
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [accessToken, onAccessTokenChange, onSessionExpired, catalogReload])

  function closeEditor() {
    if (
      mutationPending.current ||
      (dirty && !window.confirm(t('templates.discard')))
    )
      return
    setEditor(null)
    setDirty(false)
    setErrorKey(null)
    returnFocus.current = true
  }
  function handleError(error: unknown) {
    if (error instanceof ApiError && error.status === 401) {
      onSessionExpired()
      return
    }
    setErrorKey(
      error instanceof ApiError && error.status === 404
        ? 'templates.notFound'
        : error instanceof ApiError && error.status === 422
          ? 'templates.invalidServer'
          : error instanceof ApiError && error.status === 403
            ? 'templates.forbidden'
            : 'templates.requestError',
    )
  }
  async function save(data: Partial<TemplateInput>) {
    if (!editor || mutationPending.current) return
    mutationPending.current = true
    setBusy(true)
    setErrorKey(null)
    setMessageKey(null)
    try {
      const result =
        editor === 'new'
          ? await createWorkoutTemplate(accessToken, data as TemplateInput)
          : await updateWorkoutTemplate(accessToken, editor.id, data)
      setTemplates((current) =>
        editor === 'new'
          ? [result.data, ...current]
          : current.map((item) =>
              item.id === result.data.id ? result.data : item,
            ),
      )
      setEditor(null)
      setDirty(false)
      setMessageKey('templates.saved')
      if (result.accessToken !== accessToken)
        onAccessTokenChange(result.accessToken)
      returnFocus.current = true
    } catch (error) {
      handleError(error)
    } finally {
      mutationPending.current = false
      setBusy(false)
    }
  }
  async function remove(id: string) {
    if (mutationPending.current) return
    mutationPending.current = true
    setBusy(true)
    setErrorKey(null)
    setMessageKey(null)
    try {
      const result = await deleteWorkoutTemplate(accessToken, id)
      setTemplates((current) => current.filter((item) => item.id !== id))
      setDeleteId(null)
      setMessageKey('templates.deleted')
      if (result.accessToken !== accessToken)
        onAccessTokenChange(result.accessToken)
      returnFocus.current = true
    } catch (error) {
      handleError(error)
    } finally {
      mutationPending.current = false
      setBusy(false)
    }
  }

  return (
    <section className="templates-page" aria-label={t('templates.title')}>
      <div className="templates-toolbar">
        <p>{t('templates.intro')}</p>
        <button
          ref={createButton}
          type="button"
          className="template-button--dark"
          disabled={!!editor || busy || loading}
          onClick={() => {
            setEditor('new')
            setErrorKey(null)
            setMessageKey(null)
            setDeleteId(null)
          }}
        >
          <PlusIcon size={18} aria-hidden="true" />
          {t('templates.create')}
        </button>
      </div>
      {messageKey && (
        <p className="template-status" role="status">
          {t(messageKey)}
        </p>
      )}
      {editor ? (
        <TemplateEditor
          key={editor === 'new' ? 'new' : editor.id}
          template={editor === 'new' ? undefined : editor}
          catalog={catalog}
          catalogLoading={catalogLoading}
          catalogError={catalogError}
          onRetryCatalog={() => setCatalogReload((value) => value + 1)}
          busy={busy}
          error={errorKey ? t(errorKey) : null}
          onSave={save}
          onClose={closeEditor}
          onDirtyChange={setDirty}
        />
      ) : (
        <>
          {errorKey && (
            <p className="template-error" role="alert">
              {t(errorKey)}
            </p>
          )}
          {loading ? (
            <p className="template-state" role="status">
              {t('templates.loading')}
            </p>
          ) : loadError ? (
            <div className="template-state" role="alert">
              <h2>{t('templates.loadError')}</h2>
              <button
                type="button"
                onClick={() => setReload((value) => value + 1)}
              >
                {t('templates.retry')}
              </button>
            </div>
          ) : templates.length === 0 ? (
            <div className="template-state">
              <h2>{t('templates.empty')}</h2>
              <p>{t('templates.emptyHint')}</p>
              <button
                type="button"
                className="template-button--gold"
                onClick={() => setEditor('new')}
              >
                {t('templates.create')}
              </button>
            </div>
          ) : (
            <div className="template-grid">
              {templates.map((template) => (
                <article className="template-card" key={template.id}>
                  <header>
                    <span>{t('templates.template')}</span>
                    <h2>{template.name}</h2>
                  </header>
                  <div className="template-card__body">
                    {template.description && (
                      <p className="template-description">
                        {template.description}
                      </p>
                    )}
                    <ol className="template-card__exercises">
                      {template.exercises
                        .toSorted((a, b) => a.position - b.position)
                        .map((item, index) => (
                          <li key={item.id}>
                            <span>{String(index + 1).padStart(2, '0')}</span>
                            <div>
                              <strong>
                                {exerciseName(item.exercise, language)}
                              </strong>
                              <p>
                                {t('templates.setCount', {
                                  count: item.sets.length,
                                })}
                              </p>
                            </div>
                          </li>
                        ))}
                    </ol>
                    <p className="template-card__summary">
                      {t('templates.exerciseCount', {
                        count: template.exercises.length,
                      })}
                    </p>
                    <div className="template-card__actions">
                      <button
                        type="button"
                        className="template-button--gold"
                        disabled
                        title={t('templates.sessionSoon')}
                      >
                        {t('templates.startSoon')}
                        <ArrowRightIcon size={18} aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setEditor(template)
                          setErrorKey(null)
                          setMessageKey(null)
                          setDeleteId(null)
                        }}
                        aria-label={t('templates.editNamed', {
                          name: template.name,
                        })}
                      >
                        <PencilSimpleIcon size={18} aria-hidden="true" />
                        {t('templates.edit')}
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        aria-label={t('templates.deleteNamed', {
                          name: template.name,
                        })}
                        onClick={() => {
                          setDeleteId(template.id)
                          setErrorKey(null)
                        }}
                      >
                        <TrashIcon size={18} aria-hidden="true" />
                      </button>
                    </div>
                    {deleteId === template.id && (
                      <div
                        className="template-delete"
                        role="group"
                        aria-label={t('templates.deleteNamed', {
                          name: template.name,
                        })}
                      >
                        <p>
                          {t('templates.deleteConfirm', {
                            name: template.name,
                          })}
                        </p>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void remove(template.id)}
                        >
                          {t(
                            busy
                              ? 'templates.deleting'
                              : 'templates.confirmDelete',
                          )}
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => setDeleteId(null)}
                        >
                          {t('templates.cancel')}
                        </button>
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
          <aside className="template-quick-start">
            <div>
              <h2>{t('templates.quickStart')}</h2>
              <p>{t('templates.sessionSoon')}</p>
            </div>
            <button type="button" disabled>
              {t('templates.emptyWorkout')}
              <ArrowRightIcon size={18} aria-hidden="true" />
            </button>
          </aside>
        </>
      )}
    </section>
  )
}
