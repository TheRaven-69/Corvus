import {
  BarbellIcon,
  CalendarBlankIcon,
  ChartLineUpIcon,
  ClockCounterClockwiseIcon,
  GearSixIcon,
  HouseLineIcon,
  MagnifyingGlassIcon,
  MedalIcon,
  NotebookIcon,
} from '@phosphor-icons/react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { User } from '../../api/auth'
import { CorvusBrand } from '../../components/CorvusBrand'
import { LanguageSwitcher } from '../../components/LanguageSwitcher'
import { ExercisesPage } from '../exercises/ExercisesPage'
import './Dashboard.css'

type DashboardProps = {
  accessToken: string
  currentUser: User
  isLoggingOut: boolean
  logoutError: string | null
  onAccessTokenChange: (accessToken: string) => void
  onLogout: () => void
  onSessionExpired: () => void
}

type DashboardView = 'dashboard' | 'exercises'

type IconName =
  | 'calendar'
  | 'dashboard'
  | 'dumbbell'
  | 'exercise'
  | 'history'
  | 'progress'
  | 'search'
  | 'settings'
  | 'achievement'

function Icon({ name }: { name: IconName }) {
  const icons = {
    calendar: CalendarBlankIcon,
    dashboard: HouseLineIcon,
    dumbbell: BarbellIcon,
    exercise: NotebookIcon,
    history: ClockCounterClockwiseIcon,
    progress: ChartLineUpIcon,
    search: MagnifyingGlassIcon,
    settings: GearSixIcon,
    achievement: MedalIcon,
  }
  const DashboardIcon = icons[name]

  return (
    <DashboardIcon
      className="dashboard-icon"
      size={20}
      weight={name === 'dashboard' ? 'bold' : 'regular'}
      aria-hidden="true"
    />
  )
}

const trainingLinks: Array<{
  icon: IconName
  translationKey: string
  view?: DashboardView
}> = [
  { icon: 'dumbbell', translationKey: 'dashboard.nav.workouts' },
  { icon: 'calendar', translationKey: 'dashboard.nav.templates' },
  {
    icon: 'exercise',
    translationKey: 'dashboard.nav.exercises',
    view: 'exercises',
  },
  { icon: 'history', translationKey: 'dashboard.nav.sessions' },
  { icon: 'history', translationKey: 'dashboard.nav.history' },
  { icon: 'progress', translationKey: 'dashboard.nav.progress' },
]

