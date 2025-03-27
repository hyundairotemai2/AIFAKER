import os
import cv2
import torch
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from diffusers import DDPMScheduler

# device 설정
device = "cuda" if torch.cuda.is_available() else "cpu"

# DDPM 스케줄러 초기화 (diffusers 라이브러리 필요)
scheduler = DDPMScheduler(
    num_train_timesteps=1000,
    beta_start=0.0001,
    beta_end=0.02,
    beta_schedule="scaled_linear",
)


def apply_ddpm_noise(image_tensor, noise_level):
    """
    DDPM Forward Diffusion 방식으로 노이즈 추가.
    noise_level은 [0,1] 범위의 값으로 타임스텝을 결정합니다.
    """
    timestep = int(noise_level * len(scheduler.timesteps))
    timesteps = torch.tensor([timestep], dtype=torch.long).to(image_tensor.device)
    noise = torch.randn_like(image_tensor)
    noisy_image = scheduler.add_noise(image_tensor, noise, timesteps)
    return torch.clamp(noisy_image, 0, 1)


# Haar Cascade 얼굴 검출기 초기화
haar_model_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_model_path)


def get_face_mask(pil_img):
    """
    Haar Cascade를 사용하여 얼굴 영역을 검출하고,
    해당 영역의 직사각형 마스크를 생성합니다.
    """
    img_np = np.array(pil_img)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    mask = np.zeros((height, width), dtype=np.uint8)

    # Haar Cascade로 얼굴 검출
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        return mask

    # 첫 번째 얼굴의 영역만 직사각형 마스크로 생성
    for x, y, w, h in faces:
        cv2.rectangle(mask, (x, y), (x + w, y + h), 255, thickness=-1)
        break
    return mask


def noise_model(image_path, noise_level, model_name="DDPM"):
    """
    이미지의 얼굴 부분에만 DDPM 기반 노이즈를 적용합니다.
    얼굴 검출에 실패하면 전체 이미지에 노이즈를 적용합니다.

    인자:
      image_path (str): 처리할 이미지의 파일 경로.
      noise_level (float): [0,1] 범위의 노이즈 강도.
      model_name (str): 모델 이름 (기본값 "DDPM").

    반환:
      PIL.Image: 얼굴 영역에 노이즈가 적용된 결과 이미지.
    """
    img = Image.open(image_path).convert("RGB")
    mask_np = get_face_mask(img)
    img_tensor = transforms.ToTensor()(img).unsqueeze(0).to(device)

    if np.sum(mask_np) == 0:
        print("⚠️ 얼굴이 감지되지 않아 전체 이미지에 노이즈를 적용합니다.")
        noisy_img_tensor = apply_ddpm_noise(img_tensor, noise_level)
        result_img = transforms.ToPILImage()(noisy_img_tensor.squeeze(0).cpu())
    else:
        noisy_img_tensor = apply_ddpm_noise(img_tensor, noise_level)
        mask_tensor = (
            torch.from_numpy(mask_np).float().unsqueeze(0).unsqueeze(0).to(device)
            / 255.0
        )
        composite_tensor = (
            img_tensor * (1 - mask_tensor) + noisy_img_tensor * mask_tensor
        )
        result_img = transforms.ToPILImage()(composite_tensor.squeeze(0).cpu())
    return result_img
