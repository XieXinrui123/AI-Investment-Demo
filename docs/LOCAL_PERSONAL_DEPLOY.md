# Local Personal Deployment

This project is configured as a local personal investment and finance planning workspace.

## What Runs Locally

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Database: `backend/ai_berkshire.db`
- Market data:
  - A-share quotes: Sina Finance free endpoint
  - US/HK quotes: Yahoo Finance chart endpoint

GitHub is used for source code backup and version control. Personal database backups stay local by default.

## First-Time Setup

```bash
chmod +x start.sh scripts/*.sh
./scripts/init_local.sh
./start.sh start
```

Open `http://localhost:3000`.

Default local account:

```text
username: demo
password: demo123456
```

## Daily Use

```bash
./start.sh start
./start.sh status
./start.sh stop
```

## Back Up Personal Data

```bash
./scripts/backup_db.sh
```

Backups are written to `backups/` and ignored by Git.

## Restore Personal Data

```bash
./scripts/restore_db.sh backups/ai_berkshire-YYYYMMDD-HHMMSS.db
```

The restore script creates a safety copy of the current database before replacing it.

## GitHub Strategy

Commit source code and docs to GitHub. Do not commit:

- `backend/ai_berkshire.db`
- `backups/`
- `.env` files
- `node_modules/`
- `.next/`
- `backend/venv/`

This keeps private financial data on your computer while GitHub remains a clean code backup.
