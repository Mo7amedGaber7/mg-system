from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os

app = Flask(__name__, static_folder='static')

@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

@app.route('/api/<path:p>', methods=['OPTIONS'])
def options(p):
    return '', 204

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
        type TEXT, platform TEXT, hook TEXT, cta TEXT,
        status TEXT DEFAULT 'متصور',
        week INTEGER DEFAULT 1,
        publish_date TEXT, notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source TEXT, service TEXT, problem TEXT,
        status TEXT DEFAULT 'جديد',
        expected_value REAL DEFAULT 0,
        week INTEGER DEFAULT 1,
        next_step TEXT, notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS outreach (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        platform TEXT, service TEXT,
        reply TEXT DEFAULT 'في الانتظار',
        sent_date TEXT,
        week INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS weekly_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week INTEGER,
        videos_count INTEGER DEFAULT 0,
        outreach_count INTEGER DEFAULT 0,
        new_clients INTEGER DEFAULT 0,
        best_video TEXT, what_worked TEXT,
        what_didnt TEXT, next_changes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# Init DB when module loads — works with gunicorn too
init_db()

# ── STATS ──
@app.route('/api/stats')
def stats():
    conn = get_db()
    c = conn.cursor()
    total_videos  = c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    published     = c.execute("SELECT COUNT(*) FROM videos WHERE status='منشور'").fetchone()[0]
    total_clients = c.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    hot           = c.execute("SELECT COUNT(*) FROM clients WHERE status='مهتم'").fetchone()[0]
    closed        = c.execute("SELECT COUNT(*) FROM clients WHERE status='اتغلق'").fetchone()[0]
    revenue       = c.execute("SELECT COALESCE(SUM(expected_value),0) FROM clients WHERE status='اتغلق'").fetchone()[0]
    pipeline      = c.execute("SELECT COALESCE(SUM(expected_value),0) FROM clients WHERE status NOT IN ('اتغلق','رفض')").fetchone()[0]
    total_or      = c.execute("SELECT COUNT(*) FROM outreach").fetchone()[0]
    positive_or   = c.execute("SELECT COUNT(*) FROM outreach WHERE reply='رد ايجابي'").fetchone()[0]
    pending_or    = c.execute("SELECT COUNT(*) FROM outreach WHERE reply='في الانتظار'").fetchone()[0]
    conn.close()
    return jsonify({
        'videos':   {'total': total_videos, 'published': published, 'target': 40, 'pct': round((published/40)*100) if published else 0},
        'clients':  {'total': total_clients, 'hot': hot, 'closed': closed, 'pipeline': pipeline},
        'revenue':  revenue,
        'outreach': {'total': total_or, 'positive': positive_or, 'pending': pending_or, 'rate': round((positive_or/total_or)*100) if total_or else 0}
    })

# ── VIDEOS ──
@app.route('/api/videos', methods=['GET','POST'])
def videos():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO videos (title,type,platform,hook,cta,status,week,notes) VALUES (?,?,?,?,?,?,?,?)",
            (d.get('title',''), d.get('type',''), d.get('platform',''), d.get('hook',''), d.get('cta',''), d.get('status','متصور'), d.get('week',1), d.get('notes','')))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    rows = conn.execute("SELECT * FROM videos ORDER BY week, id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/videos/<int:vid>', methods=['PUT','DELETE'])
def video_item(vid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM videos WHERE id=?", (vid,))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    d = request.json
    conn.execute("UPDATE videos SET title=?,type=?,platform=?,hook=?,cta=?,status=?,week=?,notes=? WHERE id=?",
        (d.get('title'), d.get('type'), d.get('platform'), d.get('hook'), d.get('cta'), d.get('status'), d.get('week'), d.get('notes'), vid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

# ── CLIENTS ──
@app.route('/api/clients', methods=['GET','POST'])
def clients():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO clients (name,source,service,problem,status,expected_value,week,next_step,notes) VALUES (?,?,?,?,?,?,?,?,?)",
            (d.get('name',''), d.get('source',''), d.get('service',''), d.get('problem',''), d.get('status','جديد'), d.get('expected_value',0), d.get('week',1), d.get('next_step',''), d.get('notes','')))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    rows = conn.execute("SELECT * FROM clients ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/clients/<int:cid>', methods=['PUT','DELETE'])
def client_item(cid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM clients WHERE id=?", (cid,))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    d = request.json
    conn.execute("UPDATE clients SET name=?,source=?,service=?,problem=?,status=?,expected_value=?,week=?,next_step=?,notes=? WHERE id=?",
        (d.get('name'), d.get('source'), d.get('service'), d.get('problem'), d.get('status'), d.get('expected_value',0), d.get('week'), d.get('next_step'), d.get('notes'), cid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

# ── OUTREACH ──
@app.route('/api/outreach', methods=['GET','POST'])
def outreach():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO outreach (name,platform,service,reply,sent_date,week,notes) VALUES (?,?,?,?,?,?,?)",
            (d.get('name',''), d.get('platform',''), d.get('service',''), d.get('reply','في الانتظار'), d.get('sent_date',''), d.get('week',1), d.get('notes','')))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    rows = conn.execute("SELECT * FROM outreach ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/outreach/<int:oid>', methods=['PUT','DELETE'])
def outreach_item(oid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM outreach WHERE id=?", (oid,))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    d = request.json
    conn.execute("UPDATE outreach SET name=?,platform=?,service=?,reply=?,sent_date=?,week=?,notes=? WHERE id=?",
        (d.get('name'), d.get('platform'), d.get('service'), d.get('reply'), d.get('sent_date'), d.get('week'), d.get('notes'), oid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

# ── REVIEWS ──
@app.route('/api/reviews', methods=['GET','POST'])
def reviews():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO weekly_reviews (week,videos_count,outreach_count,new_clients,best_video,what_worked,what_didnt,next_changes) VALUES (?,?,?,?,?,?,?,?)",
            (d.get('week',1), d.get('videos_count',0), d.get('outreach_count',0), d.get('new_clients',0), d.get('best_video',''), d.get('what_worked',''), d.get('what_didnt',''), d.get('next_changes','')))
        conn.commit(); conn.close()
        return jsonify({'ok': True})
    rows = conn.execute("SELECT * FROM weekly_reviews ORDER BY week").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ── SERVE FRONTEND (must be LAST) ──
@app.route('/login.html')
def login_page():
    return send_from_directory('static', 'login.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
