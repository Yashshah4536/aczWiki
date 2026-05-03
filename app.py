import os
import socket
import uuid
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db, create_default_admin, now

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Permission denied.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_folders_tree(conn):
    rows = conn.execute("SELECT * FROM folders ORDER BY name").fetchall()
    folders = [dict(r) for r in rows]
    folder_map = {f['id']: f for f in folders}
    for f in folders:
        f['children'] = []
    roots = []
    for f in folders:
        pid = f['parent_id']
        if pid and pid in folder_map:
            folder_map[pid]['children'].append(f)
        else:
            roots.append(f)
    return roots


def get_all_tags(conn):
    rows = conn.execute("SELECT tags FROM articles WHERE tags != ''").fetchall()
    tag_counts = {}
    for row in rows:
        for tag in [t.strip() for t in row['tags'].split(',') if t.strip()]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return tag_counts


def record_view(article_id):
    viewed = session.get('recently_viewed', [])
    if article_id in viewed:
        viewed.remove(article_id)
    viewed.insert(0, article_id)
    session['recently_viewed'] = viewed[:10]


# ── Auth ─────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Home ──────────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    conn = get_db()
    pinned = conn.execute(
        "SELECT a.*, u.username as author FROM articles a LEFT JOIN users u ON a.created_by=u.id WHERE a.is_pinned=1 ORDER BY a.updated_at DESC"
    ).fetchall()
    recent_edited = conn.execute(
        "SELECT a.*, u.username as author FROM articles a LEFT JOIN users u ON a.created_by=u.id ORDER BY a.updated_at DESC LIMIT 8"
    ).fetchall()
    viewed_ids = session.get('recently_viewed', [])
    recently_viewed = []
    for aid in viewed_ids[:6]:
        row = conn.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
        if row:
            recently_viewed.append(row)
    folders = get_folders_tree(conn)
    tags = get_all_tags(conn)
    conn.close()
    return render_template('index.html', pinned=pinned, recent_edited=recent_edited,
                           recently_viewed=recently_viewed, folders=folders, tags=tags)


# ── Search ────────────────────────────────────────────────────────────────────

@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '').strip()
    conn = get_db()
    results = []
    if q:
        try:
            rows = conn.execute(
                "SELECT a.*, u.username as author FROM articles a LEFT JOIN users u ON a.created_by=u.id WHERE a.id IN (SELECT rowid FROM articles_fts WHERE articles_fts MATCH ?) ORDER BY a.updated_at DESC",
                (q + '*',)
            ).fetchall()
            results = rows
        except Exception:
            results = conn.execute(
                "SELECT a.*, u.username as author FROM articles a LEFT JOIN users u ON a.created_by=u.id WHERE a.title LIKE ? OR a.body LIKE ? OR a.tags LIKE ? ORDER BY a.updated_at DESC",
                (f'%{q}%', f'%{q}%', f'%{q}%')
            ).fetchall()
    folders = get_folders_tree(conn)
    tags = get_all_tags(conn)
    conn.close()
    return render_template('search.html', results=results, q=q, folders=folders, tags=tags)


# ── Folders ───────────────────────────────────────────────────────────────────

@app.route('/folder/<int:folder_id>')
@login_required
def folder_view(folder_id):
    conn = get_db()
    folder = conn.execute("SELECT * FROM folders WHERE id=?", (folder_id,)).fetchone()
    if not folder:
        abort(404)
    articles = conn.execute(
        "SELECT a.*, u.username as author FROM articles a LEFT JOIN users u ON a.created_by=u.id WHERE a.folder_id=? ORDER BY a.updated_at DESC",
        (folder_id,)
    ).fetchall()
    folders = get_folders_tree(conn)
    tags = get_all_tags(conn)
    conn.close()
    return render_template('folder.html', folder=folder, articles=articles, folders=folders, tags=tags)


