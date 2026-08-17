import { useTranslation } from 'react-i18next'

import { setLanguage, supportedLanguages, type SupportedLanguage } from '../i18n'

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const currentLanguage = i18n.resolvedLanguage?.startsWith('uk') ? 'uk' : 'en'

  return (
    <div className="language-switcher" aria-label={t('language.label')} role="group">
      {supportedLanguages.map((language) => (
        <button
          className={currentLanguage === language ? 'language-switcher__option language-switcher__option--active' : 'language-switcher__option'}
          type="button"
          aria-label={t(language === 'en' ? 'language.english' : 'language.ukrainian')}
          aria-pressed={currentLanguage === language}
          key={language}
          onClick={() => void setLanguage(language as SupportedLanguage)}
        >
          {language.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
