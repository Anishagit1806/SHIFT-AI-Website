import os, sqlite3, json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "shift_ai.db")
UPLOAD_DIR = os.path.join(APP_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SHIFT_AI_SECRET", "change-this-secret-before-public-hosting")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB total request limit
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR

CHALLENGES = [
    {"id":1,"category":"Event Management","title":"Technical Symposium","scenario":"Organize a one-day technical symposium for 500 students. Your total budget is ₹50,000 and you have two weeks to prepare. Plan the venue, registration, sessions, volunteers, food, equipment, and participant communication.","crisis":"The main auditorium becomes unavailable three days before the symposium. Adapt your agent's decisions and create a revised plan."},
    {"id":2,"category":"Event Management","title":"College Cultural Fest","scenario":"Plan a cultural fest for 800 students with a budget of ₹75,000 and 10 days for preparation. Coordinate performances, stage, sound, security, food, volunteers, and the event schedule.","crisis":"The main performer cancels at the last minute. Adapt your agent's decisions and create a revised event plan."},
    {"id":3,"category":"Event Management","title":"24-Hour Hackathon","scenario":"Organize a 24-hour hackathon for 100 participants with a budget of ₹40,000. Plan registration, teams, mentors, internet, power, food, workspace, and emergency support.","crisis":"The internet connection fails during the hackathon. Adapt your agent's decisions and propose a workable continuity plan."},
    {"id":4,"category":"Event Management","title":"Career Fair","scenario":"Organize a career fair for 1,000 students and 15 companies with a budget of ₹60,000. Coordinate company booths, interview spaces, student flow, power, signage, and volunteers.","crisis":"The main exhibition hall becomes unavailable two days before the fair. Adapt your agent's decisions and create a revised layout and schedule."},
    {"id":5,"category":"Event Management","title":"AI Workshop","scenario":"Organize a one-day AI workshop for 300 students with a budget of ₹30,000. Plan the trainer, venue, systems, internet, registration, learning materials, and participant support.","crisis":"The invited AI trainer cancels one day before the workshop. Adapt your agent's decisions and propose a replacement plan."},
    {"id":6,"category":"Real-World Decision Arena","title":"Flood Response – Emergency Resource Manager","scenario":"Coordinate an initial flood response across three affected areas with 20 volunteers, 3 rescue vehicles, and an emergency budget of ₹1,00,000. Prioritize life safety, information verification, evacuation coordination, and communication with authorized emergency services.","crisis":"Water levels rise quickly in the highest-risk area, and more residents may need evacuation. Reprioritize volunteers and vehicles, explain your decisions, and coordinate with authorized emergency services."},
    {"id":7,"category":"Real-World Decision Arena","title":"Hospital Resource Manager","scenario":"Design a hospital operations support agent to coordinate 30 beds, 10 doctors, and limited supplies during a busy period. Focus on patient flow, staff availability, bed status, and escalation to qualified medical professionals. Do not make diagnosis or treatment decisions.","crisis":"Patient arrivals increase by 50%. Revise patient-flow coordination, bed visibility, staffing support, and escalation procedures with medical professionals."},
    {"id":8,"category":"Real-World Decision Arena","title":"Smart Traffic Decision Manager","scenario":"Coordinate traffic management across four congested junctions using 10 traffic officers and a limited budget. Your agent should support monitoring, prioritization, communication, and safe traffic-flow decisions.","crisis":"An ambulance needs a clear route through a congested junction. Explain how your agent would coordinate a safe route and traffic officers while following authorized traffic control."},
    {"id":9,"category":"Real-World Decision Arena","title":"Supply Chain Decision Manager","scenario":"Plan delivery of 500 packages to five locations within 24 hours using 10 vehicles and a fixed fuel budget. Consider delivery priority, route planning, vehicle capacity, time, and fuel usage.","crisis":"A major route closes unexpectedly. Reroute vehicles, reprioritize deliveries, and explain how your agent would manage time and fuel."},
    {"id":10,"category":"Real-World Decision Arena","title":"Smart Agriculture Decision Manager","scenario":"Manage irrigation planning across 100 acres with limited water and an operating budget of ₹2,00,000. Consider crop priority, soil and weather information, water availability, and fair resource allocation.","crisis":"Available irrigation water decreases by 40%. Revise water allocation and explain how your agent would protect vulnerable crops."}
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, team_name TEXT UNIQUE NOT NULL,
            members TEXT NOT NULL, department TEXT, year TEXT,
            username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'team', created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE NOT NULL,
            challenge_id INTEGER NOT NULL, mode TEXT NOT NULL, selected_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id))""")
        con.execute("""CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            stage TEXT NOT NULL, answers TEXT NOT NULL, ai_tool TEXT, ai_prompt TEXT,
            ai_output TEXT, team_changes TEXT, files TEXT, submitted_at TEXT NOT NULL,
            UNIQUE(user_id, stage), FOREIGN KEY(user_id) REFERENCES users(id))""")
        con.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('crisis_released','0')")
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('initial_open','1')")
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('crisis_open','0')")
        admin = con.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        if not admin:
            con.execute("""INSERT INTO users(team_name,members,department,year,username,password_hash,role,created_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                ("SHIFT AI Organizers","Organizer","Nexora","—","admin",
                 generate_password_hash(os.environ.get("SHIFT_AI_ADMIN_PASSWORD","shiftai2026")),"admin",datetime.now().isoformat(timespec="seconds")))