@app.route('/folder/create', methods=['POST'])
@login_required
@role_required('Admin')
def folder_create():
    name = request.form.get('name', '').strip()
    parent_id = request.form.get('parent_id') or None
    if name:
        conn = get_db()
        conn.execute("INSERT INTO folders (name, parent_id, created_at) VALUES (?,?,?)",
                     (name, parent_id, now()))
        conn.commit()
        conn.close()
        flash('Folder created.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/folder/<int:folder_id>/rename', methods=['POST'])
@login_required
@role_required('Admin')
def folder_rename(folder_id):
    name = request.form.get('name', '').strip()
    if name:
        conn = get_db()
        conn.execute("UPDATE folders SET name=? WHERE id=?", (name, folder_id))
        conn.commit()
        conn.close()
        flash('Folder renamed.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/folder/<int:folder_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def folder_delete(folder_id):
    conn = get_db()
    conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
    conn.commit()
    conn.close()
    flash('Folder deleted.', 'success')
    return redirect(url_for('index'))


# ── Articles ──────────────────────────────────────────────────────────────────

@app.route('/article/new', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Editor')
def article_new():
    conn = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '')
        folder_id = request.form.get('folder_id') or None
        tags = request.form.get('tags', '').strip()
        n = now()
        cur = conn.execute(
            "INSERT INTO articles (title, body, folder_id, tags, created_by, created_at, updated_by, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (title, body, folder_id, tags, session['user_id'], n, session['user_id'], n)
        )
        article_id = cur.lastrowid
        conn.execute(
            "INSERT INTO article_versions (article_id, title, body, tags, saved_by, saved_at) VALUES (?,?,?,?,?,?)",
            (article_id, title, body, tags, session['user_id'], n)
        )
        conn.commit()
        conn.close()
        flash('Article created.', 'success')
        return redirect(url_for('article_view', article_id=article_id))
    folders = get_folders_tree(conn)
    tags_cloud = get_all_tags(conn)
    conn.close()
    return render_template('article_edit.html', article=None, folders=folders, tags=tags_cloud)


@app.route('/article/<int:article_id>')
@login_required
def article_view(article_id):
    conn = get_db()
    article = conn.execute(
        "SELECT a.*, u.username as author, u2.username as updater FROM articles a LEFT JOIN users u ON a.created_by=u.id LEFT JOIN users u2 ON a.updated_by=u2.id WHERE a.id=?",
        (article_id,)
    ).fetchone()
    if not article:
        abort(404)
    comments = conn.execute(
        "SELECT c.*, u.username FROM comments c LEFT JOIN users u ON c.user_id=u.id WHERE c.article_id=? ORDER BY c.created_at",
        (article_id,)
    ).fetchall()
    attachments = conn.execute(
        "SELECT * FROM attachments WHERE article_id=? ORDER BY uploaded_at", (article_id,)
    ).fetchall()
    folders = get_folders_tree(conn)
    tags = get_all_tags(conn)
    conn.close()
    record_view(article_id)
    return render_template('article_view.html', article=article, comments=comments,
                           attachments=attachments, folders=folders, tags=tags)


@app.route('/article/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Editor')
def article_edit(article_id):
    conn = get_db()
    article = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    if not article:
        abort(404)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '')
        folder_id = request.form.get('folder_id') or None
        tags = request.form.get('tags', '').strip()
        n = now()
        conn.execute(
            "UPDATE articles SET title=?, body=?, folder_id=?, tags=?, updated_by=?, updated_at=? WHERE id=?",
            (title, body, folder_id, tags, session['user_id'], n, article_id)
        )
        conn.execute(
            "INSERT INTO article_versions (article_id, title, body, tags, saved_by, saved_at) VALUES (?,?,?,?,?,?)",
            (article_id, title, body, tags, session['user_id'], n)
        )
        conn.commit()
        conn.close()
        flash('Article saved.', 'success')
        return redirect(url_for('article_view', article_id=article_id))
    folders = get_folders_tree(conn)
    tags_cloud = get_all_tags(conn)
    conn.close()
    return render_template('article_edit.html', article=article, folders=folders, tags=tags_cloud)


