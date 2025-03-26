import os
import torch
from PIL import Image
import torchvision.transforms as transforms
import matplotlib.font_manager as fm
import sys
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, session, jsonify
from datetime import datetime
import matplotlib.pyplot as plt

# UTF-8 인코딩 강제 설정
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
USER_DB = "users.txt"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 채팅 메시지 저장
chat_messages = []

def set_korean_font():
    font_candidates = ["NanumGothic", "Malgun Gothic", "AppleGothic"]
    font_found = False
    for font in fm.findSystemFonts():
        font_name = fm.FontProperties(fname=font).get_name()
        if font_name in font_candidates:
            plt.rc("font", family=font_name)
            font_found = True
            print(f"✅ 한글 폰트 적용: {font_name}")
            break
    if not font_found:
        print("[경고] 한글 폰트를 찾을 수 없습니다. 기본 폰트 사용.")

set_korean_font()

def generate_sgn_noise(image_tensor, strength=0.03):
    noise_layers = []
    for scale in [4, 8, 16, 32, 64]:
        if scale <= image_tensor.shape[2] and scale <= image_tensor.shape[3]:
            noise = torch.randn(1, 1, scale, scale, device=image_tensor.device)
            upsampled = torch.nn.functional.interpolate(
                noise, size=(image_tensor.shape[2], image_tensor.shape[3]), mode='bilinear', align_corners=False
            )
            noise_layers.append(upsampled)
    combined_noise = sum(noise_layers) / len(noise_layers)
    noisy_image = image_tensor + combined_noise.expand_as(image_tensor) * strength
    return torch.clamp(noisy_image, 0, 1)

def protect_image(image_path, noise_level=0.03):
    img = Image.open(image_path).convert("RGB")
    img_tensor = transforms.ToTensor()(img).unsqueeze(0).to("cuda" if torch.cuda.is_available() else "cpu")
    noisy_img_tensor = generate_sgn_noise(img_tensor, noise_level)
    noisy_pil = transforms.ToPILImage()(noisy_img_tensor.squeeze(0).cpu())
    output_path = os.path.join(OUTPUT_FOLDER, os.path.basename(image_path))
    noisy_pil.save(output_path)
    return output_path

def load_users():
    if not os.path.exists(USER_DB):
        return {}
    with open(USER_DB, "r", encoding="utf-8") as f:
        return dict(line.strip().split(":") for line in f if line.strip())

def save_user(username, password):
    users = load_users()
    users[username] = password
    with open(USER_DB, "w", encoding="utf-8") as f:
        for u, p in users.items():
            f.write(f"{u}:{p}\n")

def current_time():
    now = datetime.now()
    hh = now.hour
    mm = now.minute
    apm = "오후" if hh >= 12 else "오전"
    hh = hh % 12 or 12
    return f"{apm} {hh}:{mm:02d}"

@app.route("/")
def home():
    return redirect(url_for("login"))  # 항상 로그인 페이지로 리다이렉트

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        if username in users and users[username] == password:
            session["username"] = username
            return redirect(url_for("chat"))
        return render_template("login.html", error="잘못된 ID 또는 비밀번호입니다.")
    return render_template("login.html", error=None)

@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        if username in users:
            return render_template("join.html", error="이미 존재하는 ID입니다.")
        save_user(username, password)
        return redirect(url_for("login"))
    return render_template("join.html", error=None)

@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("kakao.html", messages=chat_messages, username=session["username"])

@app.route("/send_message", methods=["POST"])
def send_message():
    if "username" not in session:
        return "로그인이 필요합니다.", 401
    message = request.form["message"]
    sender_class = request.form["sender_class"]
    chat_messages.append({
        "username": session["username"],
        "content": message,
        "type": "text",
        "sender_class": sender_class,
        "time": current_time()
    })
    return jsonify({"status": "success"}), 200

@app.route("/apply_filter", methods=["POST"])
def apply_filter():
    if "username" not in session:
        return "로그인이 필요합니다.", 401
    if "file" not in request.files:
        return "파일이 없습니다.", 400
    file = request.files["file"]
    if file.filename == "":
        return "파일이 선택되지 않았습니다.", 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    output_path = protect_image(filepath)
    chat_messages.append({
        "username": session["username"],
        "content": os.path.basename(output_path),
        "type": "image",
        "sender_class": "mymsg",
        "time": current_time()
    })
    return jsonify({"status": "success"}), 200

@app.route("/output/<filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run("0.0.0.0", port=5050, debug=True)