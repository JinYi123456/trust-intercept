# TRUST//INTERCEPT — Cross-Platform Install Guide (PWA + Android APK + Desktop)

TRUST//INTERCEPT ships as a **universal PWA** (installable on iOS, Android, Windows, macOS,
Linux) and additionally builds a **standalone Android APK** through Capacitor.

---

## 0. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Node.js | 20+ | `node --version` |
| Python | 3.11+ | `python --version` |
| JDK 17 (APK only) | 17 | `java -version` |
| Android SDK (APK only) | latest via Android Studio | `sdkmanager --version` |

Set `ANDROID_HOME` to your SDK path if `gradlew` cannot find it:
`C:\Users\<you>\AppData\Local\Android\Sdk` (Windows) or
`~/Library/Android/sdk` (macOS).

---

## 1. Universal PWA (works everywhere, zero store)

The PWA is already configured (`vite-plugin-pwa`, manifest, service worker,
icons). Install behavior requires **HTTPS or localhost**.

### 1.1 Build and serve

```bash
cd frontend
npm install
npm run icons        # one-time: regenerate PNG icons from favicon.svg
npm run build        # emits dist/ + precache manifest + service worker
npm run preview      # serve the built PWA on http://localhost:5173
```

> For real devices, expose the build over HTTPS (e.g. `npx serve dist` behind a
> tunnel, or any static host). Browsers only offer installation on secure origins.

### 1.2 Install on each platform

- **Windows / macOS / Linux (Chrome, Edge):** click the **⬇ Install App** button
  in the app header (appears automatically), or the browser's install icon in
  the address bar. TRUST//INTERCEPT then runs in its own window from the Start menu /
  Applications folder.
- **Android (Chrome):** same **⬇ Install App** button → "Add to home screen".
- **iOS (Safari):** tap the **⬇ Install App** button for the guided hint, then
  **Share → Add to Home Screen** (iOS does not allow programmatic install).

The service worker (`registerType: "autoUpdate"`) precaches the app shell so
installed TRUST//INTERCEPT opens instantly and shows a friendly offline page when the
backend is unreachable. API responses are never cached — verdicts are always live.

---

## 2. Android APK via Capacitor

### 2.1 One-time setup

```bash
cd frontend
npm install @capacitor/core @capacitor/cli @capacitor/android
```

Configuration already lives in `frontend/capacitor.config.json`
(`appId: com.aegissignallab.trustintercept`, `webDir: dist`).

> **Why `androidScheme: "http"` + `allowMixedContent`:** for the hackathon demo
> the APK talks to the demo backend over plain HTTP on your LAN
> (`http://<your-ip>:8001`). Production apps should serve the API over HTTPS
> and remove these two flags.

### 2.2 Point the app at your backend

The APK's web view must reach FastAPI on your machine. Set the API base URL at
build time:

```bash
# Windows (Git Bash / PowerShell with $env:)
VITE_API_BASE_URL=http://192.168.1.20:8001   # your LAN IP, NOT localhost
npm run build
```

Find your LAN IP: `ipconfig` (Windows) / `ifconfig` (macOS/Linux).
Start the backend with CORS already permissive for demo origins:

```bash
# from the project root
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

### 2.3 Create the Android project and build the APK

```bash
npx cap add android        # one-time: generates frontend/android/
npx cap sync               # copies dist/ + plugins into the native project
cd android
./gradlew assembleDebug    # Windows: gradlew.bat assembleDebug
```

**APK output:**
`frontend/android/app/build/outputs/apk/debug/app-debug.apk`

Install it on a device/emulator:

```bash
adb install app-debug.apk
# or simply open the project in Android Studio and press Run ▶
```

### 2.4 (Optional) Signed release APK

```bash
keytool -genkey -v -keystore trust-intercept-release.keystore -alias trust-intercept \
        -keyalg RSA -keysize 2048 -validity 10000
./gradlew assembleRelease
# sign + align (Android Studio: Build → Generate Signed Bundle/APK automates this)
```

### 2.5 Rebuilding after frontend changes

```bash
npm run build && npx cap sync && cd android && ./gradlew assembleDebug
```

---

## 3. Desktop (Windows / macOS) quick reference

| Channel | Result | Command |
|---|---|---|
| PWA install (recommended) | Standalone window, auto-updating, tiny | `npm run build && npm run preview` → click **⬇ Install App** |
| Android APK | Native installer for phones/tablets | Section 2 |
| iOS | Home-screen PWA | Section 1.2 (Safari) |

---

## 4. Troubleshooting

- **Install button never appears** → the page must be served over HTTPS (or
  localhost) and the manifest + service worker must be reachable; check
  DevTools → Application → Manifest.
- **APK shows "Network error"** → the backend binds `--host 0.0.0.0`, the phone
  is on the same Wi-Fi, `VITE_API_BASE_URL` used your LAN IP at build time, and
  Windows Firewall allows inbound port 8001.
- **`gradlew` not found / SDK errors** → install Android Studio, accept licenses
  (`sdkmanager --licenses`), and set `ANDROID_HOME`.
