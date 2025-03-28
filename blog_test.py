from flask import Flask, render_template, request, redirect, jsonify
from werkzeug.utils import secure_filename
import os
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.cosmos import CosmosClient
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)

# 임시 데이터
posts = [
    {'id': 1, 'title': '파이썬이란?', 'content': 'Python은 웹 애플리케이션, 소프트웨어 개발, 데이터 과학, 기계 학습에 널리 사용되는 프로그래밍 언어입니다.', 'image_url': '/static/images/python_img.jpg', 'date': 'MARCH 15, 2025'},
    {'id': 2, 'title': '자바스크립트란?', 'content': '자바스크립트는 웹 개발에서 가장 널리 사용되는 프로그래밍 언어입니다.', 'image_url': '/static/images/java_img.png', 'date': 'MARCH 16, 2025'},
]

# Blob Storage 설정
connection_string = "DefaultEndpointsProtocol=https;AccountName=cs1100320046ff00937;AccountKey=h6CP0fugqpsm/1rUDCAJr+TVxZzUpdunVOho0zuCFy4+I/FEXmbfGzsX9FE3QhOoMlbExk4pcZPk+AStgtG0dg==;EndpointSuffix=core.windows.net"
storage_account_url = "https://cs1100320046ff00937.blob.core.windows.net"
blob_container_name = "blob-image"

blob_service_client = BlobServiceClient.from_connection_string(connection_string)
blob_container_client = blob_service_client.get_container_client(blob_container_name)

# Cosmos DB 설정
cosmos_endpoint = "https://aifakerdb.documents.azure.com:443/"  # Azure 포털에서 복사
cosmos_key = "xPefnWEhgirfcxG165O4lSJen1tqcRckZvOPIktny0Z4u6CUj1ZWFPkFlhDsj2ezRQkFIXzkJ9AoACDbxfRNmA=="  # Azure 포털에서 복사
database_name = "blog-db"  # 생성할 데이터베이스 이름
cosmos_container_name = "posts"  # 생성할 컨테이너 이름

# Cosmos DB 클라이언트 설정
cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)

# 데이터베이스가 없으면 생성
try:
    # 데이터베이스 생성
    database = cosmos_client.create_database_if_not_exists(id=database_name)
    print("데이터베이스가 생성되었거나 이미 존재합니다.")
    
    # 컨테이너 생성 (서버리스 계정용)
    container_properties = {
        'id': cosmos_container_name,
        'partitionKey': {
            'paths': ['/id'],
            'kind': 'Hash'
        }
    }
    
    container = database.create_container_if_not_exists(
        id=cosmos_container_name,
        partition_key=container_properties['partitionKey']
    )
    print("컨테이너가 생성되었거나 이미 존재합니다.")
    
except Exception as e:
    print(f"Error: {e}")
    database = cosmos_client.get_database_client(database_name)
    container = database.get_container_client(cosmos_container_name)

# SAS 토큰 생성 함수
def generate_image_sas_url(blob_name):
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=blob_container_name,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=24)  # 24시간 동안 유효
    )
    
    return f"{storage_account_url}/{blob_container_name}/{blob_name}?{sas_token}"

@app.route('/')
def home():
    try:
        # Cosmos DB에서 모든 포스트 가져오기
        query = "SELECT * FROM c ORDER BY c._ts DESC"
        posts = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        # 각 포스트의 이미지 URL 갱신
        for post in posts:
            if 'blob_name' in post:
                post['image_url'] = generate_image_sas_url(post['blob_name'])
        
        return render_template('another_blog.html', posts=posts)
    except Exception as e:
        print(f"Error: {e}")
        return render_template('another_blog.html', posts=[])

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
    try:
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                # 고유한 이미지 이름 생성
                blob_name = f"{str(uuid.uuid4())}.{image.filename.split('.')[-1].lower()}"
                
                # Blob Storage에 업로드
                blob_client = blob_container_client.get_blob_client(blob_name)
                blob_client.upload_blob(image.read(), content_type=f"image/{image.filename.split('.')[-1].lower()}")
                
                # SAS 토큰이 포함된 URL 생성
                image_url = generate_image_sas_url(blob_name)
                
                # Cosmos DB에 저장할 데이터
                post_id = str(uuid.uuid4())
                post_data = {
                    'id': post_id,
                    'title': request.form['title'],
                    'content': request.form['content'],
                    'image_url': image_url,
                    'blob_name': blob_name,  # 나중에 URL 재생성을 위해 저장
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                container.create_item(body=post_data)
                
        return redirect('/')
    except Exception as e:
        print(f"Error creating post: {e}")
        return "포스트 생성 중 오류가 발생했습니다.", 500

@app.route('/delete/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    try:
        # 1. Cosmos DB에서 포스트 정보 가져오기
        post = container.read_item(item=post_id, partition_key=post_id)
        
        # 2. Blob Storage에서 이미지 삭제 (이미지가 있는 경우)
        if post.get('image_url'):
            try:
                # URL에서 blob 이름 추출 (마지막 '/' 이후 부분)
                blob_name = post['image_url'].split('/')[-1]
                blob_client = blob_container_client.get_blob_client(blob_name)
                blob_client.delete_blob()
                print(f"이미지 삭제 완료: {blob_name}")
            except Exception as e:
                print(f"이미지 삭제 중 오류 발생: {e}")
        
        # 3. Cosmos DB에서 포스트 삭제
        container.delete_item(item=post_id, partition_key=post_id)
        print(f"포스트 삭제 완료: {post_id}")
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"삭제 중 오류 발생: {e}")
        return jsonify({'success': False}), 500

if __name__ == '__main__':
    app.run(port=5011, debug=True)