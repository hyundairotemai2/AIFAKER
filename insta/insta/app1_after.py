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
from diffusers import DDPMScheduler

# UTF-8 인코딩 강제 설정
sys.stdout.reconfigure(encoding="utf-8")

# Flask 애플리케이션 및 폴더 설정
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

# 🔥 DDPM 스케줄러 설정 (diffusers 라이브러리 필요)
scheduler = DDPMScheduler(
    num_train_timesteps=1000,
    beta_start=0.0001,
    beta_end=0.02,
    beta_schedule="scaled_linear",
)


def apply_ddpm_noise(image_tensor, noise_level):
    """DDPM Forward Diffusion 방식으로 노이즈 추가"""
    timestep = int(noise_level * len(scheduler.timesteps))
    timesteps = torch.tensor([timestep], dtype=torch.long).to(image_tensor.device)
    noise = torch.randn_like(image_tensor)
    noisy_image = scheduler.add_noise(image_tensor, noise, timesteps)
    return torch.clamp(noisy_image, 0, 1)


def protect_image(image_path, output_base, noise_level, model_name):
    """이미지에 DDPM 기반 보호 노이즈 적용 후 저장"""
    img = Image.open(image_path).convert("RGB")
    img_tensor = (
        transforms.ToTensor()(img)
        .unsqueeze(0)
        .to("cuda" if torch.cuda.is_available() else "cpu")
    )

    noisy_img_tensor = apply_ddpm_noise(img_tensor, noise_level)
    noisy_pil = transforms.ToPILImage()(noisy_img_tensor.squeeze(0).cpu())

    # 원본 확장자 유지
    _, ext = os.path.splitext(image_path)
    output_path = f"{output_base}_{model_name}_{int(noise_level*100)}{ext.lower()}"
    output_path = os.path.join(
        OUTPUT_FOLDER, os.path.basename(output_path)
    )  # 최종 저장 경로

    noisy_pil.save(output_path)
    return noisy_pil


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

    # noise_level과 model_name은 필요에 따라 조정 가능 (여기서는 예시로 0.05, "DDPM")
    output_image = protect_image(
        filepath, os.path.splitext(file.filename)[0], 0.05, "DDPM"
    )
    return send_from_directory(
        OUTPUT_FOLDER,
        os.path.basename(
            os.path.join(OUTPUT_FOLDER, os.path.basename(output_image.filename))
        ),
        as_attachment=False,
    )


if __name__ == "__main__":
    app.run("0.0.0.0", port=5050, debug=True)
