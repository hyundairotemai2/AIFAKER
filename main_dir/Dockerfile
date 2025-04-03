FROM python:3.12-slim

WORKDIR /app
COPY . /app

# ✅ 필수 패키지 (numpy 빌드에 반드시 필요)
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# ✅ pip 업그레이드
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ✅ numpy 먼저 (torchvision 등의 to_tensor 사용을 위해)
RUN pip install --no-cache-dir numpy

# ✅ 나머지 패키지
RUN pip install --no-cache-dir -r requirements.txt

# ✅ torch 마지막에
RUN pip install torch==2.2.2+cpu torchvision==0.17.2+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html

CMD gunicorn mainpage:app --bind=0.0.0.0:$PORT