@app.route('/article/<int:article_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def article_delete(article_id):
    conn = get_db()
    conn.execute("DELETE FROM articles WHERE id=?", (article_id,))
    conn.commit()
    conn.close()
    flash('Article deleted.', 'success')
    return redirect(url_for('index'))


@app.route('/article/<int:article_id>/pin', methods=['POST'])
@login_required
@role_required('Admin')
def article_pin(article_id):
    conn = get_db()
    article = conn.execute("SELECT is_pinned FROM articles WHERE id=?", (article_id,)).fetchone()
    if article:
        conn.execute("UPDATE articles SET is_pinned=? WHERE id=?", (0 if article['is_pinned'] else 1, article_id))
        conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('article_view', article_id=article_id))


# ── Version History ───────────────────────────────────────────────────────────

@app.route('/article/<int:article_id>/history')
@login_required
def article_history(article_id):
    conn = get_db()
    article = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    if not article:
        abort(404)
    versions = conn.execute(
        "SELECT v.*, u.username FROM article_versions v LEFT JOIN users u ON v.saved_by=u.id WHERE v.article_id=? ORDER BY v.saved_at DESC",
        (article_id,)
    ).fetchall()
    folders = get_folders_tree(conn)
    tags = get_all_tags(conn)
    conn.close()
    return render_template('history.html', article=article, versions=versions, folders=folders, tags=tags)


@app.route('/article/<int:article_id>/restore/<int:version_id>', methods=['POST'])
@login_required
@role_required('Admin', 'Editor')
def article_restore(article_id, version_id):
    conn = get_db()
    version = conn.execute("SELECT * FROM article_versions WHERE id=? AND article_id=?", (version_id, article_id)).fetchone()
    if not version:
        abort(404)
    n = now()
    conn.execute(
        "UPDATE articles SET title=?, body=?, tags=?, updated_by=?, updated_at=? WHERE id=?",
        (version['title'], version['body'], version['tags'], session['user_id'], n, article_id)
    )
    conn.execute(
        "INSERT INTO article_versions (article_id, title, body, tags, saved_by, saved_at) VALUES (?,?,?,?,?,?)",
        (article_id, version['title'], version['body'], version['tags'], session['user_id'], n)
    )
    conn.commit()
    conn.close()
    flash('Version restored.', 'success')
    return redirect(url_for('article_view', article_id=article_id))


# ── Tags ──────────────────────────────────────────────────────────────────────

@app.route('/tag/<tag>')
@login_required
def tag_view(tag):
    conn = get_db()
    articles = conn.execute(
        "SELECT a.*, u.username as author FROM articles a LEFT JOIN users u ON a.created_by=u.id WHERE (',' || a.tags || ',') LIKE ? ORDER BY a.updated_at DESC",
        (f'%,{tag},%',)
    ).fetchall()
    folders = get_folders_tree(conn)
    tags = get_all_tags(conn)
    conn.close()
    return render_template('tag.html', tag=tag, articles=articles, folders=folders, tags=tags)


# ── Comments ──────────────────────────────────────────────────────────────────

@app.route('/article/<int:article_id>/comment', methods=['POST'])
@login_required
def comment_add(article_id):
    body = request.form.get('body', '').strip()
    if body:
        conn = get_db()
        conn.execute(
            "INSERT INTO comments (article_id, user_id, body, created_at) VALUES (?,?,?,?)",
            (article_id, session['user_id'], body, now())
        )
        conn.commit()
        conn.close()
    return redirect(url_for('article_view', article_id=article_id) + '#comments')


@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def comment_delete(comment_id):
    conn = get_db()
    comment = conn.execute("SELECT * FROM comments WHERE id=?", (comment_id,)).fetchone()
    if comment and (comment['user_id'] == session['user_id'] or session['role'] == 'Admin'):
        article_id = comment['article_id']
        conn.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('article_view', article_id=article_id) + '#comments')
    conn.close()
    flash('Permission denied.', 'error')
    return redirect(url_for('index'))


# ── Attachments ───────────────────────────────────────────────────────────────

