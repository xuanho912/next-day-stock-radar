# Private Core / Public Dashboard

## Why

The radar has two very different assets:

- core repo: scoring logic, validation logic, provider code, workflow secrets
- public dashboard: generated HTML, CSS, JavaScript and sanitized JSON

Keep the core private if you want to protect the work. Publish only the static dashboard when you want a phone-friendly URL.

## Structure

```text
private: xuanho912/next-day-stock-radar
public:  xuanho912/next-day-stock-radar-dashboard
```

The private repo runs the model. The public repo receives only `frontend/dist`.

## Public Files

The published dashboard contains:

- `index.html`
- `styles.css`
- `app.js`
- `stock-radar-dashboard.json`
- `top-candidates.json`
- `stock-forecast-records.json`
- `validation-scorecard.json`
- `stock-model-leaderboard.json`
- `.nojekyll`

It must not contain:

- `.env`
- API keys
- provider caches
- backend-only scripts
- local databases
- raw secrets

## Setup

In the private core repo, configure:

```text
PUBLIC_DASHBOARD_REPO=xuanho912/next-day-stock-radar-dashboard
PUBLIC_DASHBOARD_BRANCH=main
```

And:

```text
DASHBOARD_DEPLOY_TOKEN
```

The workflow skips public publishing when these values are absent.

## Data Freshness

If the data provider fails, the page must show `fallback_only`, `partial_fallback`, `missing`, or `stale`. A stale page is acceptable; a fake fresh page is not.
