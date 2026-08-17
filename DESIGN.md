---
name: Corvus
description: A calibrated graphite interface for focused gym training.
colors:
  canvas: "#090b0b"
  rail: "#0d100f"
  surface: "#121615"
  surface-raised: "#171c1a"
  surface-input: "#0c0f0e"
  line: "#29302d"
  line-strong: "#3a443f"
  text: "#f1f3ef"
  muted: "#9aa49f"
  faint: "#89938e"
  accent: "#63d982"
  accent-strong: "#7ee397"
  accent-dark: "#183c25"
  focus: "rgb(99 217 130 / 30%)"
  danger: "#ff8f8f"
  danger-surface: "#2b1718"
  danger-line: "#6f3437"
  success-surface: "#10281a"
typography:
  display:
    fontFamily: "Roboto Condensed Variable, Arial Narrow, Arial, sans-serif"
    fontSize: "clamp(3.25rem, 7vw, 6rem)"
    fontWeight: 760
    lineHeight: 0.93
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Roboto Condensed Variable, Arial Narrow, Arial, sans-serif"
    fontSize: "clamp(2.1rem, 4vw, 3.7rem)"
    fontWeight: 760
    lineHeight: 0.96
    letterSpacing: "-0.04em"
  title:
    fontFamily: "Roboto Condensed Variable, Arial Narrow, Arial, sans-serif"
    fontSize: "clamp(1.65rem, 3vw, 2.2rem)"
    fontWeight: 760
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Roboto Condensed Variable, Arial Narrow, Arial, sans-serif"
    fontSize: "clamp(1rem, 1.6vw, 1.18rem)"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Roboto Condensed Variable, Arial Narrow, Arial, sans-serif"
    fontSize: "0.68rem"
    fontWeight: 760
    lineHeight: 1
    letterSpacing: "0.1em"
rounded:
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  xl: "1.5rem"
  xxl: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.canvas}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0.75rem 1.15rem"
    height: "3rem"
  button-primary-hover:
    backgroundColor: "{colors.accent-strong}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.sm}"
  button-unavailable:
    backgroundColor: "{colors.accent-dark}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0.75rem 1.15rem"
    height: "2.55rem"
  field:
    backgroundColor: "{colors.surface-input}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "0.75rem 0.9rem"
    height: "3rem"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "1.3rem 1.4rem"
  nav-active:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "0 0.75rem"
    height: "2.75rem"
---

# Design System: Corvus

## Overview

**Creative North Star: "The Calibrated Training Instrument"**

Corvus is a dark, calm, utilitarian training environment inspired by calibrated gym equipment. It should feel like a focused instrument for planning and recording work: dense enough to scan quickly, exact enough to trust, and quiet enough to use between sets.

Graphite surfaces, precise separators, compact controls, and moderate corners form one continuous world across authentication and the dashboard. A single fresh-green signal marks action, selection, focus, and positive state; restrained motion confirms state changes without turning the interface into a lifestyle landing page or generic admin template.

The system tells the truth. Ready, empty, loading, error, and unavailable states remain visibly distinct, and absent workout data is never replaced with decorative metrics or fitness hype.

**Key Characteristics:**

- Calibrated graphite surfaces with exact structural separators
- One fresh-green signal used with deliberate restraint
- Condensed, high-contrast typography optimized for dense training data
- Compact controls and moderate corners modeled on durable equipment
- Honest empty and unavailable states instead of fabricated activity
- Restrained, accessible motion with reduced-motion support

## Colors

The palette is an incremental graphite scale animated by one fresh green; semantic danger appears only when the system must interrupt or correct the user.

### Primary