@app.route('/article/<int:article_id>/upload', methods=['POST'])
@login_required
@role_required('Admin', 'Editor')
def upload_attachment(article_id):
    f = request.files.get('file')
    if f and f.filename and allowed_file(f.filename):
        original = secure_filename(f.filename)
        ext = original.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn = get_db()
        conn.execute(
            "INSERT INTO attachments (article_id, filename, original_name, uploaded_at) VALUES (?,?,?,?)",
            (article_id, filename, original, now())
        )
        conn.commit()
        conn.close()
        flash('File uploaded.', 'success')
    else:
        flash('Invalid file type.', 'error')
    return redirect(url_for('article_view', article_id=article_id))


@app.route('/uploads/<filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/attachment/<int:attachment_id>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'Editor')
def delete_attachment(attachment_id):
    conn = get_db()
    att = conn.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
    if att:
        article_id = att['article_id']
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], att['filename']))
        except FileNotFoundError:
            pass
        conn.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('article_view', article_id=article_id))
    conn.close()
    abort(404)


# ── Export to PDF ─────────────────────────────────────────────────────────────

@app.route('/article/<int:article_id>/pdf')
@login_required
def article_pdf(article_id):
    from weasyprint import HTML
    conn = get_db()
    article = conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    conn.close()
    if not article:
        abort(404)
    html_content = render_template('pdf_export.html', article=article)
    pdf = HTML(string=html_content, base_url=request.base_url).write_pdf()
    from flask import Response
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="article-{article_id}.pdf"'})


# ── User Management (Admin) ───────────────────────────────────────────────────

@app.route('/admin/users')
@login_required
@role_required('Admin')
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
    folders = get_folders_tree(conn)
    tags = get_all_tags(conn)
    conn.close()
    return render_template('admin_users.html', users=users, folders=folders, tags=tags)


@app.route('/admin/users/create', methods=['POST'])
@login_required
@role_required('Admin')
def admin_user_create():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'Viewer')
    if username and password and role in ('Admin', 'Editor', 'Viewer'):
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
                (username, generate_password_hash(password), role, now())
            )
            conn.commit()
            flash('User created.', 'success')
        except Exception:
            flash('Username already exists.', 'error')
        conn.close()
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def admin_user_delete(user_id):
    if user_id == session['user_id']:
        flash('Cannot delete yourself.', 'error')
        return redirect(url_for('admin_users'))
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
@role_required('Admin')
def admin_user_role(user_id):
    role = request.form.get('role', 'Viewer')
    if role in ('Admin', 'Editor', 'Viewer'):
        conn = get_db()
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        conn.commit()
        conn.close()
        flash('Role updated.', 'success')
    return redirect(url_for('admin_users'))


# ── Profile ───────────────────────────────────────────────────────────────────

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')
        user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
        if not check_password_hash(user['password_hash'], current_pw):
            flash('Current password is incorrect.', 'error')
        elif len(new_pw) < 6:
            flash('New password must be at least 6 characters.', 'error')
        elif new_pw != confirm_pw:
            flash('New passwords do not match.', 'error')
        else:
            conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                         (generate_password_hash(new_pw), session['user_id']))
            conn.commit()
            flash('Password changed successfully.', 'success')
        conn.close()
        return redirect(url_for('profile'))
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    article_count = conn.execute("SELECT COUNT(*) FROM articles WHERE created_by=?", (session['user_id'],)).fetchone()[0]
    comment_count = conn.execute("SELECT COUNT(*) FROM comments WHERE user_id=?", (session['user_id'],)).fetchone()[0]
    folders = get_folders_tree(conn)
    tags = get_all_tags(conn)
    conn.close()
    return render_template('profile.html', user=user, article_count=article_count,
                           comment_count=comment_count, folders=folders, tags=tags)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    create_default_admin()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            local_ip = '127.0.0.1'

    print(f"\n{'='*50}")
    print(f"  AczWiki is running!")
    print(f"  Local:   http://localhost:5000")
    print(f"  Network: http://{local_ip}:5000")
    print(f"  Share this address with others on the LAN:")
    print(f"  --> http://{local_ip}:5000")
    print(f"{'='*50}\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
