# Telegram Subscription Bot (aiogram v3)

## Quick start (dev)
```bash
cp .env.example .env
# fill BOT_TOKEN and OWNER_ID, set Postgres/Redis if needed
docker-compose up --build
# bot runs in app-bot, web server at http://localhost:8080 in app-web
```
## Migrations
We create tables on startup for dev. Alembic scaffolding is included (app/migrations).

## Fake payments
Open `/payments/fake/pay?invoice_id=...` or use in-bot button to simulate payment.