export function Dashboard({
  accessToken,
  currentUser,
  isLoggingOut,
  logoutError,
  onAccessTokenChange,
  onLogout,
  onSessionExpired,
}: DashboardProps) {
  const { t } = useTranslation()
  const [activeView, setActiveView] = useState<DashboardView>('dashboard')
  const [isExerciseFormOpen, setIsExerciseFormOpen] = useState(false)
  const volumeScale = t('dashboard.volume.scale', { returnObjects: true }) as string[]
  const weekDays = t('dashboard.volume.days', { returnObjects: true }) as string[]

  return (
    <div className="fitness-dashboard">
      <aside className="fitness-sidebar">
        <div className="fitness-brand"><CorvusBrand compact /></div>

        <nav className="fitness-nav" aria-label={t('dashboard.navLabel')}>
          <button
            className={
              activeView === 'dashboard'
                ? 'fitness-nav__link fitness-nav__link--active'
                : 'fitness-nav__link'
            }
            type="button"
            aria-current={activeView === 'dashboard' ? 'page' : undefined}
            onClick={() => setActiveView('dashboard')}
          >
            <Icon name="dashboard" />
            {t('dashboard.nav.dashboard')}
          </button>

          <p className="fitness-nav__label">{t('dashboard.nav.training')}</p>
          {trainingLinks.map((link) =>
            link.view ? (
              <button
                className={
                  activeView === link.view
                    ? 'fitness-nav__link fitness-nav__link--active'
                    : 'fitness-nav__link'
                }
                type="button"
                aria-current={activeView === link.view ? 'page' : undefined}
                key={link.translationKey}
                onClick={() => setActiveView(link.view ?? 'dashboard')}
              >
                <Icon name={link.icon} />
                {t(link.translationKey)}
              </button>
            ) : (
              <span
                className="fitness-nav__link fitness-nav__link--disabled"
                aria-disabled="true"
                key={link.translationKey}
              >
                <Icon name={link.icon} />
                {t(link.translationKey)}
              </span>
            ),
          )}
        </nav>

        <div className="fitness-sidebar__footer">
          <span className="fitness-nav__link fitness-nav__link--disabled" aria-disabled="true">
            <Icon name="settings" />
            {t('dashboard.nav.settings')}
          </span>
          <div className="fitness-profile">
            <div className="fitness-profile__identity">
              <span className="fitness-profile__avatar" aria-hidden="true">
                {currentUser.first_name.charAt(0).toUpperCase()}
              </span>
              <div>
                <strong>{currentUser.first_name} {currentUser.last_name}</strong>
                <span>@{currentUser.username}</span>
              </div>
            </div>
            <button type="button" disabled={isLoggingOut} onClick={onLogout}>
              {isLoggingOut ? t('dashboard.loggingOut') : t('dashboard.logout')}
            </button>
          </div>
        </div>
      </aside>

      <main className="fitness-main" id="dashboard">
        <header className="fitness-topbar">
          <div>
            <h1>
              {activeView === 'dashboard'
                ? t('dashboard.greeting', { name: currentUser.first_name })
                : t('exercises.title')}
            </h1>
            <span>
              {activeView === 'dashboard'
                ? t('dashboard.subtitle')
                : t('exercises.subtitle')}
            </span>
          </div>
          <div className="fitness-topbar__actions">
            <LanguageSwitcher />
            {activeView === 'dashboard' ? (
              <>
                <button className="icon-action" type="button" disabled aria-label={t('dashboard.searchSoon')}>
                  <Icon name="search" />
                </button>
                <button className="icon-action" type="button" disabled aria-label={t('dashboard.calendarSoon')}>
                  <Icon name="calendar" />
                </button>
                <button className="fitness-primary" type="button" disabled title={t('dashboard.workoutUnavailable')}>
                  {t('dashboard.startWorkout')}
                </button>
              </>
            ) : !isExerciseFormOpen ? (
              <button
                className="fitness-primary fitness-primary--enabled"
                type="button"
                aria-controls="exercise-create-panel"
                aria-expanded="false"
                onClick={() => setIsExerciseFormOpen(true)}
              >
                {t('exercises.add')}
              </button>
            ) : null}
          </div>
        </header>

        {logoutError ? <p className="form-error fitness-error" role="alert">{logoutError}</p> : null}

        {activeView === 'dashboard' ? (
          <div className="fitness-grid">
          <section className="dark-card weekly-card" aria-labelledby="week-title">
            <h2 id="week-title"><Icon name="progress" /> {t('dashboard.week.title')}</h2>
            <div className="weekly-metrics">
              <article><span>{t('dashboard.week.workouts')}</span><strong>0</strong><small>{t('dashboard.week.noSessions')}</small></article>
              <article><span>{t('dashboard.week.volume')}</span><strong>{t('dashboard.week.zeroVolume')}</strong><small>{t('dashboard.week.waiting')}</small></article>
              <article><span>{t('dashboard.week.duration')}</span><strong>{t('dashboard.week.zeroDuration')}</strong><small>{t('dashboard.week.noTraining')}</small></article>
              <article><span>{t('dashboard.week.sets')}</span><strong>0</strong><small>{t('dashboard.week.nothingRecorded')}</small></article>
            </div>
          </section>

          <section className="dark-card up-next-card" aria-labelledby="up-next-title">
            <h2 id="up-next-title"><Icon name="calendar" /> {t('dashboard.upNext.title')}</h2>
            <div className="dark-empty dark-empty--compact">
              <strong>{t('dashboard.upNext.empty')}</strong>
              <p>{t('dashboard.upNext.hint')}</p>
              <button type="button" disabled>{t('dashboard.upNext.action')}</button>
            </div>
          </section>

          <section className="dark-card volume-card" aria-labelledby="volume-title">
            <div className="dark-card__heading">
              <h2 id="volume-title">{t('dashboard.volume.title')}</h2>
              <span>{t('dashboard.volume.period')}</span>
            </div>
            <div className="volume-chart" aria-label={t('dashboard.volume.noDataLabel')}>
              <div className="chart-calibration" aria-hidden="true">
                <span>{t('dashboard.volume.measure')}</span>
                <i />
                <span>{t('dashboard.volume.baseline')}</span>
              </div>
              <div className="chart-y">{volumeScale.map((label) => <span key={label}>{label}</span>)}</div>
              <div className="chart-area">
                <i /><i /><i /><i /><i />
                <svg viewBox="0 0 700 190" preserveAspectRatio="none" aria-hidden="true">
                  <path className="chart-placeholder" d="M0 174 L700 174" />
                </svg>
                <div className="chart-days">{weekDays.map((day) => <span key={day}>{day}</span>)}</div>
              </div>
            </div>
          </section>

          <section className="dark-card progress-card" aria-labelledby="progress-title">
            <div className="dark-card__heading">
              <h2 id="progress-title"><Icon name="progress" /> {t('dashboard.progress.title')}</h2>
              <span>{t('dashboard.progress.period')}</span>
            </div>
            <div className="progress-list">
              {['volume', 'strength', 'workouts'].map((key) => (
                <div key={key}><span>{t(`dashboard.progress.${key}`)}</span><strong>-</strong><small>{t('dashboard.progress.noData')}</small></div>
              ))}
            </div>
          </section>

          <section className="dark-card recent-card" aria-labelledby="recent-title">
            <h2 id="recent-title">{t('dashboard.recent.title')}</h2>
            <div className="dark-empty">
              <Icon name="dumbbell" />
              <strong>{t('dashboard.recent.empty')}</strong>
              <p>{t('dashboard.recent.hint')}</p>
            </div>
          </section>

          <section className="dark-card achievement-card" aria-labelledby="achievement-title">
            <h2 id="achievement-title">{t('dashboard.achievements.title')}</h2>
            <div className="dark-empty">
              <span className="achievement-badge" aria-hidden="true"><Icon name="achievement" /></span>
              <strong>{t('dashboard.achievements.empty')}</strong>
              <p>{t('dashboard.achievements.hint')}</p>
            </div>
          </section>
          </div>
        ) : (
          <ExercisesPage
            accessToken={accessToken}
            isFormOpen={isExerciseFormOpen}
            onAccessTokenChange={onAccessTokenChange}
            onFormOpenChange={setIsExerciseFormOpen}
            onSessionExpired={onSessionExpired}
          />
        )}
      </main>
    </div>
  )
}
