import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { templateTranslations } from './features/templates/translations'

export const supportedLanguages = ['en', 'uk'] as const
export type SupportedLanguage = (typeof supportedLanguages)[number]

const LANGUAGE_STORAGE_KEY = 'corvus.language'

const resources = {
  en: {
    translation: {
      templates: templateTranslations.en,
      language: {
        label: 'Language',
        english: 'English',
        ukrainian: 'Ukrainian',
      },
      landing: {
        title: 'Training without the clutter',
        copy: 'Plan your workouts, record completed sets, and follow your progress in one focused place.',
        checkingSession: 'Checking your session…',
      },
      auth: {
        tabsLabel: 'Authentication',
        showLogin: 'Show sign-in form',
        showRegistration: 'Show registration form',
        signIn: 'Sign in',
        register: 'Register',
        accountCreated: 'Account created. You can now sign in to Corvus.',
        login: {
          eyebrow: 'Your training space',
          title: 'Sign in to Corvus',
          hint: 'Use the email or username you chose during registration.',
          loginLabel: 'Email or username',
          passwordLabel: 'Password',
          submitting: 'Signing in…',
        },
        registration: {
          eyebrow: 'New account',
          title: 'Create your profile',
          hint: 'Fill in the short form to start planning your workouts.',
          firstName: 'First name',
          lastName: 'Last name',
          email: 'Email',
          username: 'Username',
          usernameTitle: 'Use only Latin letters, numbers, and underscores',
          usernameHint: '3–50 characters: Latin letters, numbers, and underscores.',
          password: 'Password',
          passwordHint: 'At least 8 characters.',
          confirmPassword: 'Confirm password',
          submit: 'Create account',
          submitting: 'Creating account…',
        },
        errors: {
          invalidCredentials: 'Incorrect email, username, or password.',
          emailTaken: 'An account with this email already exists.',
          usernameTaken: 'This username is already taken.',
          invalidFields: 'Check that every field is filled in correctly.',
          passwordMismatch: 'Passwords do not match.',
          server: 'The server could not complete the request: {{message}}',
          connection: 'Could not connect to the server. Please try again.',
          logout: 'Could not log out. Check your connection and try again.',
        },
      },
      dashboard: {
        navLabel: 'Primary navigation',
        hideMenu: 'Hide menu',
        showMenu: 'Show menu',
        nav: {
          dashboard: 'Dashboard',
          training: 'Training',
          workouts: 'Workouts',
          templates: 'Templates',
          exercises: 'Exercises',
          sessions: 'Sessions',
          history: 'History',
          progress: 'Progress',
          settings: 'Settings',
        },
        logout: 'Log out',
        loggingOut: 'Leaving…',
        greeting: 'Good to see you, {{name}}',
        subtitle: 'Ready to make today count?',
        searchSoon: 'Search coming soon',
        calendarSoon: 'Calendar coming soon',
        startWorkout: '+ Start workout',
        workoutUnavailable: 'Workout sessions are not implemented yet',
        week: {
          title: 'This week',
          workouts: 'Workouts',
          volume: 'Volume',
          zeroVolume: '0 kg',
          duration: 'Duration',
          zeroDuration: '0m',
          sets: 'Sets',
          noSessions: 'No sessions yet',
          waiting: 'Waiting for data',
          noTraining: 'No training logged',
          nothingRecorded: 'Nothing recorded',
        },
        upNext: {
          title: 'Up next',
          empty: 'No workout scheduled',
          hint: 'Create a template to prepare your next session.',
          action: 'Create template',
        },
        volume: {
          title: 'Training volume',
          period: 'This week',
          measure: 'Load index',
          baseline: '0 kg baseline',
          noDataLabel: 'No training volume data yet',
          scale: ['20k', '15k', '10k', '5k', '0'],
          days: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        },
        progress: {
          title: 'Progress overview',
          period: 'This month',
          volume: 'Volume',
          strength: 'Strength',
          workouts: 'Workouts',
          noData: 'No data',
        },
        recent: {
          title: 'Recent workouts',
          empty: 'No completed workouts',
          hint: 'Your latest sessions will appear here.',
        },
        achievements: {
          title: 'Achievements',
          empty: 'Your first milestone awaits',
          hint: 'Complete workouts to unlock achievements.',
        },
      },
      exercises: {
        title: 'Exercises',
        subtitle: 'Build a clear movement catalog for every workout.',
        add: 'Add exercise',
        catalog: {
          title: 'Exercise catalog',
          count_one: '{{count}} available exercise',
          count_other: '{{count}} available exercises',
          filteredCount: '{{count}} of {{total}} exercises',
          system: 'Shared exercise',
          custom: 'Your exercise',
          muscleGroups: 'Target muscle groups',
        },
        search: {
          label: 'Search exercises',
          placeholder: 'Search by exercise or muscle…',
        },
        loading: {
          title: 'Loading your exercise catalog',
          hint: 'Retrieving shared and personal exercises.',
        },
        empty: {
          title: 'No exercises yet',
          hint: 'Add your first exercise to start building workout templates.',
          action: 'Create first exercise',
          searchTitle: 'No matching exercises',
          searchHint: 'Try another exercise name or muscle group.',
          clearSearch: 'Clear search',
        },
        errors: {
          loadTitle: 'The catalog could not be loaded',
          retry: 'Try again',
          forbidden: 'You do not have permission to access these exercises.',
          rateLimited: 'Too many requests. Wait a moment and try again.',
          invalid: 'Check the exercise name and selected muscle groups.',
          server: 'The server could not complete the exercise request. Try again.',
          connection: 'Could not connect to the server. Check your connection and try again.',
        },
        form: {
          title: 'Create an exercise',
          hint: 'Add a movement that is missing from the shared catalog.',
          close: 'Close',
          name: 'Exercise name',
          nameHint: 'Saved in the current interface language ({{language}}).',
          muscleGroups: 'Muscle groups',
          muscleGroupsHint: 'Select every primary muscle group this movement trains.',
          submit: 'Create exercise',
          submitting: 'Creating exercise…',
          success: '“{{name}}” was added to your catalog.',
          errors: {
            name: 'Enter an exercise name.',
            muscleGroup: 'Select at least one muscle group.',
            noMuscleGroups: 'No muscle groups are available yet. Add catalog data before creating an exercise.',
          },
        },
      },
    },
  },
  uk: {
    translation: {
      templates: templateTranslations.uk,
      language: {
        label: 'Мова',
        english: 'Англійська',
        ukrainian: 'Українська',
      },
      landing: {
        title: 'Тренування без хаосу',
        copy: 'Плануйте тренування, записуйте виконані підходи та стежте за прогресом в одному зручному місці.',
        checkingSession: 'Перевіряємо вашу сесію…',
      },
      auth: {
        tabsLabel: 'Авторизація',
        showLogin: 'Показати форму входу',
        showRegistration: 'Показати форму реєстрації',
        signIn: 'Увійти',
        register: 'Реєстрація',
        accountCreated: 'Обліковий запис створено. Тепер ви можете увійти в Corvus.',
        login: {
          eyebrow: 'Ваш простір для тренувань',
          title: 'Увійти в Corvus',
          hint: 'Використайте email або ім’я користувача, вибране під час реєстрації.',
          loginLabel: 'Email або ім’я користувача',
          passwordLabel: 'Пароль',
          submitting: 'Входимо…',
        },
        registration: {
          eyebrow: 'Новий обліковий запис',
          title: 'Створіть свій профіль',
          hint: 'Заповніть коротку форму, щоб почати планувати тренування.',
          firstName: 'Ім’я',
          lastName: 'Прізвище',
          email: 'Email',
          username: 'Ім’я користувача',
          usernameTitle: 'Використовуйте лише латинські літери, цифри та підкреслення',
          usernameHint: '3–50 символів: латинські літери, цифри та підкреслення.',
          password: 'Пароль',
          passwordHint: 'Щонайменше 8 символів.',
          confirmPassword: 'Підтвердіть пароль',
          submit: 'Створити обліковий запис',
          submitting: 'Створюємо обліковий запис…',
        },
        errors: {
          invalidCredentials: 'Неправильний email, ім’я користувача або пароль.',
          emailTaken: 'Обліковий запис із цим email уже існує.',
          usernameTaken: 'Це ім’я користувача вже зайняте.',
          invalidFields: 'Перевірте правильність заповнення всіх полів.',
          passwordMismatch: 'Паролі не збігаються.',
          server: 'Сервер не зміг виконати запит: {{message}}',
          connection: 'Не вдалося підключитися до сервера. Спробуйте ще раз.',
          logout: 'Не вдалося вийти. Перевірте з’єднання та спробуйте ще раз.',
        },
      },
      dashboard: {
        navLabel: 'Основна навігація',
        hideMenu: 'Сховати меню',
        showMenu: 'Відкрити меню',
        nav: {
          dashboard: 'Головна',
          training: 'Тренування',
          workouts: 'Тренування',
          templates: 'Шаблони',
          exercises: 'Вправи',
          sessions: 'Сесії',
          history: 'Історія',
          progress: 'Прогрес',
          settings: 'Налаштування',
        },
        logout: 'Вийти',
        loggingOut: 'Виходимо…',
        greeting: 'Раді вас бачити, {{name}}',
        subtitle: 'Готові зробити сьогоднішній день продуктивним?',
        searchSoon: 'Пошук незабаром',
        calendarSoon: 'Календар незабаром',
        startWorkout: '+ Почати тренування',
        workoutUnavailable: 'Тренувальні сесії ще не реалізовані',
        week: {
          title: 'Цього тижня',
          workouts: 'Тренування',
          volume: 'Обсяг',
          zeroVolume: '0 кг',
          duration: 'Тривалість',
          zeroDuration: '0 хв',
          sets: 'Підходи',
          noSessions: 'Сесій ще немає',
          waiting: 'Очікуємо дані',
          noTraining: 'Тренувань ще немає',
          nothingRecorded: 'Нічого не записано',
        },
        upNext: {
          title: 'Наступне',
          empty: 'Тренування не заплановано',
          hint: 'Створіть шаблон, щоб підготувати наступну сесію.',
          action: 'Створити шаблон',
        },
        volume: {
          title: 'Обсяг тренувань',
          period: 'Цей тиждень',
          measure: 'Індекс навантаження',
          baseline: 'База: 0 кг',
          noDataLabel: 'Даних про обсяг тренувань ще немає',
          scale: ['20 тис.', '15 тис.', '10 тис.', '5 тис.', '0'],
          days: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'],
        },
        progress: {
          title: 'Огляд прогресу',
          period: 'Цей місяць',
          volume: 'Обсяг',
          strength: 'Сила',
          workouts: 'Тренування',
          noData: 'Немає даних',
        },
        recent: {
          title: 'Останні тренування',
          empty: 'Завершених тренувань ще немає',
          hint: 'Тут з’являться ваші останні сесії.',
        },
        achievements: {
          title: 'Досягнення',
          empty: 'Перше досягнення вже чекає',
          hint: 'Завершуйте тренування, щоб відкривати досягнення.',
        },
      },
      exercises: {
        title: 'Вправи',
        subtitle: 'Створіть зрозумілий каталог рухів для кожного тренування.',
        add: 'Додати вправу',
        catalog: {
          title: 'Каталог вправ',
          count_one: 'Доступна {{count}} вправа',
          count_few: 'Доступні {{count}} вправи',
          count_many: 'Доступно {{count}} вправ',
          count_other: 'Доступно {{count}} вправи',
          filteredCount: 'Показано {{count}} із {{total}} вправ',
          system: 'Спільна вправа',
          custom: 'Ваша вправа',
          muscleGroups: 'Цільові групи м’язів',
        },
        search: {
          label: 'Пошук вправ',
          placeholder: 'Пошук за вправою або м’язом…',
        },
        loading: {
          title: 'Завантажуємо каталог вправ',
          hint: 'Отримуємо спільні та особисті вправи.',
        },
        empty: {
          title: 'Вправ поки немає',
          hint: 'Додайте першу вправу, щоб почати створювати шаблони тренувань.',
          action: 'Створити першу вправу',
          searchTitle: 'Відповідних вправ не знайдено',
          searchHint: 'Спробуйте іншу назву вправи або групу м’язів.',
          clearSearch: 'Очистити пошук',
        },
        errors: {
          loadTitle: 'Не вдалося завантажити каталог',
          retry: 'Спробувати ще раз',
          forbidden: 'У вас немає дозволу на доступ до цих вправ.',
          rateLimited: 'Забагато запитів. Зачекайте трохи та спробуйте ще раз.',
          invalid: 'Перевірте назву вправи та вибрані групи м’язів.',
          server: 'Сервер не зміг виконати запит вправ. Спробуйте ще раз.',
          connection: 'Не вдалося підключитися до сервера. Перевірте з’єднання та спробуйте ще раз.',
        },
        form: {
          title: 'Створити вправу',
          hint: 'Додайте рух, якого немає у спільному каталозі.',
          close: 'Закрити',
          name: 'Назва вправи',
          nameHint: 'Буде збережено поточною мовою інтерфейсу ({{language}}).',
          muscleGroups: 'Групи м’язів',
          muscleGroupsHint: 'Виберіть усі основні групи м’язів, які тренує цей рух.',
          submit: 'Створити вправу',
          submitting: 'Створюємо вправу…',
          success: '«{{name}}» додано до вашого каталогу.',
          errors: {
            name: 'Введіть назву вправи.',
            muscleGroup: 'Виберіть щонайменше одну групу м’язів.',
            noMuscleGroups: 'Групи м’язів поки недоступні. Додайте дані каталогу перед створенням вправи.',
          },
        },
      },
    },
  },
} as const

function readStoredLanguage(): SupportedLanguage {
  try {
    const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
    return supportedLanguages.includes(storedLanguage as SupportedLanguage)
      ? (storedLanguage as SupportedLanguage)
      : 'en'
  } catch {
    return 'en'
  }
}

void i18n.use(initReactI18next).init({
  resources,
  lng: readStoredLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export async function setLanguage(language: SupportedLanguage) {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  } catch {
    // The selected language still works when storage is unavailable.
  }

  document.documentElement.lang = language
  await i18n.changeLanguage(language)
}

document.documentElement.lang = readStoredLanguage()

export default i18n