- **Fresh Calibration Green** (#63d982): The sole active signal for primary actions, selected controls, focus, chart emphasis, and positive state.
- **Lit Calibration Green** (#7ee397): A brighter hover and success-text state that keeps interaction feedback within the same signal family.
- **Deep Signal Green** (#183c25): A dark supporting field behind avatars, badges, and intentionally subdued unavailable actions.

### Neutral

- **Midnight Graphite** (#090b0b): The page canvas and darkest visual anchor.
- **Rail Graphite** (#0d100f): The persistent navigation rail and quiet chrome.
- **Working Graphite** (#121615): The standard card and form-container surface.
- **Raised Graphite** (#171c1a): Active navigation, emphasized cards, and hover fills.
- **Recessed Graphite** (#0c0f0e): Input wells and compact control housings.
- **Precision Line** (#29302d): Standard structural boundaries, metric dividers, and calibration ticks.
- **Strong Precision Line** (#3a443f): Major boundaries and interactive strokes.
- **Instrument White** (#f1f3ef): Primary text and important values.
- **Muted Steel** (#9aa49f): Secondary explanation and supporting labels.
- **Faint Steel** (#89938e): Metadata, disabled navigation, and low-priority calibration labels.
- **Focus Calibration Ring** (rgb(99 217 130 / 30%)): Translucent keyboard and field-focus confirmation.
- **Warning Red** (#ff8f8f): Validation text and invalid-field borders.
- **Warning Field** (#2b1718): Validation and operation-failure backing.
- **Warning Line** (#6f3437): Validation and operation-failure boundaries.
- **Success Field** (#10281a): Quiet confirmation backing for completed account operations.

### Named Rules

**The One Signal Rule.** Fresh green is the only non-semantic accent; use it for action, selection, focus, positive state, and measured data emphasis, never as decorative fill.

**The Graphite Ladder Rule.** Separate regions by moving one deliberate step through the graphite scale and adding a precise line before introducing shadow.

## Typography

**Display Font:** Roboto Condensed Variable (with Arial Narrow, Arial, and sans-serif fallbacks)  
**Body Font:** Roboto Condensed Variable (with Arial Narrow, Arial, and sans-serif fallbacks)

**Character:** One self-hosted variable family keeps the interface cohesive and operational. Its condensed proportions support dense labels and workout metrics, while heavy variable weights give headlines authority without relying on decorative type.

### Hierarchy

- **Display** (760, fluid 3.25–6rem, 0.93): The authentication statement; tightly tracked and balanced within a short measure.
- **Headline** (760, fluid 2.1–3.7rem, 0.96): Dashboard greetings and primary workspace headings.
- **Title** (760, fluid 1.65–2.2rem, 1.05): Authentication-panel titles.
- **Body** (400, fluid 1–1.18rem, 1.65): Introductory copy with a maximum measure of roughly 35rem.
- **Label** (760, 0.68rem, 0.1em, uppercase): Card headings and calibration labels; smaller metadata keeps normal tracking and sentence case.
- **Metric** (650, fluid 1.9–2.7rem, 1): Workout totals use tabular numerals and tight tracking for stable comparison.

### Named Rules

**The Condensed Instrument Rule.** Use the variable family’s width and weight range to create hierarchy; do not introduce a decorative display face or a separate data font.

**The Numeric Stability Rule.** Training totals, axes, and comparable measurements use tabular numerals.

## Layout

Authentication uses a balanced two-column first viewport: a flexible statement region and a form region with a practical 24rem minimum. The statement carries generous fluid padding, while the form is a bounded, centered working surface. At 58rem the composition stacks; below 34rem the form becomes edge-to-edge, loses its floating shadow and radius, and multi-field rows become single-column.

The dashboard uses a persistent 14.5rem calibration rail beside a 12-column workbench. Major cards span 4–8 columns with a tight 0.8rem gutter; at 64rem the rail narrows to 12.5rem and cards stack into one column. Below 48rem the rail becomes a compact top strip with horizontally scrollable active navigation, secondary disabled destinations and profile chrome are removed, and card padding contracts without changing hierarchy.

Spacing follows a compact quarter-rem rhythm, with 0.5–1rem inside controls and 1.3–2rem around working groups. Structural alignment is more important than generous whitespace: card headers, dividers, metrics, chart ticks, and action rows should share exact edges.

**The Rail and Workbench Rule.** Navigation remains a stable calibration reference; task content may reflow, but its active marker, boundaries, and working density stay exact.

## Elevation & Depth

Corvus is tonally layered first and softly lifted second. One-pixel graphite borders do most of the structural work. Standard dashboard cards receive a low ambient shadow, while the authentication card receives the only strongly lifted treatment because it is the immediate task surface. On narrow mobile screens that card returns to the canvas with no shadow.

### Shadow Vocabulary

- **Card Ambient** (`0 1rem 2.5rem rgb(0 0 0 / 12%)`): Low separation beneath dashboard cards.
- **Task Lift** (`0 1.75rem 5rem rgb(0 0 0 / 32%)`): Authentication card only on layouts where it floats beside the product statement.
- **Calibration Rings** (`0 0 0 4rem rgb(99 217 130 / 2%), 0 0 0 8rem rgb(99 217 130 / 1.5%)`): The restrained environmental motif behind the authentication statement, never a general card effect.

### Named Rules

**The Tonal-Before-Shadow Rule.** Establish hierarchy with graphite steps and precise borders first; reserve shadow for a genuinely lifted task surface.

## Shapes

The form language uses moderate, equipment-like corners: compact controls and markers use 0.5rem, cards and segmented housings use 0.75rem, and the large authentication task surface uses 1rem. Borders stay crisp at 1px. Full circles are limited to the loading spinner and the ambient calibration motif; pills appear only where the active navigation marker needs a narrow mechanical indicator.

The Corvus mark is a compact bordered square containing three green calibration blocks at different intensities. It is functional brand geometry, not an invitation to add decorative illustrations.

**The Measured Corner Rule.** Radius follows scale and function; do not turn controls or containers into oversized pills.

## Components

Components feel compact, exact, and tactile enough to confirm a training action without appearing playful.

### Buttons

- **Shape:** Moderately curved equipment control (0.5rem) with a minimum height of 2.4–3rem.
- **Primary:** Fresh green field, dark text, strong 800 weight, and a brighter green border; the authentication submit action occupies the full form width.
- **Hover / Focus:** Hover brightens to the lit green and rises by 1px; keyboard focus uses the shared translucent green outline. Reduced-motion mode removes translation.
- **Unavailable:** Dashboard actions that are not implemented remain visibly subdued in a deep green or raised graphite field, retain legible labels, and use the not-allowed cursor.
- **Secondary:** Logout and empty-state controls use recessed or raised graphite, precise borders, muted text, and a restrained text/border hover.

### Chips

- **Style:** The language switcher is a compact two-cell segmented control inside a recessed graphite housing.
- **State:** The active language uses fresh-green text over raised graphite; inactive choices stay muted. Authentication tabs use the same segmented logic at a larger scale, with a filled green active state.

### Cards / Containers

- **Corner Style:** Standard dashboard cards use 0.75rem; the floating authentication card uses 1rem and becomes square-edged on narrow mobile screens.
- **Background:** Working graphite is the default, with raised graphite reserved for the weekly summary and active regions.
- **Shadow Strategy:** Follow the tonal-first elevation vocabulary; cards keep structural borders even when shadow is present.
- **Border:** A 1px precision line defines every working surface.
- **Internal Padding:** Typically 1.3rem vertically and 1.3–1.4rem horizontally, contracting to 1.15rem by 1rem on mobile.

### Inputs / Fields

- **Style:** Recessed graphite well, strong precision border, instrument-white text, 0.5rem radius, and a 3rem minimum height.
- **Focus:** The border shifts to fresh green and receives a translucent green outer calibration ring.
- **Error / Disabled:** Invalid fields shift the border to warning red; submitting controls remain present, lower opacity, and communicate waiting rather than disappearing.

### Navigation

The desktop navigation is a persistent dark rail with compact 2.75rem rows. Active navigation uses a raised graphite fill, instrument-white text, green icon, and a narrow green edge marker. Unavailable destinations remain visible and muted on desktop; on mobile the active path becomes a horizontally scrollable top strip and unavailable destinations are removed to preserve task focus.

### Calibration Rail

Charts and the authentication statement reuse a measured linear motif: exact tick intervals, restrained dashed baselines, and a short green segment against a graphite track. It signals readiness and scale without implying workout data that does not exist.

### Empty and Status States

Empty cards keep their real title and structure, then present a compact icon, direct state label, restrained explanation, and only an unavailable action when the feature is not shipped. Loading uses a small green-tipped spinner; errors and success messages use bordered semantic fields rather than transient decoration.

## Do's and Don'ts

### Do:

- **Do** preserve one coherent graphite ladder across authentication, navigation, cards, inputs, and charts.
- **Do** reserve fresh green for action, selection, focus, positive state, and measured emphasis.
- **Do** use precise 1px separators, aligned calibration marks, and tabular numerals to make training data feel trustworthy.
- **Do** keep ready, loading, empty, error, success, and unavailable states explicit and accessible.
- **Do** retain the balanced authentication statement/form and persistent-rail dashboard behavior until their documented breakpoints require reflow.
- **Do** honor visible keyboard focus, sufficient contrast, English/Ukrainian parity, and reduced-motion preferences.

### Don't:

- **Don't** introduce decorative fitness photography, motivational hype, neon gradients, or lifestyle-marketing tropes.
- **Don't** spread the green accent across large decorative areas or add competing accent hues.
- **Don't** fabricate workout totals, chart movement, achievements, or future-feature availability.
- **Don't** turn Corvus into a generic admin dashboard with airy cards, oversized pills, or ornamental widgets.
- **Don't** use motion without state meaning, and never make access to information depend on animation.
