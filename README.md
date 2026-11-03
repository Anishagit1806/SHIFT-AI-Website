# SHIFT AI – Agent Design & Crisis Adaptation Challenge

A starter Flask website for the NEXORA SHIFT AI event. Teams register, select one of 10 challenge cards, choose AI/Human mode, submit a structured agent design, and later submit a crisis adaptation. Organizers control submission windows and review/export entries.

## 1. Requirements
- Python 3.10 or newer
- Visual Studio Code
- Internet is only needed to install Flask and load the optional Google Fonts stylesheet. After installation, the app itself works on your local network.

## 2. Run in VS Code (Windows)
1. Extract this ZIP.
2. Open the extracted `SHIFT_AI_Website` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .venv\Scripts\Activate.ps1
   ```

5. Install Flask:

   ```powershell
   pip install -r requirements.txt
   ```

6. Start the website:

   ```powershell
   python app.py
   ```

7. On the laptop, open: `http://127.0.0.1:5000`

## 3. Organizer login
- Login ID: `admin`
- Password: `shiftai2026`

Change the organizer password before using this beyond a private test. On Windows PowerShell, set it before the first run:

```powershell
$env:SHIFT_AI_ADMIN_PASSWORD="YourStrongPassword"
python app.py
```

If the database has already been created, changing the environment variable will not change the existing admin password. For a fresh test database, stop the app and delete `shift_ai.db`, then start it again after setting the environment variable. Deleting the database deletes all registrations and submissions.

## 4. Participant access on the same Wi-Fi
The app listens on `0.0.0.0:5000`, so phones connected to the same Wi-Fi/hotspot can open it.

1. Find your laptop's local IPv4 address:
   ```powershell
   ipconfig
   ```
2. Find the active Wi-Fi adapter's IPv4 Address, for example `192.168.1.5`.
3. Participants open `http://192.168.1.5:5000` on their phones.
4. Allow Python through Windows Firewall on private networks if prompted.

All devices must be on the same local network. Do not share the admin password with participants.

## 5. Event workflow
1. Teams register using one shared team account.
2. Each team chooses one of the 10 challenges and AI Mode or Human Mode. Multiple teams may choose the same challenge. A team's own selection is locked after confirmation.
3. Organizer dashboard: open/close initial submissions.
4. Teams submit the initial agent design. Optional attachments: PNG/JPG/WEBP/PDF/MP4/MOV/WEBM.
5. Organizer closes initial submissions, then clicks **Release crisis & open response**.
6. Each team sees the crisis matching its selected challenge and submits its revised agent design.
7. Organizer reviews entries and exports a CSV.

## 6. Important notes / limitations
- This is a starter event website, not a production-secure public website.
- It does not build or execute agents. Teams submit an agent design and may attach diagrams/videos.
- Every team can select the same challenge; the selection is locked only for that team.
- Each stage can be submitted once; there is no participant editing after submission.
- Uploads are stored in `static/uploads`; the SQLite database is `shift_ai.db`.
- The upload limit is 100 MB per request. For a live event, consider lowering this or setting a specific video limit.
- The app currently has organizer review pages, but no separate judge accounts, scoring rubric, leaderboard, email/OTP verification, or automated timer. These can be added in a next version.
- Do not expose this development server directly to the public internet. For public hosting, use a production server, HTTPS, secure secret key, backups, and stronger access controls.
- The crisis text is visible in the organizer code. Do not give participants access to the project files.
