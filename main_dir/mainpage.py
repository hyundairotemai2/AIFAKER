import os
import base64
import io
import torch
import uuid
from flask import Flask, render_template, request, redirect, jsonify, session, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from PIL import Image
import torchvision.transforms as transforms
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
import sys



# .env 파일 로드
load_dotenv()

# Azure 설정
BLOB_CONNECTION_STRING = os.getenv('BLOB_CONNECTION_STRING')
BLOB_STORAGE_URL = os.getenv('BLOB_STORAGE_URL')
BLOB_CONTAINER_NAME = "blog-images"
BLOB_CHAT_IMAGES_CONTAINER = os.getenv('BLOB_CHAT_IMAGES_CONTAINER')
STORAGE_ACCOUNT_NAME = os.getenv('STORAGE_ACCOUNT_NAME')
STORAGE_ACCOUNT_KEY = os.getenv('STORAGE_ACCOUNT_KEY')

COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
COSMOS_KEY = os.getenv('COSMOS_KEY')
COSMOS_DATABASE_NAME = os.getenv('COSMOS_DATABASE_NAME')
COSMOS_CHAT_DATABASE_NAME = os.getenv('COSMOS_CHAT_DATABASE_NAME')
COSMOS_POSTS_CONTAINER = "posts"
COSMOS_MESSAGES_CONTAINER = os.getenv('COSMOS_MESSAGES_CONTAINER')
COSMOS_USERS_CONTAINER = os.getenv('COSMOS_USERS_CONTAINER')

# Azure 클라이언트 초기화
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
blob_chat_images_client = blob_service_client.get_container_client(BLOB_CHAT_IMAGES_CONTAINER)
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

# Cosmos DB 컨테이너 초기화
cosmos_database = cosmos_client.get_database_client(COSMOS_DATABASE_NAME)
cosmos_container = cosmos_database.get_container_client(COSMOS_POSTS_CONTAINER)

cosmos_chat_database = cosmos_client.get_database_client(COSMOS_CHAT_DATABASE_NAME)
cosmos_messages_container = cosmos_chat_database.get_container_client(COSMOS_MESSAGES_CONTAINER)
cosmos_users_container = cosmos_chat_database.get_container_client(COSMOS_USERS_CONTAINER)

# UTF-8 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
app.secret_key = "supersecretkey"

# 유틸리티 함수
def generate_unique_id():
    return str(uuid.uuid4())

def current_time():
    now = datetime.now()
    hh = now.hour
    mm = now.minute
    apm = "오후" if hh >= 12 else "오전"
    hh = hh % 12 or 12
    return f"{apm} {hh}:{mm:02d}"

def upload_to_blob(file_data, filename, container_client=None, user_id=None, post_id=None):
    if container_client is None:
        container_client = blob_container_client
    
    # 파일명에 사용자 ID와 게시물 ID 포함
    if user_id and post_id:
        filename = f"{user_id}/{post_id}/{filename}"
    elif user_id:
        filename = f"{user_id}/{filename}"
    
    blob_client = container_client.get_blob_client(filename)
    blob_client.upload_blob(file_data, overwrite=True)
    
    sas_token = generate_blob_sas(
        account_name=STORAGE_ACCOUNT_NAME,
        container_name=container_client.container_name,
        blob_name=filename,
        account_key=STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=24)
    )
    
    return f"{blob_client.url}?{sas_token}"

# 이미지 처리 함수
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

def protect_image(image_data):
    img = Image.open(io.BytesIO(image_data)).convert("RGB")
    img_tensor = transforms.ToTensor()(img).unsqueeze(0).to("cuda" if torch.cuda.is_available() else "cpu")
    noisy_img_tensor = generate_sgn_noise(img_tensor)
    noisy_pil = transforms.ToPILImage()(noisy_img_tensor.squeeze(0).cpu())
    
    buffered = io.BytesIO()
    noisy_pil.save(buffered, format="PNG")
    return buffered.getvalue()

# 블로그 관련 함수
def get_posts():
    query = "SELECT * FROM c ORDER BY c.date DESC"
    return list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))

def save_post(post_data):
    post_data['created_at'] = datetime.now().isoformat()
    cosmos_container.create_item(body=post_data)

# 채팅 관련 함수
def get_chat_messages():
    query = "SELECT * FROM c ORDER BY c.timestamp DESC"
    return list(cosmos_messages_container.query_items(query=query, enable_cross_partition_query=True))

def save_chat_message(message_data):
    message_data['timestamp'] = datetime.now().isoformat()
    cosmos_messages_container.create_item(body=message_data)

def load_users():
    query = "SELECT * FROM c"
    items = list(cosmos_users_container.query_items(query=query, enable_cross_partition_query=True))
    return {item['username']: item for item in items}

def save_user(username, password):
    user_id = generate_unique_id()
    user_data = {
        'id': user_id,
        'username': username,
        'password': password,
        'created_at': datetime.now().isoformat(),
        'role': 'user'  # 사용자 역할 추가
    }
    cosmos_users_container.create_item(body=user_data)
    return user_id

# 라우트
@app.route('/')
def main():
    return render_template('main.html')

@app.route('/blog')
def blog():
    posts = get_posts()
    for post in posts:
        post['date'] = datetime.fromisoformat(post['date']).strftime('%Y-%m-%d %H:%M')
    return render_template('blog.html', posts=posts)

@app.route('/post/<string:post_id>')
def post(post_id):
    query = f"SELECT * FROM c WHERE c.id = '{post_id}'"
    posts = list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))
    if posts:
        post = posts[0]
        post['date'] = datetime.fromisoformat(post['date']).strftime('%Y-%m-%d %H:%M')
        return render_template('post.html', post=post)
    return "게시물을 찾을 수 없습니다.", 404

