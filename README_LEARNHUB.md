# LearnHub FastAPI Backend

## Demo accounts

All seeded accounts use password: `password`.

- Admin: `admin@learnhub.com`
- CML: `cml@learnhub.com`
- Trainee: `john@example.com`, `sarah@example.com`

## Windows PowerShell setup

```powershell
cd C:\myprojects\files\learnhub_deliverable\api
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.sample .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:123456@localhost:5432/learnhub
JWT_SECRET=change-this-super-secret-key
SEED_ON_STARTUP=true
```

Run:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Docs: `http://localhost:8000/docs`

## Optional PostgreSQL migration

```powershell
psql -U postgres -d learnhub -f migrations/001_learnhub_schema.sql
```

The app also runs `Base.metadata.create_all()` during startup, so the SQL file is optional for local development.

## Pytest

```powershell
python -m pytest -v tests/test_learnhub_smoke.py
```
