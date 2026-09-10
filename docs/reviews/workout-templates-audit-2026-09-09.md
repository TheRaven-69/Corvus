# Аудит шаблонів Corvus — 9 вересня 2026

Гілка: `feature/workout-templates-frontend`. Перевірені незакомічені зміни фронтенду шаблонів, успадковані стилі навігації та оригінальний ZIP Figma Make. Навички: `impeccable` / audit і `review-animations` зі STANDARDS.md. Код застосунку під час аудиту не змінено.

## 1. Findings

| Before | After — рекомендована зміна | Why |
| --- | --- | --- |
| **P1:** межі полів мають контраст 2.17:1; номери вправ — 4.41:1 | Підняти контраст меж до ≥3:1, дрібного тексту до ≥4.5:1 | Порожні поля та порядок вправ складно розрізняти людям зі зниженим зором |
| **P2:** видалення підходу переводить фокус у BODY | Перевести фокус на сусідній підхід або «Додати підхід» | Клавіатурний користувач втрачає поточне місце в редакторі |
| **P2:** повідомлення про недопустиму вагу загальне для всієї форми | Помилка біля конкретного поля, aria-invalid, aria-describedby і фокус на першій помилці | У довгому плані незрозуміло, яку саме вагу виправити |
| **P2:** на 320 px підписи «Повторення» й «Вага (кг)» стикаються; кнопка видалення 36×44 px | Перекомпонувати рядок на найвужчому breakpoint; ціль кнопки ≥44×44 px | Підписи важко читати, по кнопці складніше влучити пальцем |
| **P2, motion:** hover-переходи працюють без перевірки можливостей вказівника | Обмежити hover стилі через `(hover: hover) and (pointer: fine)` | Touch-браузер може залишати hover-стан після торкання; правила мають відрізняти мишу від дотику |

### Точні місця й відтворення

1. **Контраст — Accessibility.** `frontend/src/features/templates/TemplatesPage.css:302`: border `#b7afa1`, фон поля `#fcfaf6`, фон форми `#ffffff`. Computed styles підтверджені в браузері. Контраст межі до зовнішнього фону **2.1739:1**; саме поле до фону лише **1.0425:1**, тому воно не надає альтернативної достатньо контрастної межі. Номери вправ на рядках **166** і **348** використовують `#857661` на білому: **4.4106:1**. Основний допоміжний текст `#716557` має **5.6738:1** і не є проблемою. Focus outline `#896a1c` на білому має **5.0699:1** і також проходить. Джерело вимог: [W3C — Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html). Рекомендований крок: `$impeccable harden`.

2. **Втрата фокуса — Accessibility.** `frontend/src/features/templates/TemplateEditor.tsx:284–290`. У плані з шістьма підходами активувати кнопкою Enter «Видалити підхід 2 вправи 1». Кількість підходів стає п’ять; `document.activeElement.tagName === 'BODY'`, доступне ім’я фокуса відсутнє. Видалення вправи використовує аналогічний механізм. Потрібні ref на сусідню керовану ціль та оголошення зміни для assistive technology. Рекомендований крок: `$impeccable harden`.

3. **Валідація без адреси помилки — Accessibility / Implementation Integrity.** `frontend/src/features/templates/TemplateEditor.tsx:85–87`, `:257–276`, `:394–398`. Ввести `-1` у вагу першого підходу та натиснути збереження. Запит правильно блокується, але `aria-invalid="true"` не має жодне поле; `aria-describedby` для ваги відсутнє; фокус залишається на кнопці збереження. Загальний текст перелічує кілька можливих причин замість номера вправи/підходу з помилкою. Рекомендований крок: `$impeccable harden`.

4. **Вузький екран — Responsive Design.** `frontend/src/features/templates/TemplatesPage.css:454–469`. Перевірено українську версію у viewport 320×740: підписи сусідніх колонок зливаються. Computed rect активної кнопки видалення підходу — **36×44 px**. 44×44 — критерій навички та бажана touch-ціль; це **не автоматичне порушення WCAG 2.2 AA**, де мінімальний критерій становить 24×24 з винятками. [W3C — Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html). Рекомендований крок: `$impeccable adapt`.

5. **Hover без media gate — Motion / Accessibility.** `frontend/src/features/templates/TemplatesPage.css:58–81`. Короткі зміни кольорів працюють без `(hover: hover) and (pointer: fine)`, на відміну від існуючих стилів Dashboard і Exercises. Це підтверджено кодом; поведінка sticky hover на фізичному touch-пристрої не тестувалася. Рекомендований крок: `$impeccable animate`.

## 2. Verdict

**Implementation integrity: основний потік реалізовано, але фінальну готовність не підтверджую.** Картки використовують дані API, порядок і дробові ваги збережені, metadata-only PATCH не перестворює вкладені рядки. Є підтверджений дефект контрасту та кілька недоліків роботи з клавіатурою/вузьким екраном. Детектор повернув `[]`; це не заміна ручної перевірки.

