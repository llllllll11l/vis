---
name: fronted-dev
description: Use this skill when developing or modifying this Vue/Vite/ECharts frontend visualization project, including creating or editing Vue components, JavaScript browser logic, ECharts chart views, routing, forms, CSS/SCSS, responsive UI, local JSON/CSV data loading, and implementation based on page prototypes or project documents.
---

# Fronted Dev

## Workflow

1. Read the relevant request, then inspect existing code before designing changes. Preserve current project patterns unless there is a concrete reason to adjust them.
2. For page work, compare the target with the matching prototype in `page prototypes/` and the guidance in `docs/Project-Proposal.md` or `docs/Modification-Suggestions.md`.
3. For chart work, inspect the real JSON/CSV file under `public/data` before shaping ECharts options. Use PapaParse for CSV parsing.
4. Implement the smallest coherent change in Vue, JavaScript, CSS, or SCSS. Avoid unrelated refactors, dependency additions, and generated boilerplate.
5. Keep the first screen usable as the actual data visualization experience, not a marketing or landing page.
6. Verify responsive layout, chart rendering, data loading, and browser console health. Run `npm run build` when the change can affect production output.

## Project Rules

- Respond in Chinese.
- Explain important changes before editing files.
- Base later development on the four HTML prototypes in `page prototypes/`.
- Keep data local unless the user explicitly asks for external APIs.
- Prefer existing Vue/Vite/ECharts conventions and local helper patterns.
- Ensure chart containers have stable dimensions and dispose ECharts instances on component unmount when instances are created manually.
- Keep UI text readable within its containers across mobile and desktop widths.

## Delivery

When finishing, summarize changed files, what behavior changed, and which checks passed or could not be run.