@app.route('/write')
def write():
    return render_template('write.html')

@app.route('/create_post', methods=['POST'])
def create_post():
    title = request.form["title"]
    content = request.form["content"]
    image = request.files.get("image")
    password = request.form.get("password", "")
    apply_filter = request.form.get("apply_filter", "false") == "true"  # 필터 적용 여부 추가

    anonymous_id = generate_unique_id()
    post_id = generate_unique_id()

    image_url = None
    filtered_image_url = None

    if image:
        filename = secure_filename(image.filename)
        image_data = image.read()
        image_url = upload_to_blob(image_data, filename, user_id=anonymous_id, post_id=post_id)

        if apply_filter:  # 필터 적용 로직 추가
            filtered_image_data = apply_grayscale_filter(image_data)
            filtered_filename = f"filtered_{filename}"
            filtered_image_url = upload_to_blob(filtered_image_data, filtered_filename, user_id=anonymous_id, post_id=post_id)

    post_data = {
        'id': post_id,
        'user_id': anonymous_id,
        'username': '익명',
        'title': title,
        'content': content,
        'image_url': image_url,
        'filtered_image_url': filtered_image_url,  # 추가
        'apply_filter': apply_filter,  # 추가
        'filter_applied': False,  # 추가
        'date': datetime.now().isoformat(),
        'password': password
    }

    save_post(post_data)
    return redirect(url_for("blog"))

def apply_grayscale_filter(image_data):
    img = Image.open(io.BytesIO(image_data)).convert("L")  # 흑백 변환
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()

@app.route('/delete/<string:post_id>', methods=['POST'])
def delete_post(post_id):
    password = request.form.get("password", "")
    
    query = f"SELECT * FROM c WHERE c.id = '{post_id}'"
    posts = list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))
    if posts:
        post = posts[0]
        if post.get('password') == password:
            cosmos_container.delete_item(item=post, partition_key=post['id'])
            return jsonify({'success': True})
        else:
            return "비밀번호가 일치하지 않습니다.", 403
    return "게시물을 찾을 수 없습니다.", 404

@app.route('/apply_filter', methods=['POST'])
def apply_filter():
    if "username" not in session:
        return "로그인이 필요합니다.", 401
    if "file" not in request.files:
        return "파일이 없습니다.", 400
    file = request.files["file"]
    if file.filename == "":
        return "파일이 선택되지 않았습니다.", 400

    # 사용자 정보 가져오기
    users = load_users()
    user = users.get(session["username"])
    if not user:
        return "사용자를 찾을 수 없습니다.", 404

    file_data = file.read()
    processed_image_data = protect_image(file_data)
    
    filename = secure_filename(file.filename)
    processed_filename = f"processed_{filename}"
    image_url = upload_to_blob(processed_image_data, processed_filename, blob_chat_images_client, user_id=user['id'])
    
    message_data = {
        'id': generate_unique_id(),
        'user_id': user['id'],
        'username': session["username"],
        'content': image_url,
        'type': 'image',
        'sender_class': 'mymsg',
        'time': current_time()
    }
    
    save_chat_message(message_data)
    return jsonify({"status": "success", "image_url": image_url}), 200


@app.route('/comments/<string:post_id>', methods=['POST'])
def add_comment(post_id):
    content = request.json.get('content')
    if not content:
        return jsonify({'success': False, 'error': '내용이 없습니다.'}), 400

    comment_data = {
        'id': generate_unique_id(),
        'post_id': post_id,
        'content': content,
        'date_str': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'username': '익명'  # 필요 시 사용자 인증 추가
    }
    cosmos_container.create_item(body=comment_data)  # 동일 컨테이너 사용, 별도 컨테이너 필요 시 수정
    return jsonify({'success': True, 'comment': comment_data})


@app.route('/apply_filter_blog', methods=['POST'])
def apply_filter_blog():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': '이미지 데이터가 제공되지 않았습니다.'}), 400

    try:
        header, encoded = data['image'].split(',', 1)
        image_data = base64.b64decode(encoded)
        processed_image_data = protect_image(image_data)
        processed_base64 = base64.b64encode(processed_image_data).decode('utf-8')
        return jsonify({'filtered_image': f"data:image/png;base64,{processed_base64}"})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark_filter_applied/<string:post_id>', methods=['POST'])
def mark_filter_applied(post_id):
    query = f"SELECT * FROM c WHERE c.id = '{post_id}'"
    posts = list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))
    if posts:
        post = posts[0]
        post['filter_applied'] = True
        cosmos_container.replace_item(item=post, body=post)
        return jsonify({'success': True})
    return jsonify({'error': '게시물을 찾을 수 없습니다.'}), 404

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        if username in users and users[username]['password'] == password:
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
    messages = get_chat_messages()
    return render_template("kakao.html", messages=messages, username=session["username"])

@app.route("/send_message", methods=["POST"])
def send_message():
    if "username" not in session:
        return "로그인이 필요합니다.", 401
        
    # 사용자 정보 가져오기
    users = load_users()
    user = users.get(session["username"])
    if not user:
        return "사용자를 찾을 수 없습니다.", 404
        
    message = request.form["message"]
    sender_class = request.form["sender_class"]
    
    message_data = {
        'id': generate_unique_id(),
        'user_id': user['id'],
        'username': session["username"],
        'content': message,
        'type': 'text',
        'sender_class': sender_class,
        'time': current_time()
    }
    
    save_chat_message(message_data)
    return jsonify({"status": "success"}), 200

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("main"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)