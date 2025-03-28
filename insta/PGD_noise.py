import torch
import torch.nn.functional as F
import torchvision.utils as vutils
from torchvision import transforms
from PIL import Image
import os
import time
from alive_progress import alive_bar


# ---------------------------
# PGDModelDummyGenerator: 생성자 네트워크 클래스
# ---------------------------
class PGDModelDummyGenerator(torch.nn.Module):
    def __init__(self):
        super().__init__()
        # 간단한 CNN 구성: Conv2d -> ReLU -> Conv2d -> Tanh 활성화 함수
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(3, 16, kernel_size=3, padding=1),
            torch.nn.ReLU(),
            torch.nn.Conv2d(16, 3, kernel_size=3, padding=1),
            torch.nn.Tanh(),
        )
        print("[PGDModelDummyGenerator] 모델 초기화 완료")

    def forward(self, x, s=None):
        # 입력 텐서 x의 shape 출력 (디버깅용)
        print("[PGDModelDummyGenerator] forward 호출, 입력 shape:", x.shape)
        return self.net(x)


# ---------------------------
# PGDModelDummyStyleEncoder: 스타일 인코더 네트워크 클래스
# ---------------------------
class PGDModelDummyStyleEncoder(torch.nn.Module):
    def __init__(self, out_dim=64):
        super().__init__()
        self.out_dim = out_dim
        # CNN과 선형 계층을 활용하여 스타일 벡터 생성
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(
                3, 16, kernel_size=3, stride=2, padding=1
            ),  # 크기를 반으로 줄임
            torch.nn.ReLU(),
            torch.nn.AdaptiveAvgPool2d((1, 1)),  # 특징 맵을 1x1로 평균 풀링
            torch.nn.Flatten(),
            torch.nn.Linear(16, out_dim),
        )
        print("[PGDModelDummyStyleEncoder] 모델 초기화 완료, 출력 차원:", out_dim)

    def forward(self, x, y=None):
        print("[PGDModelDummyStyleEncoder] forward 호출, 입력 shape:", x.shape)
        return self.net(x)


# ---------------------------
# PGDModelDummyLPIPS: L1 기반 유사도 측정 모듈
# ---------------------------
class PGDModelDummyLPIPS(torch.nn.Module):
    def forward(self, x, y):
        # 입력 x와 y의 차이를 절대값으로 계산 후 평균을 내어 유사도 측정
        print("[PGDModelDummyLPIPS] forward 호출, 입력 shapes:", x.shape, y.shape)
        return torch.abs(x - y).mean(dim=(1, 2, 3), keepdim=True)


