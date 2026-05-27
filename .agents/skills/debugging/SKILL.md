---
name: debugging
description: Use this skill when debugging this Vue/Vite/ECharts frontend visualization project, including browser runtime errors, Vite dev-server or build failures, local JSON/CSV loading, PapaParse parsing, ECharts rendering or resizing, Vue component state, routing, CSS layout, and frontend regressions.
---

# Debugging

## Workflow

1. Reproduce the issue first. Use the user's exact page, command, browser path, error text, or interaction when available.
2. Inspect the smallest relevant surface before changing code: terminal output, browser console, stack trace, local data file, Vue component, chart option, CSS, route, and related prototype or document.
3. For data failures, verify files under `public/data`, import/fetch paths, JSON/CSV shape, PapaParse options, headers, numeric conversion, empty rows, and encoding before assuming the chart code is wrong.
4. For ECharts failures, check container dimensions, mount timing, `setOption` input, empty series data, axis fields, resize handling, and disposal on component unmount.
5. For Vue/Vite failures, check import paths, package scripts, dependency versions, reactive state updates, lifecycle hooks, and browser-only code paths.
6. Apply the smallest fix that addresses the root cause. Avoid unrelated refactors, styling churn, or prototype changes.
7. Verify with the narrowest useful command first, then broaden if risk warrants it: `npm run build`, dev-server smoke test, browser console check, or targeted data parsing check.

## Project Context

- This is a pure frontend Vue + JavaScript + Vite project using Apache ECharts.
- Local JSON/CSV files are the expected data source; do not replace them with remote APIs or synthetic data unless the user explicitly asks.
- The page prototypes in `page prototypes/` are the visual and interaction baseline for later development.
- Project documents in `docs/Project-Proposal.md` and `docs/Modification-Suggestions.md` provide product goals and prototype guidance.
- Respond in Chinese and explain important changes before editing files.

## Debug Report

When finishing, state the root cause, changed files, and verification performed. If a verification step cannot run, say exactly why.
