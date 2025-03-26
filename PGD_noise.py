import torch
import torch.nn.functional as F
import torchvision.utils as vutils
from torchvision import transforms
from PIL import Image
from tkinter import Tk, filedialog
import os
import time
from alive_progress import alive_bar

# ---------------------------
# Dummy Generator
# ---------------------------
class DummyGenerator(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(3, 16, kernel_size=3, padding=1),
            torch.nn.ReLU(),
            torch.nn.Conv2d(16, 3, kernel_size=3, padding=1),
            torch.nn.Tanh()
        )

    def forward(self, x, s=None):
        return self.net(x)

# ---------------------------
# Dummy Style Encoder
# ---------------------------
class DummyStyleEncoder(torch.nn.Module):
    def __init__(self, out_dim=64):
        super().__init__()
        self.out_dim = out_dim
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1),
            torch.nn.ReLU(),
            torch.nn.AdaptiveAvgPool2d((1, 1)),
            torch.nn.Flatten(),
            torch.nn.Linear(16, out_dim)
        )

    def forward(self, x, y=None):
        return self.net(x)

# ---------------------------
# Dummy LPIPS (L1 기반)
# ---------------------------
class DummyLPIPS(torch.nn.Module):
    def forward(self, x, y):
        return torch.abs(x - y).mean(dim=(1, 2, 3), keepdim=True)

# ---------------------------
# Main Attack Function
# ---------------------------
def adversarial_input_attack_with_lpips_and_style_ui(
    nets, lpips_model, y_ref,
    epsilon=0.05, alpha=0.01, num_iter=10,
    lam_transfer=1.0, lam_vis=10.0, lam_lpips=5.0, lam_style=5.0,
    save_dir="./outputs"
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ✅ 이미지 선택창
    Tk().withdraw()
    image_path = filedialog.askopenfilename(title="이미지를 선택하세요")
    if not image_path:
        print("❌ 이미지가 선택되지 않았습니다.")
        return

    print(f"✅ 선택된 이미지: {image_path}")

    # ✅ 원본 사이즈 유지하며 불러오기
    transform = transforms.ToTensor()
    img_pil = Image.open(image_path).convert("RGB")
    x = transform(img_pil).unsqueeze(0).to(device)  # (1, 3, H, W)

    # ✅ 랜덤 스타일 벡터 생성
    style_dim = nets['style_encoder'].out_dim
    s_ref = torch.randn(1, style_dim).to(device)
    y_ref = y_ref.to(device)

    generator = nets['generator'].to(device)
    style_encoder = nets['style_encoder'].to(device)

    x_orig = x.detach()
    x_adv = x.clone().detach() + 0.001 * torch.randn_like(x)
    x_adv.requires_grad_(True)

    s_ref_ = s_ref[0].unsqueeze(0).repeat(x.size(0), 1)

    with alive_bar(num_iter, title='Adversarial Attack Progress') as bar:
        for _ in range(num_iter):
            if x_adv.grad is not None:
                x_adv.grad.zero_()

            x_fake = generator(x, s_ref_).detach()
            x_fake_adv = generator(x_adv, s_ref_)

            s_pred = style_encoder(x_fake, y_ref)
            s_pred_adv = style_encoder(x_fake_adv, y_ref)

            x_adv_norm = (x_adv - 0.5) * 2
            x_orig_norm = (x_orig - 0.5) * 2

            loss_transfer = F.mse_loss(x_fake_adv, x_fake)
            loss_lpips    = lpips_model(x_adv_norm, x_orig_norm).mean()
            loss_vis      = F.mse_loss(x_adv, x_orig)
            loss_style    = -F.cosine_similarity(s_pred, s_pred_adv, dim=1).mean()

            total_loss = (
                lam_transfer * loss_transfer +
                lam_lpips * loss_lpips +
                lam_vis * loss_vis +
                lam_style * loss_style
            )

            total_loss.backward()

            with torch.no_grad():
                grad = x_adv.grad.sign()
                x_adv = x_adv + alpha * grad
                x_adv = torch.clamp(x_adv, x_orig - epsilon, x_orig + epsilon)
                x_adv.requires_grad_(True)

            time.sleep(0.1)
            bar()

    # ✅ 노이즈 이미지 저장
    os.makedirs(save_dir, exist_ok=True)
    adv_path = os.path.join(save_dir, "adversarial_input.png")
    vutils.save_image(x_adv, adv_path, normalize=True)

    print(f"✅ 공격 이미지 저장됨: {adv_path}")

# ---------------------------
# 실행
# ---------------------------
if __name__ == "__main__":
    nets = {
        'generator': DummyGenerator(),
        'style_encoder': DummyStyleEncoder(out_dim=64)
    }

    lpips_model = DummyLPIPS()

    adversarial_input_attack_with_lpips_and_style_ui(
        nets=nets,
        lpips_model=lpips_model,
        y_ref=torch.tensor([1])
    )
