import os
import json
import time
import threading
from flask import (
    Flask, request, redirect, url_for, render_template,
    session, jsonify, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# -----------------------------
# CONFIG
# -----------------------------
APP_SECRET = "CHANGE_ME_SECRET"
DATA_FILE = "data.json"

UPLOAD_PROFILE = "uploads/profile"
UPLOAD_BANNER = "uploads/banner"
UPLOAD_POSTS = "uploads/posts"

os.makedirs(UPLOAD_PROFILE, exist_ok=True)
os.makedirs(UPLOAD_BANNER, exist_ok=True)
os.makedirs(UPLOAD_POSTS, exist_ok=True)

app = Flask(__name__)
app.secret_key = APP_SECRET

# -----------------------------
# DATA MODEL
# -----------------------------
data = {
    "users": {
        # "username": {
        #   "password_hash": "...",
        #   "role": "user" | "guest",
        #   "profile": {
        #       "desc": "",
        #       "avatar_url": "",
        #       "banner_url": ""
        #   }
        # }
    },
    "posts": [
        # {
        #   "id": 123,
        #   "author": "username",
        #   "text": "content",
        #   "media_url": "",
        #   "likes": ["user1", "user2"],
        #   "comments": [
        #       {
        #         "id": 1,
        #         "author": "username",
        #         "text": "comment text",
        #         "likes": ["userX"],
        #         "is_pre": False,
        #         "is_viral": False
        #       }
        #   ]
        # }
    ],
    "pre_comments": [
        "🔥 Fire!",
        "💡 Interesting point",
        "👏 Well said",
        "😂 This made my day",
        "❤️ Love this"
    ]
}

# -----------------------------
# PERSISTENZA
# -----------------------------
def load_data():
    global data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                pass

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def autosave_loop():
    while True:
        time.sleep(30)
        save_data()

# -----------------------------
# UTILS
# -----------------------------
def current_username():
    return session.get("user")

def current_user():
    u = current_username()
    if not u:
        return None
    return data["users"].get(u)

def is_guest():
    u = current_user()
    if not u:
        return False
    return u.get("role") == "guest"

def get_post(post_id):
    for p in data["posts"]:
        if p["id"] == post_id:
            return p
    return None

def get_comment(post, comment_id):
    for c in post["comments"]:
        if c["id"] == comment_id:
            return c
    return None

def next_comment_id():
    max_id = 0
    for p in data["posts"]:
        for c in p["comments"]:
            if c["id"] > max_id:
                max_id = c["id"]
    return max_id + 1

# -----------------------------
# ROUTES BASE
# -----------------------------
@app.route("/")
def index():
    user = current_user()
    return render_template(
        "index.html",
        user_name=current_username(),
        user=user,
        posts=data["posts"],
        pre_comments=data["pre_comments"]
    )

@app.route("/post/<int:post_id>")
def view_post(post_id):
    user = current_user()
    post = get_post(post_id)
    if not post:
        return "Post not found", 404
    return render_template(
        "post.html",
        user_name=current_username(),
        user=user,
        post=post,
        pre_comments=data["pre_comments"]
    )

# -----------------------------
# AUTH
# -----------------------------
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
        "role": "user",
        "profile": {
            "desc": "",
            "avatar_url": "",
            "banner_url": ""
        }
    }
    save_data()
    session["user"] = username
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

@app.route("/guest")
def guest_login():
    # guest "utente" senza password, ma limitato
    guest_name = f"guest_{int(time.time())}"
    data["users"][guest_name] = {
        "password_hash": "",
        "role": "guest",
        "profile": {
            "desc": "",
            "avatar_url": "",
            "banner_url": ""
        }
    }
    save_data()
    session["user"] = guest_name
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

# -----------------------------
# PROFILO (avatar, banner, desc)
# -----------------------------
@app.route("/profile/update", methods=["POST"])
def profile_update():
    if not current_username():
        return redirect(url_for("index"))
    if is_guest():
        return "Guests cannot edit profile", 403

    username = current_username()
    desc = request.form.get("desc", "").strip()
    avatar_url = request.form.get("avatar_url", "").strip()
    banner_url = request.form.get("banner_url", "").strip()

    # avatar file
    avatar_file = request.files.get("avatar_file")
    if avatar_file and avatar_file.filename:
        filename = secure_filename(f"{username}_avatar_{int(time.time())}_{avatar_file.filename}")
        path = os.path.join(UPLOAD_PROFILE, filename)
        avatar_file.save(path)
        avatar_url = url_for("uploaded_file", folder="profile", filename=filename)

    # banner file
    banner_file = request.files.get("banner_file")
    if banner_file and banner_file.filename:
        filename = secure_filename(f"{username}_banner_{int(time.time())}_{banner_file.filename}")
        path = os.path.join(UPLOAD_BANNER, filename)
        banner_file.save(path)
        banner_url = url_for("uploaded_file", folder="banner", filename=filename)

    user = data["users"][username]
    user["profile"]["desc"] = desc
    user["profile"]["avatar_url"] = avatar_url
    user["profile"]["banner_url"] = banner_url
    save_data()
    return redirect(url_for("index"))

