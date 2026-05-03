# AczWiki

A LAN-based internal knowledge base web app built with Python Flask and SQLite.

## Stack
- **Backend**: Python 3.11, Flask, SQLite (FTS5 for full-text search)
- **Frontend**: Server-rendered Jinja2 templates, Pico CSS v2 (CDN), Quill.js v2 (CDN), Highlight.js 11.9 (CDN)
- **PDF Export**: WeasyPrint
- **Production Server**: Gunicorn

## Project Structure
```
app.py              — Full Flask backend (all routes)
database.py         — Database init, schema, migrations, helpers
requirements.txt    — Python dependencies
templates/
  base.html             — Layout: navbar, sidebar (quick links, folders, snippets, tags), dark mode
  login.html            — Login page
  index.html            — Home: announcements, pinned, recently edited, recently viewed
  article_view.html     — Article view + reactions + comments + attachments + snippet view
  article_edit.html     — Create/edit: type selector, language, private toggle, Quill + image upload
  history.html          — Version history with preview & restore
  search.html           — Full-text search results
  folder.html           — Articles filtered by folder
  tag.html              — Articles filtered by tag
  snippets.html         — All code snippets with language filter
  announcements.html    — Notice board (Admin can create/pin/delete)
  worklog.html          — Personal daily work log with calendar sidebar
  timesheet.html        — Daily timesheet with hours auto-calc and CSV export
  files.html            — Team file sharing with visibility control
  admin_users.html      — User management (Admin only)
  profile.html          — Profile page + password change
  pdf_export.html       — PDF template for WeasyPrint
uploads/            — All uploaded files (attachments, images, shared files)
knowledge_base.db   — SQLite database
```

## Database Tables
- `users` — username, password_hash, role (Admin/Editor/Viewer)
- `folders` — nested folder tree
- `articles` — title, body, folder_id, tags, is_pinned, is_private, type (article/snippet), language
- `article_versions` — version snapshots per article
- `comments` — per-article comments
- `attachments` — article file attachments
- `reactions` — 👍 Helpful / 👎 Needs Update per user per article (unique)
- `announcements` — notice board posts with pinning
- `work_logs` — personal daily work log entries per user
- `timesheets` — daily login/logout/tasks per user with hours calculation
- `shared_files` — team file sharing with everyone/private visibility
- `articles_fts` — FTS5 virtual table for full-text search

## Features

### Core
- **Auth**: Login, 3 roles (Admin / Editor / Viewer), password change on profile
- **Articles**: Quill.js rich text editor with inline image upload, folders, tags, version history
- **Snippets**: Code snippet type with language selector, Highlight.js syntax highlighting, Copy Code button
- **Private articles**: `🔒` toggle — only creator and Admins can see private content
- **Folder tree**: Nested, Admin can create/rename/delete
- **Tags**: Tag cloud sidebar, per-article tags, tag filtering page
- **Search**: FTS5 full-text search (title, body, tags) with privacy filter

### New Features (batch 2)
- **Reactions**: 👍 Helpful / 👎 Needs Update below each article; one per user, toggleable
- **Announcements** (`/announcements`): Admin posts notices; top 3 shown on homepage; pinning supported
- **Work Log** (`/worklog`): Personal daily entries (work done, blockers, remarks); calendar sidebar; Admin can view all users filtered by date/user
- **Timesheet** (`/timesheet`): Log login/logout times + tasks; auto-calculates hours; Admin sees all with date-range filter + CSV export
- **File Sharing** (`/files`): Upload any file (PDF, image, docx, xlsx, zip, max 20 MB); visibility = everyone or private; download links; Admin sees all
- **Image upload in editor**: Toolbar image button + inline file picker uploads image to `/upload_image` and inserts it directly into Quill

### UI
- **Dark mode**: Toggle in navbar, stored in localStorage
- **LAN access**: Runs on `0.0.0.0:5000`, prints network IP on startup
- **Sidebar**: Quick links, folder tree, snippets list, tag cloud
- **Article meta**: Author, created date, last edited by, last edited date shown below title

## Default Admin
On first run:
- Username: `admin`
- Password: `admin123`

## Running
```
python app.py
```

## Deployment
```
gunicorn --bind=0.0.0.0:5000 --reuse-port app:app
```