def setting(key):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else "0"

def set_setting(key, value):
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def get_challenge(cid):
    return next((c for c in CHALLENGES if c["id"] == cid), None)

def get_selection(user_id):
    with db() as con:
        return con.execute("SELECT * FROM selections WHERE user_id=?", (user_id,)).fetchone()

def get_submission(user_id, stage):
    with db() as con:
        return con.execute("SELECT * FROM submissions WHERE user_id=? AND stage=?", (user_id,stage)).fetchone()

def save_uploads(files):
    saved=[]
    allowed={"png","jpg","jpeg","webp","pdf","mp4","mov","webm"}
    for f in files:
        if not f or not f.filename: continue
        ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
        if ext not in allowed:
            raise ValueError("Allowed uploads: PNG, JPG, WEBP, PDF, MP4, MOV, WEBM.")
        name=f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{secure_filename(f.filename)}"
        f.save(os.path.join(UPLOAD_DIR,name))
        saved.append(name)
    return saved

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("home.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        team=request.form.get("team_name","").strip()
        members=request.form.get("members","").strip()
        username=request.form.get("username","").strip().lower()
        password=request.form.get("password","")
        department=request.form.get("department","").strip()
        year=request.form.get("year","").strip()
        if not all([team,members,username,password]):
            flash("Please complete all required fields.","error")
        elif len(password)<6:
            flash("Password must contain at least 6 characters.","error")
        else:
            try:
                with db() as con:
                    con.execute("""INSERT INTO users(team_name,members,department,year,username,password_hash,role,created_at)
                    VALUES(?,?,?,?,?,?,?,?)""",(team,members,department,year,username,generate_password_hash(password),"team",datetime.now().isoformat(timespec="seconds")))
                flash("Team registered. Please log in.","success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That team name or login ID is already registered. Use a different one.","error")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form.get("username","").strip().lower()
        password=request.form.get("password","")
        with db() as con:
            user=con.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
        if user and check_password_hash(user["password_hash"],password):
            session.clear()
            session.update(user_id=user["id"],team_name=user["team_name"],username=user["username"],role=user["role"])
            return redirect(url_for("admin_dashboard" if user["role"]=="admin" else "dashboard"))
        flash("Invalid login ID or password.","error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role")=="admin": return redirect(url_for("admin_dashboard"))
    selection=get_selection(session["user_id"])
    challenge=get_challenge(selection["challenge_id"]) if selection else None
    return render_template("dashboard.html",selection=selection,challenge=challenge,
        initial=get_submission(session["user_id"],"initial"),
        crisis=get_submission(session["user_id"],"crisis"),
        initial_open=setting("initial_open")=="1",
        crisis_released=setting("crisis_released")=="1",
        crisis_open=setting("crisis_open")=="1")

@app.route("/challenges")
@login_required
def challenges():
    if session.get("role")=="admin": return redirect(url_for("admin_dashboard"))
    selection=get_selection(session["user_id"])
    return render_template("challenges.html",challenges=CHALLENGES,selection=selection)

@app.route("/select-challenge/<int:cid>", methods=["POST"])
@login_required
def select_challenge(cid):
    if session.get("role")=="admin": abort(403)
    if get_selection(session["user_id"]):
        flash("Your team has already selected a challenge. Contact the organizer if a correction is needed.","error")
        return redirect(url_for("dashboard"))
    if setting("initial_open")!="1":
        flash("Challenge selection is currently closed.","error")
        return redirect(url_for("challenges"))
    if not get_challenge(cid): abort(404)
    mode=request.form.get("mode")
    if mode not in ("AI","Human"):
        flash("Choose AI Mode or Human Mode.","error")
        return redirect(url_for("challenges"))
    with db() as con:
        con.execute("INSERT INTO selections(user_id,challenge_id,mode,selected_at) VALUES(?,?,?,?)",
                    (session["user_id"],cid,mode,datetime.now().isoformat(timespec="seconds")))
    flash("Challenge selected successfully. Other teams may select the same challenge.","success")
    return redirect(url_for("dashboard"))

@app.route("/submit/<stage>", methods=["GET","POST"])
@login_required
def submit(stage):
    if stage not in ("initial","crisis") or session.get("role")=="admin": abort(404)
    selection=get_selection(session["user_id"])
    if not selection:
        flash("Select a problem statement first.","error")
        return redirect(url_for("challenges"))
    if get_submission(session["user_id"],stage):
        flash("This submission has already been received and is locked.","error")
        return redirect(url_for("dashboard"))
    if stage=="initial" and setting("initial_open")!="1":
        flash("Initial submissions are closed.","error"); return redirect(url_for("dashboard"))
    if stage=="crisis" and not (setting("crisis_released")=="1" and setting("crisis_open")=="1"):
        flash("The crisis response submission is not open yet.","error"); return redirect(url_for("dashboard"))
    challenge=get_challenge(selection["challenge_id"])
    if request.method=="POST":
        fields=["agent_name","agent_goal","input_data","analysis_process","decision_process","tools_actions","expected_output","justification"]
        answers={f:request.form.get(f,"").strip() for f in fields}
        if stage=="crisis":
            fields2=["original_changes","revised_decisions","resource_reallocation","revised_workflow","fallback_plan"]
            answers.update({f:request.form.get(f,"").strip() for f in fields2})
        if any(not answers.get(f) for f in fields):
            flash("Please complete all required agent-design sections.","error")
            return render_template("submit.html",stage=stage,challenge=challenge,mode=selection["mode"])
        if stage=="crisis" and any(not answers.get(f) for f in fields2):
            flash("Please complete all required crisis-response sections.","error")
            return render_template("submit.html",stage=stage,challenge=challenge,mode=selection["mode"])
        try:
            uploaded=save_uploads(request.files.getlist("attachments"))
        except ValueError as e:
            flash(str(e),"error")
            return render_template("submit.html",stage=stage,challenge=challenge,mode=selection["mode"])
        ai_tool=request.form.get("ai_tool","").strip() if selection["mode"]=="AI" else None
        ai_prompt=request.form.get("ai_prompt","").strip() if selection["mode"]=="AI" else None
        ai_output=request.form.get("ai_output","").strip() if selection["mode"]=="AI" else None
        team_changes=request.form.get("team_changes","").strip() if selection["mode"]=="AI" else None
        with db() as con:
            con.execute("""INSERT INTO submissions(user_id,stage,answers,ai_tool,ai_prompt,ai_output,team_changes,files,submitted_at)
            VALUES(?,?,?,?,?,?,?,?,?)""",(session["user_id"],stage,json.dumps(answers),ai_tool,ai_prompt,ai_output,team_changes,json.dumps(uploaded),datetime.now().isoformat(timespec="seconds")))
        flash("Your submission has been saved and locked. You can view its status on your dashboard.","success")
        return redirect(url_for("dashboard"))
    return render_template("submit.html",stage=stage,challenge=challenge,mode=selection["mode"])

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    with db() as con:
        teams=con.execute("""SELECT u.id,u.team_name,u.members,u.department,u.year,u.username,s.challenge_id,s.mode,s.selected_at
            FROM users u LEFT JOIN selections s ON s.user_id=u.id WHERE u.role='team' ORDER BY u.team_name""").fetchall()
        subs=con.execute("""SELECT s.*,u.team_name FROM submissions s JOIN users u ON u.id=s.user_id ORDER BY s.submitted_at DESC""").fetchall()
    return render_template("admin.html",teams=teams,submissions=subs,challenges=CHALLENGES,
        initial_open=setting("initial_open")=="1",crisis_released=setting("crisis_released")=="1",
        crisis_open=setting("crisis_open")=="1")

@app.route("/admin/settings", methods=["POST"])
@login_required
@admin_required
def admin_settings():
    action=request.form.get("action")
    if action=="initial_open": set_setting("initial_open",request.form.get("value","0"))
    elif action=="release_crisis":
        set_setting("crisis_released","1")
        set_setting("crisis_open","1")
    elif action=="close_crisis": set_setting("crisis_open","0")
    elif action=="open_crisis": 
        if setting("crisis_released")=="1": set_setting("crisis_open","1")
    flash("Organizer settings updated.","success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/submission/<int:sid>")
@login_required
@admin_required
def view_submission(sid):
    with db() as con:
        sub=con.execute("""SELECT s.*,u.team_name,u.members,u.department,u.year,u.username
            FROM submissions s JOIN users u ON u.id=s.user_id WHERE s.id=?""",(sid,)).fetchone()
    if not sub: abort(404)
    selection=get_selection(sub["user_id"])
    challenge=get_challenge(selection["challenge_id"])
    return render_template("view_submission.html",sub=sub,answers=json.loads(sub["answers"]),
        files=json.loads(sub["files"] or "[]"),challenge=challenge,mode=selection["mode"])

@app.route("/admin/export")
@login_required
@admin_required
def export():
    import csv, io
    from flask import make_response
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["Team","Login ID","Challenge","Mode","Stage","Submitted At","Answers JSON","AI Tool","AI Prompt","AI Output","Team Changes","Files"])
    with db() as con:
        rows=con.execute("""SELECT u.team_name,u.username,se.challenge_id,se.mode,s.stage,s.submitted_at,s.answers,s.ai_tool,s.ai_prompt,s.ai_output,s.team_changes,s.files
            FROM submissions s JOIN users u ON u.id=s.user_id JOIN selections se ON se.user_id=u.id ORDER BY u.team_name,s.stage""").fetchall()
    for r in rows:
        c=get_challenge(r["challenge_id"])
        writer.writerow([r["team_name"],r["username"],c["title"] if c else "",r["mode"],r["stage"],r["submitted_at"],r["answers"],r["ai_tool"],r["ai_prompt"],r["ai_output"],r["team_changes"],r["files"]])
    response=make_response(output.getvalue())
    response.headers["Content-Disposition"]="attachment; filename=shift_ai_submissions.csv"
    response.headers["Content-Type"]="text/csv; charset=utf-8"
    return response

@app.errorhandler(403)
def forbidden(e): return render_template("message.html",title="Access denied",message="You do not have permission to view this page."),403
@app.errorhandler(404)
def not_found(e): return render_template("message.html",title="Page not found",message="The requested page does not exist."),404

init_db()
if __name__=="__main__":
    # 0.0.0.0 allows phones on the same Wi-Fi/LAN to access the site.
    app.run(host="0.0.0.0",port=5000,debug=True)
