FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y build-essential

RUN pip uninstall -y setuptools && pip install --no-cache-dir --upgrade pip setuptools wheel

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install torch==2.2.2+cpu torchvision==0.17.2+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html

# ✅ 여기만 수정
CMD gunicorn mainpage:app --bind=0.0.0.0:$PORT