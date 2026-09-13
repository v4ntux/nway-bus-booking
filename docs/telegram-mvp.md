# NWay Telegram MVP

The bot works entirely in Telegram: `/start` → origin → destination → date → trip → seat → own contact → passenger → confirmation → PNG ticket. One passenger per order; use “Ещё один билет” for a companion. Russian interface, departure-city local time, cash at boarding. A confirmed reservation is **unpaid** until staff records the received money.

`/tickets` lists the user's last ten bookings. They can resend a ticket and cancel an unpaid booking before departure. Cancellation releases the seat and invalidates the QR. The contact-share button must contain the sender's own Telegram user ID. Bot bookings cannot be fetched or cancelled anonymously through public API codes.

## Staff

`/admin` asks for the staff member's own Telegram contact and checks the existing NWay user role. It never grants roles. Use the phone belonging to an existing operator, admin, superadmin or driver. Company boundaries apply to every action. Staff can view bookings, record received cash (operator/admin), and confirm boarding. Scan a PNG ticket's QR with a phone camera: its Telegram link opens the protected ticket check. `/check TICKET_ID` also works. Scanning alone does not mark a ticket used; the staff member confirms boarding with a button.

Example ticket (sample data, not valid for travel):

![NWay demo ticket](assets/ticket-demo.png)

## Deployment

The existing API service also runs the Telegram worker; no extra bot service is needed. The Docker image includes the Cyrillic font and PNG/QR libraries. Startup runs migration `0003_telegram_mvp` before the worker starts.

Backend Railway variables:

```ini
DATABASE_URL=${{Postgres.DATABASE_URL}}
TELEGRAM_BOT_ENABLED=true
TELEGRAM_BOT_TOKEN=<BotFather token>
TELEGRAM_WEBHOOK_SECRET=<random 32+ character URL-safe secret>
TELEGRAM_DEMO_MODE=true
ALLOW_MOCK_PAYMENTS=false
DEBUG=false
```

`TELEGRAM_SUPPORT` is optional contact text supplied by the operator. `TELEGRAM_BOOKING_CUTOFF_MINUTES` defaults to 30. Configure a non-default `JWT_SECRET`. Keep secrets in Railway variables; never commit them.

After deployment, register the webhook using a shell with backend environment variables:

```sh
python -m app.cli telegram-webhook --url https://YOUR-BACKEND.up.railway.app
```

The endpoint `/telegram/webhook` validates Telegram's secret header, stores incoming updates in PostgreSQL and responds quickly. Duplicate update IDs are ignored. One worker holds a PostgreSQL advisory lock even during deployment overlap. Conversation state, a unique checkout request key and a ticket delivery queue survive restarts. Delivery retries up to eight times; “Отправить билет картинкой” resets a failed delivery. A network failure after Telegram accepted a photo can result in a duplicate photo, but cannot create a second reservation.

The worker expires old unconfirmed holds every 30 seconds. Successfully processed inbox payloads are removed immediately; deduplication IDs are retained for seven days. Logs contain identifiers and error types, not bot tokens, phone numbers or HTTP request URLs.

## Before real passenger sales

The initial database contains **sample cities, buses and trips**. `TELEGRAM_DEMO_MODE=true` visibly labels the bot and PNG tickets as demo. Replace the seeded timetable, operator and boarding locations with actual operating data using the admin API before setting it to false. Ensure a staff member can enter `/admin` and check boarding. The seed only creates ten days of trips; staff must maintain the future timetable. No payment gateway is connected: Payme/Click/card implementations are stubs and disabled by default. The booking bot does not offer them.

## Verification

Run from `backend` against a local test database:

```sh
python -m pytest -q
```

Tests cover the full conversation across new DB sessions, duplicate checkout taps, PNG delivery and retry, contact ownership, booking privacy, cancellation/QR invalidation, webhook authentication/deduplication, staff scope, and cash payment recording. The test suite must never use a production database.