# -----------------------------------------------------------------------------
# PGD 기반 adversarial 공격 함수: 이미지에 대해 공격을 수행하는 함수
# -----------------------------------------------------------------------------
def pgdmodel_attack_on_image(
    image_path,
    nets,
    lpips_model,
    y_ref,
    epsilon=0.05,
    alpha=0.01,
    num_iter=5,
    lam_transfer=1.0,
    lam_vis=10.0,
    lam_lpips=5.0,
    lam_style=5.0,
):
    """
    image_path의 이미지를 로드하여 PGD 기반 adversarial 공격을 수행한 후,
    처리된 이미지를 PIL.Image 객체로 반환합니다.
    """
    # 사용 가능한 장치 설정 (GPU가 있다면 cuda 사용)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[pgdmodel_attack_on_image] 사용 장치:", device)

    # PIL 이미지를 Tensor로 변환하는 transform 객체 생성
    transform = transforms.ToTensor()

    # 이미지 로드 및 RGB 변환
    img_pil = Image.open(image_path).convert("RGB")
    print("[pgdmodel_attack_on_image] 이미지 로드 완료:", image_path)

    # 이미지를 텐서로 변환하고 배치 차원 추가 후, device로 이동
    x = transform(img_pil).unsqueeze(0).to(device)

    # 스타일 인코더의 출력 차원에 맞게 임의의 스타일 벡터 생성 (랜덤 초기화)
    style_dim = nets["style_encoder"].out_dim
    s_ref = torch.randn(1, style_dim).to(device)
    print("[pgdmodel_attack_on_image] 스타일 참조 벡터 생성, 차원:", s_ref.shape)

    # y_ref도 device로 이동 (y_ref는 추가 정보로 사용)
    y_ref = y_ref.to(device)

    # 네트워크들을 device로 이동
    generator = nets["generator"].to(device)
    style_encoder = nets["style_encoder"].to(device)
    print("[pgdmodel_attack_on_image] 네트워크들을 device로 이동 완료")

    # 원본 이미지 텐서 복사
    x_orig = x.detach()

    # 적대적 예제 초기화: 원본 이미지에 약간의 노이즈 추가
    x_adv = x.clone().detach() + 0.001 * torch.randn_like(x)
    x_adv.requires_grad_(True)

    # 배치 내 모든 이미지에 대해 동일한 스타일 벡터 사용
    s_ref_ = s_ref[0].unsqueeze(0).repeat(x.size(0), 1)

    # PGD 공격 진행 (alive_bar를 통해 진행 상황 표시)
    print("[pgdmodel_attack_on_image] PGD 공격 시작")
    with alive_bar(num_iter, title="Adversarial Attack Progress") as bar:
        for iter in range(num_iter):
            # 이전 step의 기울기 초기화
            if x_adv.grad is not None:
                x_adv.grad.zero_()

            # 원본 이미지에 대한 생성 결과 계산 (detach하여 gradient 전파 방지)
            x_fake = generator(x, s_ref_).detach()
            # 적대적 이미지에 대한 생성 결과 계산
            x_fake_adv = generator(x_adv, s_ref_)
            # 스타일 인코딩: 원본 이미지와 적대적 이미지 각각의 스타일 특징 추출
            s_pred = style_encoder(x_fake, y_ref)
            s_pred_adv = style_encoder(x_fake_adv, y_ref)

            # 입력 텐서를 [-1, 1] 범위로 정규화
            x_adv_norm = (x_adv - 0.5) * 2
            x_orig_norm = (x_orig - 0.5) * 2

            # 각 손실 계산:
            loss_transfer = F.mse_loss(x_fake_adv, x_fake)  # 생성 결과 간의 전송 손실
            loss_lpips = lpips_model(
                x_adv_norm, x_orig_norm
            ).mean()  # LPIPS 손실 (유사도 측정)
            loss_vis = F.mse_loss(x_adv, x_orig)  # 시각적 유사성 손실
            loss_style = -F.cosine_similarity(
                s_pred, s_pred_adv, dim=1
            ).mean()  # 스타일 간 유사도 손실 (최대화 목표)

            # 총 손실 계산 (각 항에 람다 계수 적용)
            total_loss = (
                lam_transfer * loss_transfer
                + lam_lpips * loss_lpips
                + lam_vis * loss_vis
                + lam_style * loss_style
            )

            # 현재 반복의 손실 출력 (디버깅용)
            print(f"[Iteration {iter+1}] total_loss: {total_loss.item():.6f}")

            # 역전파를 통해 기울기 계산
            total_loss.backward()

            # 적대적 예제 업데이트: 기울기의 부호를 따라 step 크기(alpha)만큼 업데이트
            with torch.no_grad():
                grad = x_adv.grad.sign()
                x_adv = x_adv + alpha * grad
                # 원본 이미지 기준 epsilon 범위 내로 클램핑
                x_adv = torch.clamp(x_adv, x_orig - epsilon, x_orig + epsilon)
                x_adv.requires_grad_(True)

            # 진행 상황 업데이트
            bar()

    print("[pgdmodel_attack_on_image] PGD 공격 종료")
    # 최종 적대적 예제를 PIL 이미지로 변환 후 반환
    result_img = transforms.ToPILImage()(x_adv.squeeze(0).cpu())
    print("[pgdmodel_attack_on_image] 최종 이미지 변환 완료")
    return result_img
