# ResQ AI – Smart First Response for Accident Bystanders

Everything is in this one folder.

## Folder contents
    ResQ-AI/
    ├── server.py          backend: serves the app, saves reports in SQLite (resq.db), optional AI photo check
    ├── run.sh             start on Mac/Linux      (./run.sh)
    ├── run.bat            start on Windows        (double-click)
    ├── README.md          this file
    ├── public/
    │   ├── index.html     bystander app (guides, location, photos, send report)
    │   ├── dashboard.html responder dashboard (live reports, location, photos)
    │   ├── manifest.json  installable app info
    │   └── sw.js          offline support
    └── standalone/
        └── index.html     the same app with NO backend (just open or host the file)

## Quick start (needs Python 3 only, nothing to install)
1. Run `run.bat` (Windows) or `./run.sh` (Mac/Linux), or `python3 server.py`
2. App:       http://localhost:8000
3. Dashboard: http://localhost:8000/dashboard.html

## Open on other devices (phone, laptop, a friend far away)
Phones allow location and camera only on HTTPS pages. Easiest options:
- Free tunnel: `cloudflared tunnel --url http://localhost:8000` (or `ngrok http 8000`), then share the printed URL
- Permanent: deploy to Render, Railway or Fly.io with start command `python3 server.py`
- No backend needed? Drag the `standalone` folder onto https://app.netlify.com/drop

## Features
- One-tap Call 112, live location (Open in Maps, Copy link, Share)
- 8 step-by-step guides: scene safety, CPR (with 110 BPM beat), heavy bleeding, neck/spine injury, burns, broken bones, choking, seizures
- Describe the situation in words or tap a card; read-aloud voice; light and dark mode; offline after first load
- Scene photos saved on the device, with a Check button
- Send report with location, note and latest photo to the server; dashboard with Mark handled

## Optional AI photo check (server)
    export ANTHROPIC_API_KEY=your-key      (Windows: set ANTHROPIC_API_KEY=your-key)
    python3 server.py
Without a key the Check button shows a "not configured" message.

## API
GET /api/health · POST /api/reports · GET /api/reports · GET /api/photos/<id> · POST /api/reports/<id>/handled · POST /api/check

## Before real use
Add dashboard login, HTTPS, rate limits, photo retention and privacy consent. Have a medical professional review every first aid step. Prototype only; not a substitute for emergency services.
