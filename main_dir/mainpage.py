import os
import base64
import io
import torch
from flask import Flask, render_template, request, redirect, jsonify, session, send_from_directory, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image
import torchvision.transforms as transforms
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import sys

# UTF-8 인코딩 강제 설정
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
app.secret_key = "supersecretkey"

# 설정
UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'output'
USER_DB = 'users.txt'
BLOG_UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = BLOG_UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(BLOG_UPLOAD_FOLDER, exist_ok=True)

# 채팅 메시지와 블로그 글 저장
chat_messages = []
posts = [
    {
        'id': 1,
        'title': '파이썬이란?',
        'content': 'Python은 웹 애플리케이션, 소프트웨어 개발, 데이터 과학, 기계 학습에 널리 사용되는 프로그래밍 언어입니다.',
        'image_url': '/static/images/python_img.jpg',
        'date': datetime.strptime('MARCH 15, 2025', '%B %d, %Y')
    },
    {
        'id': 2,
        'title': '자바스크립트란?',
        'content': '자바스크립트는 웹 개발에서 가장 널리 사용되는 프로그래밍 언어입니다.',
        'image_url': '/static/images/java_img.png',
        'date': datetime.strptime('MARCH 16, 2025', '%B %d, %Y')
    },
]

# 한글 폰트 설정
def set_korean_font():
    font_candidates = ["NanumGothic", "Malgun Gothic", "AppleGothic"]
    for font in fm.findSystemFonts():
        font_name = fm.FontProperties(fname=font).get_name()
        if font_name in font_candidates:
            plt.rc("font", family=font_name)
            print(f"✅ 한글 폰트 적용: {font_name}")
            return
    print("[경고] 한글 폰트를 찾을 수 없습니다. 기본 폰트 사용.")
set_korean_font()

# 블로그 관련 함수
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_date(date_str):
    return datetime.strptime(date_str, '%B %d, %Y')

# 채팅 관련 함수
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

# 라우트
@app.route('/')
def main():
    try:
        return render_template('main.html')
    except Exception as e:
        return f"템플릿 로드 오류: {str(e)}", 500

@app.route('/blog')
def home():
    sorted_posts = sorted(posts, key=lambda x: x['date'], reverse=True)
    for post in sorted_posts:
        post['date_str'] = post['date'].strftime('%Y-%m-%d %H:%M:%S')
    return render_template('blog.html', posts=sorted_posts)

@app.route('/post/<int:post_id>')
def post(post_id):
    post_data = next((p for p in posts if p['id'] == post_id), None)
    if post_data is None:
        return "글을 찾을 수 없습니다.", 404
    post_data['date_str'] = post_data['date'].strftime('%Y-%m-%d %H:%M:%S')
    # 댓글 데이터 추가 (기본적으로 빈 리스트로 설정하거나 실제 댓글 데이터를 가져와야 함)
    comments = []  # 실제 구현 시 댓글 데이터를 여기에 추가
    return render_template('post_detail.html', post=post_data, comments=comments)

@app.route('/write')
def write():
    return render_template('write.html')

@app.route('/create_post', methods=['POST'])
def create_post():
    title = request.form['title']
    content = request.form['content']
    apply_filter = request.form.get('apply_filter', 'no')
    image_url = ''
    date = datetime.now()

    if 'image' in request.files:
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_url = f'/static/uploads/{filename}'

            if apply_filter == 'yes':
                img = Image.open(image_path).convert('L')
                filtered_filename = f"filtered_{filename}"
                filtered_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filtered_filename)
                img.save(filtered_image_path)
                posts.append({
                    'id': max(post['id'] for post in posts) + 1 if posts else 1,
                    'title': title,
                    'content': content,
                    'image_url': image_url,
                    'filtered_image_url': f'/static/uploads/{filtered_filename}',
                    'apply_filter': True,
                    'date': date
                })
            else:
                posts.append({
                    'id': max(post['id'] for post in posts) + 1 if posts else 1,
                    'title': title,
                    'content': content,
                    'image_url': image_url,
                    'apply_filter': False,
                    'date': date
                })
    else:
        posts.append({
            'id': max(post['id'] for post in posts) + 1 if posts else 1,
            'title': title,
            'content': content,
            'image_url': image_url,
            'apply_filter': False,
            'date': date
        })

    return redirect('/blog')

@app.route('/delete/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    global posts
    posts = [p for p in posts if p['id'] != post_id]
    return jsonify({'success': True})

@app.route('/apply_filter_blog', methods=['POST'])
def apply_filter_blog():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': '이미지 데이터가 제공되지 않았습니다.'}), 400

    image_data_url = data['image']
    try:
        header, encoded = image_data_url.split(',', 1)
        image_data = base64.b64decode(encoded)
    except Exception as e:
        return jsonify({'error': '이미지 처리 중 오류 발생: ' + str(e)}), 400

    temp_input_path = os.path.join(BLOG_UPLOAD_FOLDER, 'temp_input.png')
    with open(temp_input_path, 'wb') as f:
        f.write(image_data)

    try:
        img = Image.open(temp_input_path).convert('L')  # 흑백 변환
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        processed_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        data_url = "data:image/png;base64," + processed_base64
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.remove(temp_input_path)

    return jsonify({'filtered_image': data_url})

@app.route('/login', methods=["GET", "POST"])
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
    return redirect(url_for("main"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    app.run(host="0.0.0.0", port=port, debug=True)