import os
import cv2
import torch
import numpy as np
import matplotlib.pyplot as plt
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


# 얼굴 검출을 위한 Haar Cascade와 Facemark LBF 초기화
haar_model_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_model_path)

# OpenCV Facemark LBF 초기화 (opencv-contrib-python 필요)
# 현재 파일(noisemodel.py)의 절대 경로를 구합니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
print("현재 파일 경로:", current_dir)

# insta/insta 폴더에서 두 단계 상위로 이동하면 AIFAKER 폴더가 됩니다.
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
print("프로젝트 루트(즉, AIFAKER 폴더) 경로:", project_root)

# AIFAKER 폴더 안에 lbfmodel.yaml 파일이 있는지 확인하고, 그 절대 경로를 구합니다.
lbf_model_path = os.path.join(project_root, "lbfmodel.yaml")
if not os.path.exists(lbf_model_path):
    raise FileNotFoundError(f"lbfmodel.yaml 파일을 찾을 수 없습니다: {lbf_model_path}")
print("lbfmodel.yaml 파일의 절대 경로:", lbf_model_path)
facemark = cv2.face.createFacemarkLBF()
facemark.loadModel(lbf_model_path)


def get_face_mask(pil_img):
    """
    OpenCV의 얼굴 검출기와 Facemark LBF를 사용하여 얼굴 랜드마크를 추출하고,
    얼굴 윤곽(예: 68개 랜드마크, 인덱스 0~68)에 해당하는 부분의 convex hull을 생성하여 마스크로 만듭니다.
    """
    img_np = np.array(pil_img)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    mask = np.zeros((height, width), dtype=np.uint8)

    # Haar Cascade로 얼굴 검출
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        return mask

    # Facemark LBF로 얼굴 랜드마크 추출
    ok, landmarks = facemark.fit(gray, faces)
    if not ok or len(landmarks) == 0:
        return mask

    # 첫 번째 얼굴의 랜드마크 사용 (얼굴 전체 영역: 인덱스 0~68)
    for landmark in landmarks:
        face_contour = landmark[0][0:68].astype(np.int32)
        hull = cv2.convexHull(face_contour)
        cv2.fillConvexPoly(mask, hull, 255)
        break  # 첫 얼굴만 처리
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


# ==============================
# 테스트 코드 (웹 연결 없이 단독 실행)
# ==============================
"""
if __name__ == "__main__":
    # 테스트를 위한 입력 이미지 경로 (test.jpg)
    test_image_path = "input/004.jpg"

    # 테스트 이미지가 없으면 간단한 이미지 생성
    if not os.path.exists(test_image_path):
        test_img = Image.new("RGB", (256, 256), color=(200, 200, 200))
        test_img.save(test_image_path)
        print(f"테스트 이미지를 생성했습니다: {test_image_path}")

    # DDPM 기반 얼굴 보호 적용
    noise_level = 0.05  # 예시 노이즈 레벨
    result_ddpm_face = noise_model(test_image_path, noise_level, model_name="DDPM")

    # 원본 이미지 로드
    original = Image.open(test_image_path).convert("RGB")

    # 결과 이미지 출력 (원본, DDPM 얼굴 보호)
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].imshow(original)
    axes[0].set_title("원본 이미지")
    axes[0].axis("off")

    axes[1].imshow(result_ddpm_face)
    axes[1].set_title("DDPM 얼굴 보호")
    axes[1].axis("off")

    plt.tight_layout()
    plt.show()

"""