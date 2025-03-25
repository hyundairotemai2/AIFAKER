import os
import glob
import torch
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import torchvision.transforms as transforms
from tqdm import tqdm
import matplotlib.font_manager as fm
import sys
from flask import Flask, request, render_template, send_from_directory

# UTF-8 인코딩 강제 설정
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def set_korean_font():
    """한글 폰트 자동 설정"""
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
#test
def generate_sgn_noise(image_tensor, strength=0.03):
    """스타일GAN 기반 보호 노이즈 생성"""
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
    """이미지에 스타일GAN 기반 보호 노이즈 적용 후 저장"""
    img = Image.open(image_path).convert("RGB")
    img_tensor = transforms.ToTensor()(img).unsqueeze(0).to("cuda" if torch.cuda.is_available() else "cpu")
    noisy_img_tensor = generate_sgn_noise(img_tensor, noise_level)
    noisy_pil = transforms.ToPILImage()(noisy_img_tensor.squeeze(0).cpu())
    output_path = os.path.join(OUTPUT_FOLDER, os.path.basename(image_path))
    noisy_pil.save(output_path)
    return output_path

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/item")
def item():
    return "item!"

@app.route("/login")
def login():
    return "Login"


@app.route("/apply_filter", methods=["POST"])
def apply_filter():
    if "file" not in request.files:
        return "파일이 없습니다.", 400
    file = request.files["file"]
    if file.filename == "":
        return "파일이 선택되지 않았습니다.", 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    output_path = protect_image(filepath)
    return send_from_directory(OUTPUT_FOLDER, os.path.basename(output_path), as_attachment=False)


if __name__ == "__main__":
    app.run("0.0.0.0", port=5050, debug=True)
