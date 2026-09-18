# Attendly on Supabase

Local SQLite is removed. EXE, school console and parent APK all use one Supabase project.

## 1. Create the project

1. Open [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. New project
3. SQL Editor → paste `supabase/schema.sql` → Run

## 2. Keys

Project Settings → API:

- Project URL → `SUPABASE_URL`
- `service_role` (secret) → `SUPABASE_SERVICE_KEY`

Create `attendly-app/.env`:

```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
ATTENDLY_SECRET=any-long-random-string
```

Put the same `.env` next to `Attendly.exe` when you ship the EXE.

Never put the service role key in the Android app.

## 3. Run

```bat
pip install -r requirements.txt
run.bat
```

First start creates the owner + demo school only if the project is empty (6 students, no fake month of attendance).

## What is stored (kept small)

| Table | Why |
|--------|-----|
| admins / schools / license_keys | logins + membership |
| students | one row per child |
| attendance | one row per child per day (`time_in` / `time_out` only) |
| alerts | one row per school message |
| fcm_tokens | one row per parent phone |

Not stored: parent sessions (signed token), per-parent notification copies, duplicated name/class on attendance.

## Parent APK (direct Supabase — no school PC)

The phone uses the **publishable** key and these RPCs (run `supabase/parent_rpc.sql` once in SQL Editor):

`parent_login`, `parent_today`, `parent_month`, `parent_alerts`, `parent_feed`, `parent_register_fcm`

School EXE still uses the **service_role** key for gate / students / alerts.
