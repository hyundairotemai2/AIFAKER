import os
from PIL import Image

def downscale_to_hd_width_overwrite(image_path, target_width=1280):
    img = Image.open(image_path).convert("RGB")
    original_width, original_height = img.size

    if original_width <= target_width:
        print(f"➖ 생략 (이미 HD 이하): {image_path}")
        return

    ratio = target_width / original_width
    new_height = int(original_height * ratio)
    resized_img = img.resize((target_width, new_height), Image.LANCZOS)
    resized_img.save(image_path)
    print(f"✅ 리사이즈 완료: {image_path}")

def downscale_all_images_in_folder(folder_path, target_width=1280):
    exts = ('.jpg', '.jpeg', '.png')
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(exts)]

    if not files:
        print("❌ 처리할 이미지가 없습니다.")
        return

    for file_name in files:
        image_path = os.path.join(folder_path, file_name)
        downscale_to_hd_width_overwrite(image_path, target_width)

    print("🎉 모든 이미지 처리 완료!")

downscale_all_images_in_folder("C:/pycode/AIFAKER/Input")
