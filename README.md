# Attendly

NFC school attendance. A tag on the student’s bag, a tap at the school gate, and a push on the parent phone.

This folder is the working product:

- **School + owner desktop** — Flask console, packaged as `Attendly.exe`
- **Parent Android app** — `android/` (APK)
- **Supabase** — one cloud database (see [SUPABASE.md](SUPABASE.md))

Hardware is not required yet. The gate reader accepts a typed NFC tag, student ID, or name.

## Roles

| Role | Where | Login |
|------|--------|--------|
| Owner (superadmin) | Desktop | `owner` / `Attendly@2026` |
| School | Desktop | `greenspring` / `School@123` |
| Parent | Android | School **Green Spring Public School**, phone **9876543210**, DOB **12/04/2016** (Aarav) |

Aarav and Anaya share the same parent phone. After login, switch children from the dropdown.

## Run the school / owner console

Windows:

```bat
run.bat
```

Linux / WSL:

```bash
chmod +x run.sh
./run.sh
```

Opens http://127.0.0.1:5055

The parent app talks to the same process on the LAN, e.g. `http://192.168.1.10:5055`.

## Build the Windows EXE

On Windows:

```bat
build_exe.bat
```

Output: `dist\Attendly.exe`.

Copy `.env.example` to `.env`, add your Supabase URL and service role key, then start. Schema: `supabase/schema.sql`. Details: [SUPABASE.md](SUPABASE.md).

## Parent APK

```bat
cd android
setup-and-build.bat
```

Or from this folder after Gradle is ready:

```bash
cd android && ./gradlew assembleRelease
```

Install `android/app/build/outputs/apk/release/app-release.apk`.

On a **real phone**, School PC address is your Windows Wi‑Fi IP, not `10.0.2.2`:

```
http://192.168.1.8:5055
```

Same Wi‑Fi as the PC. Keep `run.bat` or `Attendly.exe` running. First time, right‑click `open-phone-access.bat` → Run as administrator (Windows Firewall).

## Firebase push (FCM)

Arrival, left-school, and school alerts go through **Google Firebase Cloud Messaging**.

1. Put `android/app/google-services.json` from the Firebase Android app (`com.attendly.parent`)
2. Put `data/firebase-adminsdk.json` from Firebase → Project settings → Service accounts
3. Restart the school server and rebuild the APK

Full steps: [FIREBASE.md](FIREBASE.md)

Without those two files the product still runs; the parent app polls the school PC instead.

## What each screen does

**School**

- Gate reader — simulate NFC tap (in / out). Parent gets “Aarav arrived at school at 8:10 AM” or “left school at …”
- Students — class sort, search, pagination, NFC tag, parent phone, DOB
- Attendance — green present / red absent, manual in / out / absent, Excel download
- Parent alerts — 20 ready messages plus a custom box
- Membership — paste an owner-generated code

**Owner**

- Dashboard of every school and days remaining
- Extend a plan directly, or generate `XXXX-XXXX-XXXX-XXXX` codes
- Enable / disable / delete schools

Passwords are hashed. Database stays local for now.
