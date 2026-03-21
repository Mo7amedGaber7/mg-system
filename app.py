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
    
    c.execute('''CREATE TABLE IF NOT EXISTS weekly_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week INTEGER,
        videos_count INTEGER DEFAULT 0,
        outreach_count INTEGER DEFAULT 0,
        new_clients INTEGER DEFAULT 0,
        best_video TEXT,
        what_worked TEXT,
        what_didnt TEXT,
        next_changes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS checklists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        title TEXT,
        items TEXT,
        week INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Seed sample data if empty
    c.execute("SELECT COUNT(*) FROM videos")
    if c.fetchone()[0] == 0:
        sample_videos = [
            ("دفعت فلوس على موقع ومحدش دخله غيرك", "وجع + تعليم", "الـ٣ منصات", "دفعت فلوس على موقع... ومحدش دخله غيرك", "كوّمنت 'موقع'", "منشور ✅", 1),
            ("٣ أسئلة قبل ما تعمل أي موقع", "وجع + تعليم", "الـ٣ منصات", "قبل ما تدفع — اسأل ٣ أسئلة دول", "كوّمنت 'أسئلة'", "منشور ✅", 1),
            ("لو بتعمل الرواتب على Excel", "وجع + تعليم", "الـ٣ منصات", "ليه لسه شغال على Excel؟", "كوّمنت 'رواتب'", "متصور 🎬", 1),
            ("الفرق بين موقع وفانل", "تعليم", "TikTok", "", "كوّمنت 'فانل'", "جاهز 📋", 1),
            ("٣ أخطاء بتخلي الزائر يمشي", "وجع + تعليم", "الـ٣ منصات", "موقعك بيخسر عملاء في ٥ ثواني", "كوّمنت 'أخطاء'", "متصور 🎬", 2),
        ]
        for v in sample_videos:
            c.execute("INSERT INTO videos (title,type,platform,hook,cta,status,week) VALUES (?,?,?,?,?,?,?)", v)

    c.execute("SELECT COUNT(*) FROM clients")
    if c.fetchone()[0] == 0:
        sample_clients = [
            ("د. أحمد — عيادة أسنان", "Facebook Groups", "ويب سايت + فانل", "مفيش حجز أونلاين", "مهتم 🔥", 8000, 1, "بعت عرض — ينتظر"),
            ("شركة النيل للتوزيع", "Outreach مباشر", "سيستم HR", "الرواتب على Excel — ٢٠ موظف", "بيتكلم 💬", 15000, 1, "موعد الخميس"),
            ("مركز اللغات الحديثة", "محيط دافئ", "ويب سايت", "موقع قديم مش responsive", "جديد 🆕", 5000, 2, "بعت رسالة"),
        ]
        for cl in sample_clients:
            c.execute("INSERT INTO clients (name,source,service,problem,status,expected_value,week,next_step) VALUES (?,?,?,?,?,?,?,?)", cl)

    c.execute("SELECT COUNT(*) FROM outreach")
    if c.fetchone()[0] == 0:
        sample_or = [
            ("د. محمد — عيادة الدقي", "Facebook", "ويب سايت", "رد إيجابي ✅", "2026-03-21", 1, "مهتم — بعتله عرض"),
            ("شركة الشروق للمقاولات", "LinkedIn", "سيستم", "في الانتظار ⏳", "2026-03-21", 1, ""),
            ("أ. سارة — مركز تدريب", "Facebook", "ويب سايت", "ما ردتش ❌", "2026-03-20", 1, "هبعتلها follow up"),
        ]
        for o in sample_or:
            c.execute("INSERT INTO outreach (name,platform,service,reply,sent_date,week,notes) VALUES (?,?,?,?,?,?,?)", o)

    # Default checklists
    c.execute("SELECT COUNT(*) FROM checklists")
    if c.fetchone()[0] == 0:
        checklists = [
            ("يومي", "روتين الصبح — ٣٠ دقيقة", '["رد على كومنتات الفيديوهات","تفاعل في ٣ Groups","تعليق استراتيجي على ٣ بوستات","بص على أداء الفيديوهات امبارح"]', 1),
            ("يومي", "روتين الضهر — ٦٠ دقيقة", '["تصوير فيديوين","مونتاج سريع","نشر على المنصات الـ٣","رد على الرسايل الجديدة"]', 1),
            ("يومي", "روتين الليل — ٤٥ دقيقة", '["بعت ٤-٥ رسايل Outreach","سجل المحادثات الجديدة في الشيت","اكتب سكريبتات بكره","مراجعة أداء اليوم"]', 1),
            ("أسبوعي", "تشيكليست أسبوع ١ — التأسيس", '["إنشاء البروفايلات على الـ٣ منصات","تحويل الأعمال السابقة لـ٣ Case Studies","تصوير ١٠ فيديوهات batch","كتابة السكريبتات الـ١٠","الانضمام لـ٥ Facebook Groups","كل فرد في التيم يكلم ١٠ من محيطه","إنشاء ليستة ٢٠ شخص للـ Outreach"]', 1),
            ("أسبوعي", "تشيكليست أسبوع ٢ — التفعيل", '["نشر فيديوين يومياً","رد على كل كومنت في أول ساعة","بعت ٢٠ رسالة Outreach جديدة","تفاعل يومي في الـ Groups","تقديم ٣ تقييمات مجانية","تحليل أفضل فيديو اشتغل","متابعة المحيط الدافئ اللي ما ردش"]', 2),
            ("أسبوعي", "تشيكليست أسبوع ٣ — التحويل", '["Follow up على كل المحادثات المفتوحة","٢٠ رسالة Outreach جديدة","إغلاق أول صفقة","اعمل فيديو Case Study حقيقية","طلب Referral من المحيط الدافئ","توثيق أول Case Study","بناء Template للـ Outreach"]', 3),
            ("أسبوعي", "تشيكليست أسبوع ٤ — الثبات", '["تحليل الشهر كامل","تحديد أفضل ٣ أنواع محتوى","إغلاق صفقة تانية","طلب شهادات العملاء","عمل تقرير الشهر الأول","بناء خطة الشهر التاني","مراجعة الأدوار في التيم"]', 4),
            ("محتوى", "قائمة أفكار الفيديوهات", '["دفعت فلوس على موقع ومحدش دخله غيرك","٣ أسئلة قبل ما تعمل أي موقع","لو بتعمل الرواتب على Excel","الفرق بين موقع وفانل","٣ أخطاء بتخلي الزائر يمشي من موقعك","ليه موقعك بيجيب زيارات ومفيش حد بيتواصل","الفرق بين شركة بسيستم وشركة من غير سيستم","٣ علامات إن شركتك محتاجة سيستم دلوقتي","عميل كان بيخسر ٣ ساعات يومياً — عملنا له كده","سيستم الكاشير ده هيوفرلك كام في السنة"]', 1),
        ]
        for ch in checklists:
            c.execute("INSERT INTO checklists (category,title,items,week) VALUES (?,?,?,?)", ch)

    conn.commit()
    conn.close()

# ── STATS ──
@app.route('/api/stats')
def stats():
    conn = get_db()
    c = conn.cursor()
    
    total_videos = c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    published = c.execute("SELECT COUNT(*) FROM videos WHERE status='منشور ✅'").fetchone()[0]
    total_clients = c.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    hot_clients = c.execute("SELECT COUNT(*) FROM clients WHERE status='مهتم 🔥'").fetchone()[0]
    closed = c.execute("SELECT COUNT(*) FROM clients WHERE status='اتغلق ✅'").fetchone()[0]
    revenue = c.execute("SELECT COALESCE(SUM(expected_value),0) FROM clients WHERE status='اتغلق ✅'").fetchone()[0]
    total_or = c.execute("SELECT COUNT(*) FROM outreach").fetchone()[0]
    positive_or = c.execute("SELECT COUNT(*) FROM outreach WHERE reply='رد إيجابي ✅'").fetchone()[0]
    pending_or = c.execute("SELECT COUNT(*) FROM outreach WHERE reply='في الانتظار ⏳'").fetchone()[0]
    pipeline = c.execute("SELECT COALESCE(SUM(expected_value),0) FROM clients WHERE status != 'اتغلق ✅' AND status != 'رفض 🚫'").fetchone()[0]
    
    conn.close()
    return jsonify({
        'videos': {'total': total_videos, 'published': published, 'target': 40, 'pct': round((published/40)*100) if published else 0},
        'clients': {'total': total_clients, 'hot': hot_clients, 'closed': closed, 'pipeline': pipeline},
        'revenue': revenue,
        'outreach': {'total': total_or, 'positive': positive_or, 'pending': pending_or, 'rate': round((positive_or/total_or)*100) if total_or else 0}
    })

# ── VIDEOS ──
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
            (d.get('name',''), d.get('source',''), d.get('service',''), d.get('problem',''), d.get('status','جديد 🆕'), d.get('expected_value',0), d.get('week',1), d.get('next_step',''), d.get('notes','')))
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
            (d.get('name',''), d.get('platform',''), d.get('service',''), d.get('reply','في الانتظار ⏳'), d.get('sent_date',''), d.get('week',1), d.get('notes','')))
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

# ── CHECKLISTS ──
@app.route('/api/checklists', methods=['GET'])
def checklists():
    conn = get_db()
    rows = conn.execute("SELECT * FROM checklists ORDER BY category, week").fetchall()
    conn.close()
    import json
    result = []
    for r in rows:
        row = dict(r)
        try: row['items'] = json.loads(row['items'])
        except: row['items'] = []
        result.append(row)
    return jsonify(result)

# ── WEEKLY REVIEWS ──
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

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)

@app.route('/login.html')
def login_page():
    return send_from_directory('static', 'login.html')
