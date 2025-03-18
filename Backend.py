from flask import Flask, request, send_file
from PIL import Image
from io import BytesIO
import torch
import numpy as np
import torchvision.transforms as transforms
from diffusers import DDPMScheduler
import os

app = Flask(__name__)

# !-- 노이즈 모델 --!
scheduler = DDPMScheduler(num_train_timesteps = 1000, beta_start = 0.0001, beta_end = 0.02, beta_schedule = "scaled_linear")

def apply_denoising_diffusion_probabilistic_models(image_tensor, noise_level):
    timesteps = torch.tensor([int(noise_level * len(scheduler.timesteps))], dtype = torch.long).to(image_tensor.device)
    noise = torch.randn_like(image_tensor)
    noisy_image = scheduler.add_noise(image_tensor, noise, timesteps)
    return torch.clamp(noisy_image, 0, 1)

# 필요 이미지에 VAE 인코더 - TIMESTEP - 노이즈 포함된 걸 이미지로 다시 변환

# !-- 이미지에 노이즈 적용 --!
def protect_image_tensor(img_tensor, noise_level):
    noisy_img_tensor = apply_stable_diffusion_noise(img_tensor, noise_level)
    noisy_pil = transforms.ToPILImage()(noisy_img_tensor.squeeze(0).cpu())
    return noisy_pil

# !-- 이미지 업로드 --!
@app.route('/apply_sdn', methods=['POST'])
def apply_sdn_to_image():
    if 'image' not in request.files:
        return "업로드 된 이미지가 없습니다.", 400
    file = request.files['image']
    if file.filename == '':
        return "선택된 이미지가가 없습니다.", 400
    if file and file.filename.split('.')[-1] not in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
        return "지원하지 않는 이미지 형식입니다. (jpg, jpeg, png, gif, bmp)", 400
    
    # !-- 이미지 노이즈 레벨 선택 --!
    noise_level_str = request.form.get('noise_level', '0.03') # 디폴트 노이즈 값 3%
    try:
        noise_level = float(noise_level_str)
        if not 0 <= noise_level <= 1:
            raise ValueError("노이즈 레벨은 0과 1 사이여야 합니다.")
    except ValueError:
        return "잘못된 노이즈 레벨 값입니다. (0.0에서 1.0 사이의 숫자)", 400
    
    try:
        img = Image.open(file.stream).convert('RGB')
        img_tensor = transforms.ToTensor()(img).unsqueeze(0).to('cuda' if torch.cuda.is_available() else 'cpu')
        
        noisy_pil = protect_image_tensor(img_tensor, noise_level)
        
        #!-- 처리된 이미지를 BytesIO로 변환하여 전송 --!
        output = BytesIO()
        noisy_pil.save(output, format = 'jpg') # jpg로 변환
        output.seek(0)
        return send_file(output, mimetype='image/jpg')
    
    except Exception as e:
        return f"이미지 처리 중 오류가 발생했습니다: {str(e)}", 500
    
#!-- 일단 로컬에서 5000번 포트로 서버 실행 --!
if __name__ == '__main__':
    app.run(debug=True, port = 5000) 