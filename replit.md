# Knowledge Base

A LAN-based internal knowledge base web app built with Python Flask and SQLite.

## Stack
- **Backend**: Python 3.11, Flask, SQLite (FTS5 for full-text search)
- **Frontend**: Server-rendered Jinja2 templates, Pico CSS (CDN), Quill.js (CDN)
- **PDF Export**: WeasyPrint
- **Production Server**: Gunicorn

## Project Structure
```
app.py           — Full Flask backend (all routes)
database.py      — Database initialization, schema, helpers
requirements.txt — Python dependencies
templates/       — Jinja2 HTML templates
  base.html          — Layout: navbar, sidebar (folders + tag cloud), dark mode
  login.html         — Login page
  index.html         — Home: pinned, recently edited, recently viewed
  article_view.html  — Article view + comments + attachments
  article_edit.html  — Create/edit with Quill.js rich text editor
  history.html       — Version history with preview & restore
  search.html        — Full-text search results
  folder.html        — Articles filtered by folder
  tag.html           — Articles filtered by tag
  admin_users.html   — User management (Admin only)
  pdf_export.html    — PDF template for WeasyPrint
uploads/         — Uploaded file attachments (gitignored)
knowledge_base.db — SQLite database (gitignored)
```

## Features
- **Auth**: Username/password login, three roles (Admin, Editor, Viewer)
- **Articles**: Rich text editor (Quill.js), folders, tags, version history
- **Folder tree**: Nested folders in sidebar, Admin can create/rename/delete
- **Tags**: Comma-separated tags per article, tag cloud in sidebar, tag filtering
- **Search**: Real-time full-text search using SQLite FTS5 (title, body, tags)
- **Version history**: Every save snapshots the article; users can preview & restore
- **Homepage**: Pinned articles, recently edited, recently viewed (session-based)
- **File attachments**: Upload images/PDFs, served by Flask
- **Comments**: Per-article comments, users can delete their own, Admins can delete any
- **PDF export**: WeasyPrint generates downloadable PDF from article content
- **Dark mode**: Toggle button in navbar, preference stored in localStorage
- **LAN access**: Runs on 0.0.0.0:5000, prints local IP on startup

## Default Admin
On first run, a default admin is auto-created:
- Username: `admin`
- Password: `admin123`

## Running
```
python app.py
```

## Deployment
Configured for Gunicorn autoscale deployment:
```
gunicorn --bind=0.0.0.0:5000 --reuse-port app:app
```