# -----------------------------
# POST (creazione, like, share)
# -----------------------------
@app.route("/post/create", methods=["POST"])
def post_create():
    if not current_username():
        return redirect(url_for("index"))
    if is_guest():
        return "Guests cannot create posts", 403

    username = current_username()
    text = request.form.get("text", "").strip()
    media_url = request.form.get("media_url", "").strip()

    media_file = request.files.get("media_file")
    if media_file and media_file.filename:
        filename = secure_filename(f"{username}_post_{int(time.time())}_{media_file.filename}")
        path = os.path.join(UPLOAD_POSTS, filename)
        media_file.save(path)
        media_url = url_for("uploaded_file", folder="posts", filename=filename)

    if not text and not media_url:
        return redirect(url_for("index"))

    post = {
        "id": int(time.time() * 1000),
        "author": username,
        "text": text,
        "media_url": media_url,
        "likes": [],
        "comments": []
    }
    data["posts"].append(post)
    save_data()
    return redirect(url_for("index"))

@app.route("/post/<int:post_id>/like", methods=["POST"])
def post_like(post_id):
    if not current_username():
        return "Unauthorized", 401
    if is_guest():
        return "Guests cannot like posts", 403

    username = current_username()
    post = get_post(post_id)
    if not post:
        return "Post not found", 404

    if username in post["likes"]:
        post["likes"].remove(username)
    else:
        post["likes"].append(username)

    save_data()
    return jsonify({"likes": len(post["likes"])})

@app.route("/post/<int:post_id>/share", methods=["GET"])
def post_share(post_id):
    post = get_post(post_id)
    if not post:
        return "Post not found", 404
    link = url_for("view_post", post_id=post_id, _external=True)
    return jsonify({"share_link": link})

# -----------------------------
# COMMENTI (normali, pre, virali)
# -----------------------------
@app.route("/post/<int:post_id>/comment", methods=["POST"])
def post_comment(post_id):
    if not current_username():
        return "Unauthorized", 401

    username = current_username()
    post = get_post(post_id)
    if not post:
        return "Post not found", 404

    text = request.form.get("text", "").strip()
    pre_id = request.form.get("pre_id", "").strip()

    is_pre = False
    if not text and pre_id:
        try:
            idx = int(pre_id)
            if 0 <= idx < len(data["pre_comments"]):
                text = data["pre_comments"][idx]
                is_pre = True
        except ValueError:
            pass

    if not text:
        return "Empty comment", 400

    comment = {
        "id": next_comment_id(),
        "author": username,
        "text": text,
        "likes": [],
        "is_pre": is_pre,
        "is_viral": False
    }
    post["comments"].append(comment)
    save_data()
    return redirect(url_for("view_post", post_id=post_id))

@app.route("/comment/<int:comment_id>/like", methods=["POST"])
def comment_like(comment_id):
    if not current_username():
        return "Unauthorized", 401
    if is_guest():
        return "Guests cannot like comments", 403

    username = current_username()
    # trova commento
    target_comment = None
    target_post = None
    for p in data["posts"]:
        for c in p["comments"]:
            if c["id"] == comment_id:
                target_comment = c
                target_post = p
                break
        if target_comment:
            break

    if not target_comment:
        return "Comment not found", 404

    if username in target_comment["likes"]:
        target_comment["likes"].remove(username)
    else:
        target_comment["likes"].append(username)

    # logica "virale": se supera una soglia di like
    if len(target_comment["likes"]) >= 5:
        target_comment["is_viral"] = True

    save_data()
    return jsonify({
        "likes": len(target_comment["likes"]),
        "is_viral": target_comment["is_viral"]
    })

# -----------------------------
# FILE STATICI UPLOAD
# -----------------------------
@app.route("/uploads/<folder>/<path:filename>")
def uploaded_file(folder, filename):
    if folder == "profile":
        return send_from_directory(UPLOAD_PROFILE, filename)
    if folder == "banner":
        return send_from_directory(UPLOAD_BANNER, filename)
    if folder == "posts":
        return send_from_directory(UPLOAD_POSTS, filename)
    return "Not found", 404

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    load_data()
    t = threading.Thread(target=autosave_loop, daemon=True)
    t.start()
    app.run(debug=True)