### Audit Health Score

| Вимір | Оцінка | Підстава |
| --- | --- | --- |
| Accessibility | 2/4 | Контраст меж, втрата фокуса, неадресна валідація |
| Performance | 3/4 | Короткі CSS transitions; немає layout-анімацій у шаблонах; FPS під навантаженням не вимірювався |
| Responsive design | 2/4 | Перевірені раніше 390 px і desktop; на 320 px підтверджений дефект |
| Theming | 2/4 | Scoped палітра працює, але більшість нових кольорів повторюється літералами |
| Implementation integrity | 3/4 | Основні операції та контракти перевірені; доступність потребує доробки |
| **Разом** | **12/20** | **Потрібне цільове виправлення; це оцінка рубрики навички, а не відсоток тестів** |

Підсумок: **P0 — 0; P1 — 1; P2 — 4; P3 — 0**. Не виділяю повторення кольорів в окрему термінову проблему: користувач задав новий дизайн, а повне винесення палітри в токени можна зробити під час подальшого поширення дизайну.

### Рух: що реально є

- У `TemplatesPage.css:54–56` — transitions фону та межі кнопок по **150 ms**, `ease-out`. Вони перериваються природно як CSS transitions. Ознак тривалих, блокувальних або layout-анімацій у цьому розділі немає. Невеликий repaint кольору не подаю як доведений дефект продуктивності.
- У `TemplatesPage.css:475–478` reduced-motion вимикає ці transitions, залишаючи видимі стани. Рухомого входу в шаблонах немає; відключення кольорового переходу тут не приховує функціональний стан.
- Успадкований з Dashboard рух кнопки виходу `translateY(1px)` має окремий reduced-motion override. Анімації авторизації та спінер — старий код поза основним обсягом цього аудиту.
- **Ripple 650 ms з Figma Make не перенесений.** У ZIP його використовує `StartBtn` у `src/pages/Templates.tsx`; у Corvus запуск тренування наразі disabled. Відсутність ripple на недоступній дії сама по собі не є функціональним дефектом. Не слід вмикати кнопку заради анімації.
- **`corvus-page-in` 180 ms / translateY(6px) з ZIP також не перенесений.** Це відмінність від референсу, не причина автоматично анімувати кожен перехід. Для клавіатурної або частої навігації миттєва зміна допустима.
- Якщо ripple переноситиметься на активні кнопки, спочатку адаптувати reduced-motion і pointer events та скоротити feedback до **100–160 ms** згідно зі STANDARDS.md навички. Не копіювати прототипні 650 ms, MouseEvent-only запуск та timeout без cleanup без перегляду. `scale(0)` декоративної хвилі не плутаємо зі схлопуванням цілого діалогу.

**Motion verdict: Block для остаточного схвалення — спочатку закрити hover-gating.** Критичних регресій тривалості чи продуктивності наявних transitions не виявлено. Повна відповідність руху Figma не заявляється.

### Перевірки та обмеження

- `npm.cmd test`: **24/24** успішно.
- `npm.cmd run lint`: успішно.
- `npm.cmd run build`: успішно; JS bundle приблизно **101.80 kB gzip**.
- `git diff --check`: без помилок whitespace.
- `node .agents/skills/impeccable/scripts/detect.mjs --json frontend/src/features/templates frontend/src/features/dashboard/Dashboard.tsx`: `[]`.
- Браузер: computed styles, контраст, Enter-видалення підходу, недопустима вага, українська форма на 320 px. Використано тимчасову сторінку з fixtures; її видалено після перевірки. Користувацькі дані не змінювалися.
- Живий PostgreSQL, фізичний телефон і screen reader не використовувалися. Збереження/видалення на HTTP-межі перевірені тестами з mock responses; це не наскрізний тест живого бекенду.

### Наступні кроки

1. `$impeccable harden`: контраст, адресні помилки та відновлення фокуса.
2. `$impeccable adapt`: рядки підходів на 320 px і touch-цілі.
3. `$impeccable animate`: hover-gating; окремо адаптація потрібних ефектів із Figma для активних дій.
4. `$impeccable polish`: фінальна узгодженість після виправлень.

Ці кроки можна виконати разом або окремо. Після виправлень повторити `$impeccable audit`.


## Implementation follow-up

The five findings have been addressed: stronger input borders and ordinal text,
focus restoration after removal/reordering, linked field validation with focus
on the first invalid input, a two-column mobile set layout with a 44px remove
button, and hover effects restricted to fine pointers. Shared visual tokens now
apply to authentication, dashboard, exercise catalog, and templates.
Regression coverage includes keyboard removal and accessible validation.
