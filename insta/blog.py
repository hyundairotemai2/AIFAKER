import os
import base64
import io
from flask import Flask, render_template, request, redirect, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image

app = Flask(__name__)

# 문자열을 datetime 객체로 변환하는 함수
def parse_date(date_str):
    return datetime.strptime(date_str, '%B %d, %Y')

# 임시 데이터 (블로그 글 목록)
posts = [
    {
        'id': 1,
        'title': '파이썬이란?',
        'content': 'Python은 웹 애플리케이션, 소프트웨어 개발, 데이터 과학, 기계 학습에 널리 사용되는 프로그래밍 언어입니다.',
        'image_url': '/static/images/python_img.jpg',
        'date': parse_date('MARCH 15, 2025')
    },
    {
        'id': 2,
        'title': '자바스크립트란?',
        'content': '자바스크립트는 웹 개발에서 가장 널리 사용되는 프로그래밍 언어입니다.',
        'image_url': '/static/images/java_img.png',
        'date': parse_date('MARCH 16, 2025')
    },
]

@app.route('/')
def home():
    sorted_posts = sorted(posts, key=lambda x: x['date'], reverse=True)
    for post in sorted_posts:
        if isinstance(post['date'], datetime):
            post['date_str'] = post['date'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            post['date_str'] = post['date']
    return render_template('another_blog.html', posts=sorted_posts)

@app.route('/post/<int:post_id>')
def post(post_id):
    post_data = next((p for p in posts if p['id'] == post_id), None)
    if post_data is None:
        return "글을 찾을 수 없습니다.", 404
    if isinstance(post_data['date'], datetime):
        post_data['date_str'] = post_data['date'].strftime('%Y-%m-%d %H:%M:%S')
    else:
        post_data['date_str'] = post_data['date']
    return render_template('post_detail.html', post=post_data)

@app.route('/write')
def write():
    return render_template('write.html')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/create_post', methods=['POST'])
def create_post():
    title = request.form['title']
    content = request.form['content']
    image_url = ''
    date = datetime.now()

    if 'image' in request.files:
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            print("이미지 파일 저장 완료:", image_path)
            image_url = f'/static/uploads/{filename}'

    new_id = max(post['id'] for post in posts) + 1 if posts else 1
    posts.append({
        'id': new_id,
        'title': title,
        'content': content,
        'image_url': image_url,
        'date': date
    })
    return redirect('/')

@app.route('/delete/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    global posts
    posts = [p for p in posts if p['id'] != post_id]
    return jsonify({'success': True})

# 흑백 필터 적용 엔드포인트
@app.route('/apply_filter', methods=['POST'])
def apply_filter():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': '이미지 데이터가 제공되지 않았습니다.'}), 400

    image_data_url = data['image']
    try:
        header, encoded = image_data_url.split(',', 1)
        image_data = base64.b64decode(encoded)
    except Exception as e:
        return jsonify({'error': '이미지 처리 중 오류 발생: ' + str(e)}), 400

    temp_input_path = os.path.join(UPLOAD_FOLDER, 'temp_input.png')
    with open(temp_input_path, 'wb') as f:
        f.write(image_data)

    try:
        img = Image.open(temp_input_path).convert('L')  # 흑백 변환
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        buffered.seek(0)
        processed_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        data_url = "data:image/png;base64," + processed_base64
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.remove(temp_input_path)

    return jsonify({'filtered_image': data_url})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
