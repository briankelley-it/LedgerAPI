# LedgerAPI

[![CI](https://github.com/briankelley-it/LedgerAPI/actions/workflows/ci.yml/badge.svg)](https://github.com/briankelley-it/LedgerAPI/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/briankelley-it/LedgerAPI/python-coverage-comment-action-data/badge.svg)](https://github.com/briankelley-it/LedgerAPI/tree/python-coverage-comment-action-data)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/django-5.2-green)

An expense tracker REST API. Users register, log in with a JWT, and manage
their own spending categories, expenses and monthly budgets. A summary endpoint
reports total spending, totals by category and totals by month, and every
budget shows how much has been spent against it.

The goal of this project is to show a small API built carefully: consistent
errors, strict per-user data isolation, money handled as decimals, every
endpoint documented in OpenAPI, and a test suite that runs in CI against
PostgreSQL with a coverage gate.

## Tech stack

| Area | Choice |
|---|---|
| Language / framework | Python 3.12, Django 5.2 (LTS), Django REST Framework |
| Auth | JWT via djangorestframework-simplejwt |
| API docs | OpenAPI 3 via drf-spectacular, Swagger UI |
| Filtering | django-filter |
| Database | SQLite for local development, PostgreSQL in Docker, CI and production |
| Config | Environment variables via django-environ |
| Tests | pytest, pytest-django, factory_boy, pytest-cov (90% minimum) |
| Code quality | ruff (lint + format), pre-commit |
| Runtime | Docker, docker compose, gunicorn, WhiteNoise |
| CI | GitHub Actions |

## Quick start

### Option 1: Docker (API + PostgreSQL)

```bash
docker compose up -d --build
```

The API is now at <http://localhost:8010> and redirects to the Swagger UI.
Migrations run automatically when the container starts.

The host ports default to `8010` (API) and `5440` (PostgreSQL) so they do not
clash with other projects. Change them with `API_PORT` and `DB_PORT` in a `.env`
file. All containers belong to the `ledgerapi` compose project, so
`docker compose down` only stops this project.

### Option 2: Local Python (SQLite)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # then set SECRET_KEY
python manage.py migrate
python manage.py runserver
```

The API is now at <http://localhost:8000>.

## API documentation

- Swagger UI: <http://localhost:8010/api/docs/> (Docker) or <http://localhost:8000/api/docs/> (local)
- OpenAPI schema: `/api/schema/`

Every endpoint has a summary, request and response examples, and its error
responses documented. Click **Authorize** in Swagger UI and paste an access
token to try the protected endpoints.

## Endpoints

All endpoints live under `/api/v1/`. Everything except `health/`, `auth/register/`
and the token endpoints needs an `Authorization: Bearer <access token>` header.

| Method | Path | Description |
|---|---|---|
| GET | `health/` | Health check, also checks the database |
| POST | `auth/register/` | Create an account with email + password |
| POST | `auth/token/` | Log in, returns `access` and `refresh` tokens |
| POST | `auth/token/refresh/` | Get a new access token |
| GET | `auth/me/` | The current user |
| GET, POST | `categories/` | List or create categories |
| GET, PUT, PATCH, DELETE | `categories/{id}/` | One category |
| GET, POST | `expenses/` | List or create expenses |
| GET, PUT, PATCH, DELETE | `expenses/{id}/` | One expense |
| GET, POST | `budgets/` | List or create monthly budgets |
| GET, PUT, PATCH, DELETE | `budgets/{id}/` | One budget |
| GET | `reports/summary/` | Totals, by category and by month |

`GET expenses/` supports:

| Parameter | Example | Meaning |
|---|---|---|
| `date_after`, `date_before` | `2026-01-01` | Date range, inclusive |
| `category` | `3` | Expenses in one category |
| `uncategorized` | `true` | Expenses without a category |
| `min_amount`, `max_amount` | `10.00` | Amount range, inclusive |
| `currency` | `EUR` | Only this currency |
| `search` | `coffee` | Text search in the description |
| `ordering` | `-amount` | `date`, `amount` or `created_at`, prefix `-` for descending. Default `-date` |
| `page`, `page_size` | `2`, `50` | Pagination. Default 20 per page, maximum 100 |

`GET reports/summary/` accepts optional `start`, `end` (inclusive dates) and
`currency` (default `USD`).

A budget is a spending limit for one category in one month (one budget per
category per month). Responses include what has been spent so far:

```json
{
  "id": 1, "category": 2, "month": "2026-10", "limit": "60.00", "currency": "USD",
  "spent": "75.40", "remaining": "-15.40", "over_budget": true,
  "created_at": "2026-10-05T17:12:55Z", "updated_at": "2026-10-05T17:12:55Z"
}
```

`GET budgets/` supports `month` (`2026-10`), `category`, `over_budget`
(`true`/`false`) and `ordering` by `month`, `limit` or `spent`.

## Example with curl

```bash
# 1. Register
curl -X POST http://localhost:8010/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@example.com", "password": "correct-horse-battery"}'
# {"id":1,"email":"jane@example.com","date_joined":"2026-10-05T17:04:52.390684Z"}

# 2. Log in and keep the access token
curl -X POST http://localhost:8010/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@example.com", "password": "correct-horse-battery"}'
# {"refresh":"eyJhbGciOi...","access":"eyJhbGciOi..."}
TOKEN="paste the access token here"

# 3. Create a category and an expense
curl -X POST http://localhost:8010/api/v1/categories/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Groceries", "color": "#4CAF50"}'

curl -X POST http://localhost:8010/api/v1/expenses/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"amount": "42.50", "description": "Weekly groceries", "date": "2026-10-04", "category": 1}'

# 4. Filter and summarize
curl "http://localhost:8010/api/v1/expenses/?min_amount=10&ordering=-amount" \
  -H "Authorization: Bearer $TOKEN"

curl "http://localhost:8010/api/v1/reports/summary/?start=2026-10-01&end=2026-10-31" \
  -H "Authorization: Bearer $TOKEN"
# {"start":"2026-10-01","end":"2026-10-31","currency":"USD","total":"42.50","count":1,
#  "by_category":[{"category_id":1,"category_name":"Groceries","total":"42.50","count":1}],
#  "by_month":[{"month":"2026-10","total":"42.50","count":1}]}
```

Access tokens last 15 minutes and refresh tokens 7 days (configurable with
`JWT_ACCESS_MINUTES` and `JWT_REFRESH_DAYS`).

## Error format

Every error, from validation to a missing route to an unexpected crash, has
the same shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input.",
    "details": {"amount": ["Amount must be greater than 0."]}
  }
}
```

`code` is a stable machine-readable string (`validation_error`,
`not_authenticated`, `token_not_valid`, `not_found`, ...). `details` holds
per-field messages for validation errors and is `null` otherwise.

| Status | When |
|---|---|
| 200 / 201 / 204 | Success, created, deleted |
| 400 | Invalid body or query parameters |
| 401 | Missing, invalid or expired token, or wrong login |
| 404 | Not found, including records that belong to another user |
| 503 | Health check cannot reach the database |

## Running tests

```bash
pytest                                # local, SQLite, prints coverage
docker compose run --rm tests         # in Docker, against PostgreSQL
ruff check . && ruff format --check . # lint
```

The suite fails if coverage drops below 90%. It covers the auth flow, CRUD
happy paths, validation errors, isolation between two users, every filter,
ordering, pagination, and the summary math against hand-computed totals.
Test data comes from factory_boy factories in `tests/factories.py`.

To run the same checks automatically before each commit:

```bash
pre-commit install
```

## Continuous integration

GitHub Actions runs on every push and pull request:

1. **lint**: `ruff check` and `ruff format --check`
2. **test**: against a PostgreSQL service container. It also checks for
   missing migrations, validates the OpenAPI schema (warnings fail the
   build) and enforces 90% coverage
3. **docker**: builds the production image
4. **coverage-badge**: on `main`, publishes the coverage badge to a branch
   in this repository (no external service)

## Project layout

```
config/            Django settings, root URLs, WSGI
apps/
  core/            Error handler, pagination, health check, shared mixins
  accounts/        Register, JWT login, current user
  ledger/          Category and Expense models, serializers, views, filters
  reports/         Summary endpoint and services.py with the aggregation logic
tests/             pytest suite, one folder per app, plus factories
docker/            Container entrypoint (runs migrations)
```

## Design decisions

**Every query is scoped to the logged-in user.** `OwnedQuerysetMixin` filters
each queryset by `request.user` and sets the owner on create, so the rule
lives in one place instead of every view. Asking for another user's record
returns **404, not 403**: a 403 would confirm that the id exists. The same rule
applies when an expense points at a category: another user's category id gets
the same error as an id that does not exist.

**Money is `Decimal`, never `float`.** Floats cannot represent most decimal
fractions exactly (`0.1 + 0.2 == 0.30000000000000004`). Amounts are stored as
`DecimalField(max_digits=12, decimal_places=2)`, summed by the database, and
returned as strings (`"42.50"`) so JSON clients do not turn them back into
floats.

**Rules are enforced twice where it matters.** "Amount > 0" and "category
names are unique per user, ignoring case" are checked in the serializer for a
clear 400 message, and again with database constraints as a safety net.

**Summaries are per currency.** Adding USD and EUR together gives a meaningless
number, and real conversion needs exchange rates. The summary endpoint adds up
one currency at a time (default USD) and says which one in the response.

**Thin views, logic elsewhere.** Validation lives in serializers, query
parameters in a `FilterSet`, and the math in small services modules
(`apps/reports/services.py`, `apps/ledger/services.py`) that can be tested
without HTTP.

**No N+1 queries for budgets.** Each budget's `spent` is calculated in the
same SQL query that loads the budgets, using a subquery. Listing 100 budgets
takes 2 queries (count + page), not 101, and a test locks that in.

**One error format.** A custom DRF exception handler, plus JSON handlers for
Django's 404 and 500 pages, means clients only ever parse one error shape.

**Built-in User model, email as login.** Registration stores the lowercased
email as the username, so emails are unique at the database level and people
log in with email + password. The token serializer accepts `email` instead of
`username`. This avoids a custom user model while keeping the API email-based.

**Config from the environment.** Settings come from environment variables
(`.env` locally, see `.env.example`). SQLite is the zero-setup default and
`DATABASE_URL` switches to PostgreSQL. No secrets are committed.

**Tests run against PostgreSQL in CI.** SQLite is convenient locally, but
constraints and date functions can behave differently, so CI and
`docker compose run --rm tests` use the production database engine.

## Possible next steps

- Rate limiting on the login and register endpoints
- Refresh token rotation and blacklisting on logout
- Production security settings (HTTPS redirect, HSTS, secure cookies) behind a reverse proxy
