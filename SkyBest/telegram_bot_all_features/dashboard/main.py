
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Template
import sqlite3
import os
import csv
import io
import requests

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")
BROADCAST_API = os.getenv("BROADCAST_API")  # Optional bot endpoint for broadcasting

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <style>
        body { background: #111; color: #eee; font-family: sans-serif; padding: 2em; }
        input, button, select { padding: 10px; margin: 5px; }
        table { width: 100%%; margin-top: 2em; border-collapse: collapse; }
        td, th { padding: 10px; border: 1px solid #444; }
    </style>
</head>
<body>
<h1>🛠 Admin Dashboard</h1>

<p>
<b>📊 Total Users:</b> {{ stats.total_users }} |
<b>🌐 Top Lang:</b> {{ stats.top_lang }} |
<b>🔁 Referrals:</b> {{ stats.referrals }} |
<a href="/export">⬇ Export CSV</a>
</p>

<form method="post" action="/broadcast">
    <input type="text" name="message" placeholder="Broadcast message..." style="width:60%%">
    <button type="submit">Send</button>
</form>

<h2>👥 Users</h2>
<form method="get" action="/">
<input type="text" name="search" placeholder="Search ID or username">
<button type="submit">🔍 Search</button>
</form>

<table>
<tr><th>ID</th><th>Username</th><th>XP</th><th>Level</th><th>Lang</th><th>Blocked</th><th>Action</th></tr>
{% for u in users %}
<tr>
    <form method="post" action="/edit">
    <td>{{u[0]}}<input type="hidden" name="id" value="{{u[0]}}"></td>
    <td>{{u[1] or 'N/A'}}</td>
    <td><input type="number" name="xp" value="{{u[2]}}"></td>
    <td><input type="number" name="level" value="{{u[3]}}"></td>
    <td><select name="lang">
        {% for lang in ['en','ru','hy','fr'] %}
        <option value="{{lang}}" {% if lang == u[4] %}selected{% endif %}>{{lang}}</option>
        {% endfor %}
    </select></td>
    <td>{{ 'Yes' if u[5] else 'No' }}</td>
    <td>
        <button type="submit">💾 Save</button>
        <a href="/block/{{u[0]}}" style="color:yellow;">{{ 'Unblock' if u[5] else 'Block' }}</a>
    </td>
    </form>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

LOGIN_PAGE = """<html><body style="padding:4em;font-family:sans-serif;background:#111;color:#eee">
<h2>🔐 Login</h2>
<form method="post" action="/login">
    <input type="password" name="password" placeholder="Admin password" style="padding:10px">
    <button type="submit" style="padding:10px">Login</button>
</form>
</body></html>"""

def is_logged_in(request: Request):
    return request.session.get("logged_in", False)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, search: str = ""):
    if not is_logged_in(request):
        return HTMLResponse(LOGIN_PAGE)

    conn = sqlite3.connect("botdata.db")
    cur = conn.cursor()
    if search:
        cur.execute("SELECT id, username, xp, level, lang, blocked FROM users WHERE id LIKE ? OR username LIKE ?",
                    (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT id, username, xp, level, lang, blocked FROM users ORDER BY xp DESC")
    users = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT lang, COUNT(*) FROM users GROUP BY lang ORDER BY COUNT(*) DESC LIMIT 1")
    top_lang = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM referrals")
    referrals = cur.fetchone()[0]

    conn.close()
    return Template(HTML_TEMPLATE).render(users=users, stats={
        "total_users": total_users,
        "top_lang": top_lang[0] if top_lang else "N/A",
        "referrals": referrals[0]
    })

@app.post("/login")
def login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASS:
        request.session["logged_in"] = True
    return RedirectResponse("/", status_code=302)

@app.post("/broadcast")
def broadcast(request: Request, message: str = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/", status_code=302)
    print(f"[Broadcast] {message}")
    if BROADCAST_API:
        try:
            requests.post(BROADCAST_API, json={"message": message})
        except Exception as e:
            print(f"Broadcast failed: {e}")
    return RedirectResponse("/", status_code=302)

@app.post("/edit")
def edit_user(id: int = Form(...), xp: int = Form(...), level: int = Form(...), lang: str = Form(...)):
    conn = sqlite3.connect("botdata.db")
    cur = conn.cursor()
    cur.execute("UPDATE users SET xp=?, level=?, lang=? WHERE id=?", (xp, level, lang, id))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=302)

@app.get("/block/{user_id}")
def toggle_block(user_id: int):
    conn = sqlite3.connect("botdata.db")
    cur = conn.cursor()
    cur.execute("SELECT blocked FROM users WHERE id=?", (user_id,))
    current = cur.fetchone()
    new_status = 0 if current and current[0] else 1
    cur.execute("UPDATE users SET blocked=? WHERE id=?", (new_status, user_id))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=302)

@app.get("/export")
def export_csv():
    conn = sqlite3.connect("botdata.db")
    cur = conn.cursor()
    cur.execute("SELECT id, username, xp, level, lang, blocked FROM users")
    users = cur.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "username", "xp", "level", "lang", "blocked"])
    writer.writerows(users)
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=users.csv"})
