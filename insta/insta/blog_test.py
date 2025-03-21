from flask import Flask, render_template, request, redirect, jsonify
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# 임시 데이터
posts = [
    {'id': 1, 'title': '파이썬이란?', 'content': 'Python은 웹 애플리케이션, 소프트웨어 개발, 데이터 과학, 기계 학습에 널리 사용되는 프로그래밍 언어입니다.', 'image_url': '/static/images/python_img.jpg', 'date': 'MARCH 15, 2025'},
    {'id': 2, 'title': '자바스크립트란?', 'content': '자바스크립트는 웹 개발에서 가장 널리 사용되는 프로그래밍 언어입니다.', 'image_url': '/static/images/java_img.png', 'date': 'MARCH 16, 2025'},
]

@app.route('/')
def home():
    return render_template('another_blog.html', posts=posts)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = next((p for p in posts if p['id'] == post_id), None)
    if post is None:
        return "글을 찾을 수 없습니다.", 404
    return render_template('post_detail.html', post=post)

@app.route('/write')
def write():
    return render_template('write.html')

# 업로드 가능한 확장자 지정
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 이미지 업로드 경로 설정
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 업로드 폴더가 없으면 생성
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 파일 확장자 검증 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 이미지 업로드 처리
@app.route('/create_post', methods=['POST'])
def create_post():
    title = request.form['title']
    content = request.form['content']
    image_url = ''

    if 'image' in request.files:
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_url = f'/static/uploads/{filename}'
    
    new_id = max(post['id'] for post in posts) + 1 if posts else 1
    posts.append({'id': new_id, 'title': title, 'content': content, 'image_url': image_url, 'date': 'MARCH 20, 2025'})
    
    return redirect('/')


@app.route('/delete/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    global posts
    posts = [p for p in posts if p['id'] != post_id]
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(port=5011, debug=True)
