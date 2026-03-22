from flask import Flask, request, jsonify, send_from_directory
import sqlite3, os, json

app = Flask(__name__, static_folder='static')

@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

@app.route('/api/<path:p>', methods=['OPTIONS'])
def options(p): return '', 204

DB = os.path.join(os.path.dirname(__file__), 'dashboard.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        type TEXT, platform TEXT, hook TEXT, cta TEXT,
        status TEXT DEFAULT 'متصور', week INTEGER DEFAULT 1,
        publish_date TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        source TEXT, service TEXT, problem TEXT,
        status TEXT DEFAULT 'جديد', expected_value REAL DEFAULT 0,
        week INTEGER DEFAULT 1, next_step TEXT, notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS outreach (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        platform TEXT, service TEXT, reply TEXT DEFAULT 'في الانتظار',
        sent_date TEXT, week INTEGER DEFAULT 1, notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS weekly_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, week INTEGER,
        videos_count INTEGER DEFAULT 0, outreach_count INTEGER DEFAULT 0,
        new_clients INTEGER DEFAULT 0, best_video TEXT,
        what_worked TEXT, what_didnt TEXT, next_changes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS checklists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL, title TEXT NOT NULL,
        items TEXT DEFAULT '[]',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute("SELECT COUNT(*) FROM checklists")
    if c.fetchone()[0] == 0:
        defaults = [
            ('يومي','روتين الصبح — 30 دقيقة',[{"text":"رد على كومنتات الفيديوهات","assignee":""},{"text":"تفاعل في 3 Groups","assignee":""},{"text":"تعليق استراتيجي على 3 بوستات","assignee":""},{"text":"بص على أداء الفيديوهات امبارح","assignee":""}]),
            ('يومي','روتين الضهر — 60 دقيقة',[{"text":"تصوير فيديوين","assignee":""},{"text":"مونتاج سريع","assignee":""},{"text":"نشر على المنصات الـ3","assignee":""},{"text":"رد على الرسايل الجديدة","assignee":""}]),
            ('يومي','روتين الليل — 45 دقيقة',[{"text":"بعت 4-5 رسايل Outreach","assignee":""},{"text":"سجل المحادثات الجديدة","assignee":""},{"text":"اكتب سكريبتات بكره","assignee":""},{"text":"مراجعة أداء اليوم","assignee":""}]),
            ('أسبوعي','تشيكليست اسبوع 1 — التأسيس',[{"text":"إنشاء البروفايلات على الـ3 منصات","assignee":""},{"text":"تحويل الأعمال السابقة لـ3 Case Studies","assignee":""},{"text":"تصوير 10 فيديوهات batch","assignee":""},{"text":"الانضمام لـ5 Facebook Groups","assignee":""},{"text":"إنشاء ليستة 20 شخص للـ Outreach","assignee":""}]),
            ('أسبوعي','تشيكليست اسبوع 2 — التفعيل',[{"text":"نشر فيديوين يومياً","assignee":""},{"text":"رد على كل كومنت في أول ساعة","assignee":""},{"text":"بعت 20 رسالة Outreach جديدة","assignee":""},{"text":"تقديم 3 تقييمات مجانية","assignee":""},{"text":"تحليل أفضل فيديو اشتغل","assignee":""}]),
            ('محتوى','أفكار فيديوهات — ويب سايتس',[{"text":"دفعت فلوس على موقع ومحدش دخله غيرك","assignee":""},{"text":"3 أسئلة قبل ما تعمل أي موقع","assignee":""},{"text":"الفرق بين موقع عادي وموقع بيبيع","assignee":""},{"text":"3 أخطاء بتخلي الزائر يمشي في 5 ثواني","assignee":""}]),
            ('محتوى','أفكار فيديوهات — سيستمز',[{"text":"لو بتعمل الرواتب على Excel — ده وجعك","assignee":""},{"text":"3 علامات إن شركتك محتاجة سيستم دلوقتي","assignee":""},{"text":"الفرق بين شركة بسيستم وشركة من غير سيستم","assignee":""},{"text":"عميل كان بيخسر 3 ساعات يومياً","assignee":""}]),
        ]
        for cat, title, items in defaults:
            c.execute("INSERT INTO checklists (category,title,items) VALUES (?,?,?)",(cat,title,json.dumps(items,ensure_ascii=False)))
    conn.commit(); conn.close()

init_db()

@app.route('/api/stats')
def stats():
    conn = get_db(); c = conn.cursor()
    published   = c.execute("SELECT COUNT(*) FROM videos WHERE status='منشور'").fetchone()[0]
    total_v     = c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    total_cl    = c.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    hot         = c.execute("SELECT COUNT(*) FROM clients WHERE status='مهتم'").fetchone()[0]
    closed      = c.execute("SELECT COUNT(*) FROM clients WHERE status='اتغلق'").fetchone()[0]
    revenue     = c.execute("SELECT COALESCE(SUM(expected_value),0) FROM clients WHERE status='اتغلق'").fetchone()[0]
    pipeline    = c.execute("SELECT COALESCE(SUM(expected_value),0) FROM clients WHERE status NOT IN ('اتغلق','رفض')").fetchone()[0]
    total_or    = c.execute("SELECT COUNT(*) FROM outreach").fetchone()[0]
    positive_or = c.execute("SELECT COUNT(*) FROM outreach WHERE reply='رد ايجابي'").fetchone()[0]
    pending_or  = c.execute("SELECT COUNT(*) FROM outreach WHERE reply='في الانتظار'").fetchone()[0]
    conn.close()
    return jsonify({'videos':{'total':total_v,'published':published,'target':40,'pct':round((published/40)*100) if published else 0},'clients':{'total':total_cl,'hot':hot,'closed':closed,'pipeline':pipeline},'revenue':revenue,'outreach':{'total':total_or,'positive':positive_or,'pending':pending_or,'rate':round((positive_or/total_or)*100) if total_or else 0}})

@app.route('/api/videos', methods=['GET','POST'])
def videos():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO videos (title,type,platform,hook,cta,status,week,notes) VALUES (?,?,?,?,?,?,?,?)",(d.get('title',''),d.get('type',''),d.get('platform',''),d.get('hook',''),d.get('cta',''),d.get('status','متصور'),d.get('week',1),d.get('notes','')))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    rows = conn.execute("SELECT * FROM videos ORDER BY week,id DESC").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/videos/<int:vid>', methods=['PUT','DELETE'])
def video_item(vid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM videos WHERE id=?",(vid,)); conn.commit(); conn.close(); return jsonify({'ok':True})
    d = request.json
    conn.execute("UPDATE videos SET title=?,type=?,platform=?,hook=?,cta=?,status=?,week=?,notes=? WHERE id=?",(d.get('title'),d.get('type'),d.get('platform'),d.get('hook'),d.get('cta'),d.get('status'),d.get('week'),d.get('notes'),vid))
    conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/clients', methods=['GET','POST'])
def clients():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO clients (name,source,service,problem,status,expected_value,week,next_step,notes) VALUES (?,?,?,?,?,?,?,?,?)",(d.get('name',''),d.get('source',''),d.get('service',''),d.get('problem',''),d.get('status','جديد'),d.get('expected_value',0),d.get('week',1),d.get('next_step',''),d.get('notes','')))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    rows = conn.execute("SELECT * FROM clients ORDER BY id DESC").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/clients/<int:cid>', methods=['PUT','DELETE'])
def client_item(cid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM clients WHERE id=?",(cid,)); conn.commit(); conn.close(); return jsonify({'ok':True})
    d = request.json
    conn.execute("UPDATE clients SET name=?,source=?,service=?,problem=?,status=?,expected_value=?,week=?,next_step=?,notes=? WHERE id=?",(d.get('name'),d.get('source'),d.get('service'),d.get('problem'),d.get('status'),d.get('expected_value',0),d.get('week'),d.get('next_step'),d.get('notes'),cid))
    conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/outreach', methods=['GET','POST'])
def outreach():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO outreach (name,platform,service,reply,sent_date,week,notes) VALUES (?,?,?,?,?,?,?)",(d.get('name',''),d.get('platform',''),d.get('service',''),d.get('reply','في الانتظار'),d.get('sent_date',''),d.get('week',1),d.get('notes','')))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    rows = conn.execute("SELECT * FROM outreach ORDER BY id DESC").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/api/outreach/<int:oid>', methods=['PUT','DELETE'])
def outreach_item(oid):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM outreach WHERE id=?",(oid,)); conn.commit(); conn.close(); return jsonify({'ok':True})
    d = request.json
    conn.execute("UPDATE outreach SET name=?,platform=?,service=?,reply=?,sent_date=?,week=?,notes=? WHERE id=?",(d.get('name'),d.get('platform'),d.get('service'),d.get('reply'),d.get('sent_date'),d.get('week'),d.get('notes'),oid))
    conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/checklists', methods=['GET','POST'])
def checklists():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO checklists (category,title,items) VALUES (?,?,?)",(d.get('category','يومي'),d.get('title',''),json.dumps(d.get('items',[]),ensure_ascii=False)))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    rows = conn.execute("SELECT * FROM checklists ORDER BY category,id").fetchall()
    conn.close()
    result = []
    for r in rows:
        row = dict(r)
        try: row['items'] = json.loads(row['items'])
        except: row['items'] = []
        result.append(row)
    return jsonify(result)

@app.route('/api/checklists/<int:cid>', methods=['DELETE'])
def checklist_item(cid):
    conn = get_db()
    conn.execute("DELETE FROM checklists WHERE id=?",(cid,))
    conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/reviews', methods=['GET','POST'])
def reviews():
    conn = get_db()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO weekly_reviews (week,videos_count,outreach_count,new_clients,best_video,what_worked,what_didnt,next_changes) VALUES (?,?,?,?,?,?,?,?)",(d.get('week',1),d.get('videos_count',0),d.get('outreach_count',0),d.get('new_clients',0),d.get('best_video',''),d.get('what_worked',''),d.get('what_didnt',''),d.get('next_changes','')))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    rows = conn.execute("SELECT * FROM weekly_reviews ORDER BY week").fetchall()
    conn.close(); return jsonify([dict(r) for r in rows])

@app.route('/login.html')
def login_page(): return send_from_directory('static', 'login.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path): return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
