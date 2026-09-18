# Firebase Cloud Messaging (FCM)

Attendly sends parent pushes through Google FCM. You need your own Firebase project — this file is the only setup.

Package name of the parent app: `com.attendly.parent`

## 1. Create the Firebase project

1. Open [https://console.firebase.google.com](https://console.firebase.google.com)
2. Add project → name it **Attendly**
3. You can turn Google Analytics off

## 2. Add the Android app (parent APK)

1. Project overview → **Add app** → Android
2. Android package name: `com.attendly.parent`
3. App nickname: Attendly Parent
4. Register, then download **google-services.json**
5. Save it exactly here:

```
attendly-app/android/app/google-services.json
```

6. In Firebase: **Build → Cloud Messaging** — no extra toggle is required on a new project

## 3. Add the server key (school EXE / Python)

1. Firebase console → gear → **Project settings**
2. **Service accounts** tab
3. **Generate new private key** → download the JSON
4. Rename it and save here:

```
attendly-app/data/firebase-adminsdk.json
```

If you run `Attendly.exe`, put the same file next to the EXE:

```
Attendly.exe
data\firebase-adminsdk.json
data\attendly.db
```

## 4. Rebuild and restart

School / owner:

```bat
pip install -r requirements.txt
run.bat
```

Or close and open `Attendly.exe` again.

Parent APK (after `google-services.json` is in place):

```bat
cd android
build-apk.bat
```

Install the new `Attendly-Parent.apk`.

## 5. Check it

1. School dashboard should show **Firebase FCM on**
2. Open the parent app, sign in, allow notifications
3. Gate reader → tap Aarav (`AT7K2M9Q4X`)
4. Parent phone should get: *Aarav Sharma arrived at school at …*

Until both JSON files are in place, the app still works: it falls back to local polling on the same Wi‑Fi.

Do not commit `google-services.json` or `firebase-adminsdk.json` — they are secrets.
