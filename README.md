# **AIFAKER**

[코드 깃허브](https://github.com/hyundairotemai2/AIFAKER/blob/main/AIFAKER.ipynb)

[웹페이지](https://aifaker-a7c9ehd0bzbxfpcy.koreasouth-01.azurewebsites.net/)

[프레젠테이션](https://www.canva.com/design/DAGim4xNjVM/OS5Z3hfUzYSrRb0oreUEyw/edit?utm_content=DAGim4xNjVM&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

# 🔧 프로젝트 이름 (예: Noise-Aware Web Platform)

> Flask 기반 웹 애플리케이션 + 노이즈 모델 + 프론트엔드 통합 프로젝트  
> GitHub Actions를 활용한 CI/CD와 Azure 배포까지 전 과정 포함

---

## 📅 프로젝트 일정

```mermaid
gantt
    title 프로젝트 일정
    dateFormat 2025-03
    section 준비
    기획 :a1, 2025-03-03, 7d
    설계 :after a1, 2025-03-11, 4d
    section 개발
    기능 개발 :2025-03-12, 10d
    테스트 :2025-03-22, 4d
```

```mermaid
flowchart LR
    Engineer["👨‍💻 개발자 (Engineer)"]
    IDE["🧱 VSCode (IDE)"]
    Codebase["📂 코드베이스 (Project Structure)"]

    Model["🧪 노이즈 모델 (Noise_model)"]
    Frontend["🎨 프론트엔드 (Front_end)"]
    Backend["⚙️ Flask 앱 (Webapplication)"]

    GitHub["🌐 GitHub (Remote Repository)"]
    Actions["🔄 GitHub Actions (CI/CD Tool)"]
    Azure["☁️ Azure (Webserver)"]
    Customer["🙋 사용자 (Customer)"]

    Engineer --> IDE
    IDE --> Codebase
    Codebase --> Model
    Codebase --> Frontend
    Codebase --> Backend

    Model --> GitHub
    Frontend --> GitHub
    Backend --> GitHub

    GitHub --> Actions
    Actions --> Azure
    Azure --> Customer
```
