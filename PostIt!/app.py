import os, json, time, threading
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

APP_SECRET = "super-secret-change-me"
DATA_FILE = "data.json"
UPLOAD_PROFILE = "uploads/profile"
UPLOAD_POSTS = "uploads/posts"

app = Flask(__name__)
app.secret_key = APP_SECRET

os.makedirs(UPLOAD_PROFILE, exist_ok=True)
os.makedirs(UPLOAD_POSTS, exist_ok=True)

data = {
    "users": {},   # username: {password_hash, profile:{desc, avatar_url}}
    "posts": []    # {id, author, text, media_url}
}

def load_data():
    global data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def autosave_loop():
    while True:
        time.sleep(30)
        save_data()

@app.route("/")
def index():
    user = None
    if "user" in session:
        user = data["users"].get(session["user"])
    return render_template("index.html", user_name=session.get("user"), user=user, posts=data["posts"])

@app.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if not username or not password:
        return "Missing fields", 400
    if username in data["users"]:
        return "User exists", 400
    data["users"][username] = {
        "password_hash": generate_password_hash(password),
        "profile": {"desc": "", "avatar_url": ""}
    }
    save_data()
    return redirect(url_for("index"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    user = data["users"].get(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return "Invalid credentials", 400
    session["user"] = username
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

@app.route("/profile/update", methods=["POST"])
def profile_update():
    if "user" not in session:
        return redirect(url_for("index"))
    username = session["user"]
    desc = request.form.get("desc", "").strip()
    avatar_url = request.form.get("avatar_url", "").strip()

    # file upload
    file = request.files.get("avatar_file")
    if file and file.filename:
        filename = secure_filename(f"{username}_{int(time.time())}_{file.filename}")
        path = os.path.join(UPLOAD_PROFILE, filename)
        file.save(path)
        avatar_url = url_for("uploaded_file", folder="profile", filename=filename)

    data["users"][username]["profile"]["desc"] = desc
    data["users"][username]["profile"]["avatar_url"] = avatar_url
    save_data()
    return redirect(url_for("index"))

@app.route("/post/create", methods=["POST"])
def post_create():
    if "user" not in session:
        return redirect(url_for("index"))
    username = session["user"]
    text = request.form.get("text", "").strip()
    media_url = request.form.get("media_url", "").strip()

    file = request.files.get("media_file")
    if file and file.filename:
        filename = secure_filename(f"{username}_{int(time.time())}_{file.filename}")
        path = os.path.join(UPLOAD_POSTS, filename)
        file.save(path)
        media_url = url_for("uploaded_file", folder="posts", filename=filename)

    if not text and not media_url:
        return redirect(url_for("index"))

    post = {
        "id": int(time.time()*1000),
        "author": username,
        "text": text,
        "media_url": media_url
    }
    data["posts"].append(post)
    save_data()
    return redirect(url_for("index"))

@app.route("/uploads/<folder>/<path:filename>")
def uploaded_file(folder, filename):
    if folder == "profile":
        return send_from_directory(UPLOAD_PROFILE, filename)
    if folder == "posts":
        return send_from_directory(UPLOAD_POSTS, filename)
    return "Not found", 404

if __name__ == "__main__":
    load_data()
    t = threading.Thread(target=autosave_loop, daemon=True)
    t.start()
    app.run(debug=True)
