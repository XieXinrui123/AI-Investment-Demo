# GitHub Sync

Use GitHub for source code backup and free CI checks. Keep personal database files local.

## Create the Repository

1. Open `https://github.com/new`.
2. Create an empty repository, for example `ai-berkshire-personal`.
3. Do not add a README, `.gitignore`, or license on GitHub because this local project already has them.

## Push This Local Project

Replace `YOUR_USERNAME` and repository name as needed:

```bash
git remote add origin https://github.com/YOUR_USERNAME/ai-berkshire-personal.git
git push -u origin main
```

## What Will Be Uploaded

Uploaded:

- Source code
- Local deployment scripts
- Documentation
- GitHub Actions workflow

Not uploaded:

- `backend/ai_berkshire.db`
- `backups/`
- `backend/.env`
- `frontend/.env.local`
- `frontend/.next/`
- `frontend/node_modules/`
- `backend/venv/`

## Daily Backup Pattern

Before large edits or after adding important personal records:

```bash
./scripts/backup_db.sh
git status
git add .
git commit -m "Update personal app"
git push
```

The database backup remains local unless you intentionally move it elsewhere.
