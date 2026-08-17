# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

People who train in a gym and want a structured alternative to notes, spreadsheets, and generic fitness applications.

## Product Purpose

Corvus helps a person plan reusable workouts, record completed training sessions, and understand exercise progress over time. The MVP succeeds when the complete flow from account creation to reviewing progress is clear and dependable.

## Positioning

Corvus keeps planned targets and completed training records in one focused workflow while preserving historical workout data when templates later change.

## Operating Context

The product is used before training to prepare a workout, during a gym session to record sets efficiently, and afterward to review history and progress. Desktop and mobile web are both required, with English and Ukrainian localization.

## Capabilities and Constraints

- The MVP covers authentication, exercises, workout templates, workout sessions, completed sets, history, progress, and notes.
- Private workout data is owned by the authenticated user and backend authorization remains authoritative.
- Exercise and set order must be preserved.
- Historical sessions must remain stable after template edits.
- Unimplemented controls must remain visibly unavailable and the interface must not fabricate workout data.
- The existing stack is React, TypeScript, Vite, `react-i18next`, and Phosphor Icons.

## Brand Commitments

The product name is Corvus. Its confirmed interface direction is a dark, calm, utilitarian training environment inspired by calibrated gym equipment: graphite surfaces, precise structure, a single fresh-green action accent, restrained motion, and no decorative fitness hype.

## Evidence on Hand

The repository contains implemented authentication UI, localized product copy, a dashboard shell, empty states, and the Corvus name. It does not contain real workout totals, testimonials, achievements, or commercial proof; future work must not fabricate them.

## Product Principles

- Complete the core workout flow before expanding the platform.
- Make recording training fast, legible, and resistant to accidental data loss.
- Keep planned targets distinct from completed results.
- Prefer honest empty states over decorative sample data.
- Preserve one coherent product language across every surface.

## Accessibility & Inclusion

Maintain semantic landmarks, headings, labels, keyboard access, visible focus, sufficient contrast, reduced-motion support, and equivalent English and Ukrainian experiences.
