from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')

@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r


DB = os.path.join(os.path.dirname(__file__), 'dashboard.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        type TEXT,
        platform TEXT,
        hook TEXT,
        cta TEXT,
        status TEXT DEFAULT 'متصور 🎬',
        week INTEGER DEFAULT 1,
        publish_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source TEXT,
        service TEXT,
        problem TEXT,
        status TEXT DEFAULT 'جديد 🆕',
        expected_value REAL DEFAULT 0,
        week INTEGER DEFAULT 1,
        next_step TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS outreach (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        platform TEXT,
        service TEXT,
        reply TEXT DEFAULT 'في الانتظار ⏳',
        sent_date TEXT,
        week INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()


# ── API ──
@app.route('/api/videos', methods=['GET','POST'])
def videos():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO videos (title,type,platform,hook,cta,status,week,notes) VALUES (?,?,?,?,?,?,?,?)",
            (d.get('title',''), d.get('type',''), d.get('platform',''), d.get('hook',''), d.get('cta',''), d.get('status','متصور 🎬'), d.get('week',1), d.get('notes','')))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    rows = conn.execute("SELECT * FROM videos ORDER BY week, id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── SERVE FRONTEND ──
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    return send_from_directory('static', 'index.html')


@app.route('/login.html')
def login_page():
    return send_from_directory('static', 'login.html')


# 🚀 IMPORTANT FOR RENDER
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)