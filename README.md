# The Publishing Company — Portal

Flask web app powering the client portals for Paperbacks & Pixels'
concierge publishing services. This is Track 2 of the platform —
the Flask rebuild that's replacing the Softr-based Track 1.

**Stack:** Flask + Supabase Auth + Airtable

- **Flask** — web framework
- **Supabase Auth** — handles login, sessions, password reset
  (auth only; NOT used as the database)
- **Airtable** — data backend (22 tables, base `appj8IY8wQ6PhnNOi`)

## Architecture — the one rule that matters

Every Airtable query in `services/airtable_queries.py` takes the
logged-in author's record ID as its first argument. Routes never fetch
records directly — they go through this chokepoint, which enforces
ownership by following Airtable link relationships. This is the
entire multi-tenant security model.

## Running locally

```
# Copy the env template and fill it in
cp .env.example .env
# ...then paste in your Airtable PAT, Supabase URL + anon key,
# and a FLASK_SECRET_KEY (generate with the snippet in .env.example)

# Create the virtual env and install dependencies
python -m venv venv
venv\Scripts\pip install -r requirements.txt

# Start the dev server
venv\Scripts\python run.py
```

Then open http://localhost:5000

## Project layout

```
the-publishing-company/
├── app.py                  # Flask app factory + all routes
├── run.py                  # Entry point (exposes `app` for gunicorn)
├── config.py               # Airtable table/field ID constants
├── airtable_helpers.py     # Reusable Airtable API wrappers
├── auth/
│   ├── supabase_client.py  # Supabase Auth REST wrappers
│   └── decorators.py       # @login_required, @role_required
├── services/
│   ├── user_mapping.py     # Supabase user → Airtable Portal User
│   └── airtable_queries.py # DATA ISOLATION CHOKEPOINT
├── templates/              # Jinja templates (base + auth/ + author/)
├── static/css/portal.css   # Neobrutalist P&P brand styles
├── Procfile                # `web: gunicorn run:app` (for Render)
└── requirements.txt
```

## Deployment

Deployed on Render, custom domain `portal.paperbacksandpixels.com`.
Render runs the app via the `Procfile`: `web: gunicorn run:app`.

**Required environment variables on Render:**

| Variable | Source |
|---|---|
| `AIRTABLE_PAT` | https://airtable.com/create/tokens |
| `AIRTABLE_BASE_ID` | `appj8IY8wQ6PhnNOi` |
| `FLASK_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | `production` |
| `SUPABASE_URL` | Supabase project settings |
| `SUPABASE_ANON_KEY` | Supabase project settings |

The app will refuse to start in production mode if
`FLASK_SECRET_KEY` is missing — this is intentional, not a bug.

## Detailed project docs

The comprehensive README, decisions log, ship plan, and session
summaries live in Google Drive at:
`G:/My Drive/Claude Code/The Publishing Company/`
