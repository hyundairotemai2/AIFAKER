FROM python:3.12-slim

WORKDIR /app
COPY . /app

# 시스템 라이브러리 먼저 설치 (numpy 빌드에 필요)
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# setuptools와 pip 업데이트
RUN pip uninstall -y setuptools && pip install --no-cache-dir --upgrade pip setuptools wheel

# ✅ numpy를 먼저 명시적으로 설치 (torchvision 등에서 필요함)
RUN pip install --no-cache-dir numpy

# requirements.txt 설치
RUN pip install --no-cache-dir -r requirements.txt

# PyTorch + torchvision (CPU 버전)
RUN pip install torch==2.2.2+cpu torchvision==0.17.2+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html

# 서비스 실행
CMD gunicorn mainpage:app --bind=0.0.0.0:$PORT