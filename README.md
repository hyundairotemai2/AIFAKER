# **AIFAKER**

[코드 깃허브](https://github.com/hyundairotemai2/AIFAKER/blob/main/AIFAKER.ipynb)

[웹페이지](https://aifaker-a7c9ehd0bzbxfpcy.koreasouth-01.azurewebsites.net/)

[프레젠테이션](https://www.canva.com/design/DAGim4xNjVM/OS5Z3hfUzYSrRb0oreUEyw/edit?utm_content=DAGim4xNjVM&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

```mermaid
gantt
    title 프로젝트 일정
    dateFormat 2025-03
    section 준비
    기획 :a1, 2025-03-03, 7d
    설계 :after a1 2025-03-11, 4d
    section 개발
    기능 개발 :2025-03-12, 10d
    테스트 :2025-03-22, 4d
    flowchart LR
```

```mermaid
    Engineer["👨‍💻 개발자<br/>(Engineer)"]
    IDE["🧱 VSCode<br/>(IDE)"]
    Codebase["📂 코드베이스<br/>(Project Structure)"]

    Model["🧪 노이즈 모델<br/>(Noise_model)"]
    Frontend["🎨 프론트엔드<br/>(Front_end)"]
    Backend["⚙️ Flask 앱<br/>(Webapplication)"]

    GitHub["🌐 GitHub<br/>(Remote Repository)"]
    Actions["🔄 GitHub Actions<br/>(CI/CD Tool)"]
    Azure["☁️ Azure<br/>(Webserver)"]
    Customer["🙋 사용자<br/>(Customer)"]

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

    %% ✅ 클래스 정의 (노드 색상)
    classDef dev fill:#e6f7ff,stroke:#1890ff,stroke-width:2px;
    classDef code fill:#fffbe6,stroke:#faad14,stroke-width:2px;
    classDef infra fill:#f6ffed,stroke:#52c41a,stroke-width:2px;
    classDef deploy fill:#fff0f6,stroke:#eb2f96,stroke-width:2px;

    %% ✅ 클래스 적용
    class Engineer,IDE dev;
    class Codebase,Model,Frontend,Backend code;
    class GitHub,Actions infra;
    class Azure,Customer deploy;
```
