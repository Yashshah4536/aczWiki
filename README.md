# AczWiki

A lightweight, LAN-based internal knowledge base for your team — built with Python Flask and SQLite. No cloud, no subscriptions, runs entirely on your local network.

---

## Features

1. **Articles** — Rich text editor (Quill.js), folders, tags, version history, PDF export
2. **Code Snippets** — Syntax-highlighted code blocks with language selector and Copy Code button
3. **Private Articles** — 🔒 toggle makes content visible only to the author and Admins
4. **Article Reactions** — 👍 Helpful / 👎 Needs Update buttons per article
5. **Announcements** — Admin-only notice board; top 3 pinned posts shown on homepage
6. **Daily Work Log** — Personal log (work done, blockers, remarks) with a calendar sidebar
7. **Timesheet** — Log daily login/logout times; hours auto-calculated; Admin CSV export
8. **Team File Sharing** — Upload any file (PDF, image, docx, xlsx, zip) with public or private visibility

### Also included
- Three user roles: **Admin**, **Editor**, **Viewer**
- Full-text search (SQLite FTS5)
- Comments on articles
- File attachments per article
- Dark mode toggle
- User management (Admin only)

---

## Requirements

- Python 3.8 or newer
- pip (comes with Python)

---

## Install & Run Locally (Windows)

```bat
git clone <your-repo-url> AczWiki
cd AczWiki
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

**Default login:**
- Username: `admin`
- Password: `admin123`

> Change the admin password immediately after first login via the Profile page.

---

## Run on LAN (share with teammates)

1. On the server PC, open **Command Prompt** and run:
   ```
   ipconfig
   ```
   Find your **IPv4 Address** (e.g. `192.168.1.42`).

2. Start the server:
   ```
   python app.py
   ```
   The startup message will also print your LAN address automatically.

3. Share the address with teammates:
   ```
   http://192.168.1.42:5000
   ```
   They open it in any browser — **no installation needed on their side**.

> Make sure Windows Firewall allows Python on port 5000, or allow it for the local network when prompted.

---

## Auto-start on Windows Boot

1. Double-click `start_server.bat` to confirm it works.
2. Press `Win + R`, type `shell:startup`, press Enter.
3. Copy (or create a shortcut to) `start_server.bat` into that Startup folder.

AczWiki will now launch automatically whenever the PC boots.

---

## Folder Structure

```
AczWiki/
├── app.py              — All Flask routes and business logic
├── database.py         — Database schema, migrations, helpers
├── requirements.txt    — Python dependencies
├── start_server.bat    — Windows launcher (double-click to start)
├── backup.bat          — Windows backup script
├── templates/          — Jinja2 HTML templates
│   ├── base.html           Shared layout (navbar, sidebar, dark mode)
│   ├── index.html          Homepage
│   ├── article_view.html   Article / snippet view
│   ├── article_edit.html   Article / snippet editor
│   ├── worklog.html        Daily work log
│   ├── timesheet.html      Timesheet
│   ├── files.html          Team file sharing
│   ├── announcements.html  Notice board
│   └── ...
├── uploads/            — All uploaded files (attachments, shared files, images)
└── knowledge_base.db   — SQLite database (all your data lives here)
```

---

## Backing Up Your Data

All data lives in two places:

| What | Where |
|------|--------|
| All articles, users, logs | `knowledge_base.db` |
| All uploaded files | `uploads/` folder |

**Manual backup:** Run `backup.bat` — it creates a timestamped folder under `backups/`.

**Scheduled backup:** Open Windows Task Scheduler → Create Basic Task → Action: run `backup.bat` → set your preferred schedule.

---

## User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Everything: manage users, create/edit/delete any article, post announcements, view all worklogs and timesheets |
| **Editor** | Create and edit articles/snippets, upload files, add comments, log work and time |
| **Viewer** | Read articles, add comments, log their own work/time, upload shared files |
