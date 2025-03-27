import os
import base64
import io
import torch
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    jsonify,
    send_from_directory,
)  # send_from_directory 추가
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
from datetime import datetime

# from cosmos import runDemo  # cosmos 모듈은 그대로 사용

# PDG 모델 모듈 import
from PGD_noise import (
    pgdmodel_attack_on_image,
    PGDModelDummyGenerator,
    PGDModelDummyStyleEncoder,
    PGDModelDummyLPIPS,
)

# 전역에서 device 및 모델들을 한 번만 초기화
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("[Global] Using device:", device)

# 전역 모델 초기화 (한 번만 초기화하여 재사용)
generator_model = PGDModelDummyGenerator().to(device)
style_encoder_model = PGDModelDummyStyleEncoder(out_dim=64).to(device)
lpips_model = PGDModelDummyLPIPS().to(device)
print("[Global] 모델 초기화 완료")

app = Flask(__name__)
# SocketIO 객체 생성
socket = SocketIO(app, cors_allowed_origins="*", transports=["websocket", "polling"])

# 업로드 폴더와 별개로 outputs 폴더 생성 (노이즈 적용 이미지 저장용)
OUTPUT_FOLDER = "outputs"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# 문자열을 datetime 객체로 변환하는 함수
def parse_date(date_str):
    return datetime.strptime(date_str, "%B %d, %Y")


# 임시 데이터 (블로그 글 목록)
posts = [
    {
        "id": 1,
        "title": "파이썬이란?",
        "content": "Python은 웹 애플리케이션, 소프트웨어 개발, 데이터 과학, 기계 학습에 널리 사용되는 프로그래밍 언어입니다.",
        "image_url": "/static/images/python_img.jpg",
        "date": parse_date("MARCH 15, 2025"),
    },
    {
        "id": 2,
        "title": "자바스크립트란?",
        "content": "자바스크립트는 웹 개발에서 가장 널리 사용되는 프로그래밍 언어입니다.",
        "image_url": "/static/images/java_img.png",
        "date": parse_date("MARCH 16, 2025"),
    },
]


@app.route("/")
def home():
    sorted_posts = sorted(posts, key=lambda x: x["date"], reverse=True)
    # 날짜를 문자열로 변환
    for post in sorted_posts:
        if isinstance(post["date"], datetime):
            post["date_str"] = post["date"].strftime("%Y-%m-%d %H:%M:%S")
        else:
            post["date_str"] = post["date"]
    return render_template("another_blog.html", posts=sorted_posts)


@app.route("/post/<int:post_id>")
def post(post_id):
    post_data = next((p for p in posts if p["id"] == post_id), None)
    if post_data is None:
        return "글을 찾을 수 없습니다.", 404
    if isinstance(post_data["date"], datetime):
        post_data["date_str"] = post_data["date"].strftime("%Y-%m-%d %H:%M:%S")
    else:
        post_data["date_str"] = post_data["date"]
    return render_template("post_detail.html", post=post_data)


@app.route("/write")
def write():
    return render_template("write.html")


# 업로드 가능한 확장자 지정
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# 이미지 업로드 경로 설정
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# 파일 확장자 검증 함수
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# 이미지 업로드 처리 및 PGD 기반 노이즈 적용 (/create_post)
@app.route("/create_post", methods=["POST"])
def create_post():
    title = request.form["title"]
    content = request.form["content"]
    image_url = ""
    date = datetime.now()  # 현재 날짜를 datetime 객체로 저장

    if "image" in request.files:
        image = request.files["image"]
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(image_path)
            print("이미지 파일 저장 완료:", image_path)

            # 전역에서 초기화한 모델을 사용하여 PGD 기반 adversarial 공격 적용
            try:
                nets = {
                    "generator": generator_model,  # 전역 generator_model 사용
                    "style_encoder": style_encoder_model,  # 전역 style_encoder_model 사용
                }
                processed_image = pgdmodel_attack_on_image(
                    image_path,
                    nets,
                    lpips_model,
                    torch.tensor([1]),
                    epsilon=0.03,
                    alpha=0.01,
                    num_iter=5,
                )
                # 노이즈 적용 이미지 저장: outputs 폴더의 adversarial_input.png 로 저장
                output_filename = "adversarial_input.png"
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)
                processed_image.save(output_path)
                image_url = f"/outputs/{output_filename}"
                print("PGD 기반 노이즈 적용된 이미지 저장 완료:", output_path)
            except Exception as e:
                print("PGD 기반 노이즈 적용 중 오류 발생:", e)
                # 오류 발생 시 원본 이미지를 사용하도록 함
                image_url = f"/static/uploads/{filename}"

    new_id = max(post["id"] for post in posts) + 1 if posts else 1
    posts.append(
        {
            "id": new_id,
            "title": title,
            "content": content,
            "image_url": image_url,
            "date": date,
        }
    )
    return redirect("/")


# 게시글 삭제 처리
@app.route("/delete/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    global posts
    posts = [p for p in posts if p["id"] != post_id]
    return jsonify({"success": True})


# 클라이언트의 프리뷰 이미지에 PGD 기반 노이즈 필터를 적용하는 엔드포인트 (/apply_filter)
@app.route("/apply_filter", methods=["POST"])
def apply_filter():
    data = request.get_json()
    if not data or "image" not in data:
        print("이미지 데이터가 제공되지 않았습니다.")
        return jsonify({"error": "이미지 데이터가 제공되지 않았습니다."}), 400

    image_data_url = data["image"]
    try:
        header, encoded = image_data_url.split(",", 1)
    except Exception as e:
        print("이미지 데이터 URL 파싱 오류:", e)
        return jsonify({"error": "이미지 데이터 형식이 올바르지 않습니다."}), 400

    try:
        image_data = base64.b64decode(encoded)
    except Exception as e:
        print("base64 디코딩 오류:", e)
        return jsonify({"error": "base64 디코딩 실패"}), 400

    # 임시 파일로 저장
    temp_input_path = os.path.join(UPLOAD_FOLDER, "temp_input.png")
    with open(temp_input_path, "wb") as f:
        f.write(image_data)
    print("임시 이미지 파일 저장 완료:", temp_input_path)

    # 전역 모델을 사용하여 이미지 처리
    try:
        nets = {
            "generator": generator_model,  # 전역 generator_model 사용
            "style_encoder": style_encoder_model,  # 전역 style_encoder_model 사용
        }
        processed_image = pgdmodel_attack_on_image(
            temp_input_path,
            nets,
            lpips_model,
            torch.tensor([1]),
            epsilon=0.05,
            alpha=0.01,
            num_iter=10,
        )
        print("PGD 기반 노이즈 모델 적용 완료.")
    except Exception as e:
        print("PGD 기반 노이즈 모델 적용 중 오류 발생:", e)
        return jsonify({"error": str(e)}), 500

    # 노이즈 적용 이미지 저장: outputs 폴더의 adversarial_input.png 로 저장
    output_filename = "adversarial_input.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    processed_image.save(output_path)
    print("노이즈 적용 이미지가 outputs 폴더에 저장됨:", output_path)

    # 임시 파일 삭제
    os.remove(temp_input_path)
    print("임시 이미지 파일 삭제 완료.")

    # JSON 응답에 해당 URL을 포함하여 반환
    return jsonify({"filtered_image": f"/outputs/{output_filename}"})


# outputs 폴더의 파일들을 웹에서 접근할 수 있도록 라우트 추가
@app.route("/outputs/<path:filename>")
def outputs_files(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
