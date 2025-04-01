# **AIFAKER**

[코드 깃허브](https://github.com/hyundairotemai2/AIFAKER/blob/main/AIFAKER.ipynb)

[웹페이지](https://aifaker-a7c9ehd0bzbxfpcy.koreasouth-01.azurewebsites.net/)

[프레젠테이션](https://www.canva.com/design/DAGim4xNjVM/OS5Z3hfUzYSrRb0oreUEyw/edit?utm_content=DAGim4xNjVM&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

# 🔧 프로젝트 스택

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
    설계 :after a1, 2025-03-10, 4d
    section 개발
    기능 개발 :2025-03-12, 10d
    테스트 :2025-03-22, 4d
```

## 🗂️ 시스템 아키텍처

```mermaid
flowchart LR
    Model["🧪 노이즈 모델<br/>(Noise_model)"]
    Frontend["🎨 프론트엔드<br/>(Front_end)"]
    Backend["⚙️ Flask 앱<br/>(Webapplication)"]

    GitHub["🌐 GitHub<br/>(Remote Repository)"]
    Actions["🔄 GitHub Actions<br/>(CI/CD Tool)"]
    Azure["☁️ Azure<br/>(Webserver)"]
    Customer["🙋 고객<br/>(Customer)"]

    %% ✅ AI Server 그룹
    subgraph "🧠 AI Server"
        Model --> GitHub
        Frontend --> GitHub
        Backend --> GitHub
    end

    %% ✅ Web Server 그룹
    subgraph "💻 Web Server"
        GitHub --> Actions
        Actions --> Azure
    end

    %% ✅ 데이터 흐름: 사용자로 "결과" 전달
    Azure --> Customer

    %% ✅ 클래스 정의 (노드 색상)
    classDef dev fill:#e6f7ff,stroke:#1890ff,stroke-width:2px;
    classDef code fill:#fffbe6,stroke:#faad14,stroke-width:2px;
    classDef infra fill:#f6ffed,stroke:#52c41a,stroke-width:2px;
    classDef deploy fill:#fff0f6,stroke:#eb2f96,stroke-width:2px;

    %% ✅ 클래스 적용
    class Model,Frontend,Backend code;
    class GitHub,Actions infra;
    class Azure,Customer deploy;
```

##  데이터베이스 아키텍처

```mermaid
erDiagram
    USERS {
        string id PK
        string username
        string password
        string created_at
        string role
    }

    CHAT_MESSAGES {
        string id PK
        string user_id FK
        string username
        string content
        string type
        string sender_class
        string time
        string timestamp
    }

    BLOG_POSTS {
        string id PK
        string user_id
        string username
        string title
        string content
        string image_url
        string date
        string password
        boolean is_filtered
        string original_image_url
    }

    COMMENTS {
        string id PK
        string post_id FK
        string user_id
        string username
        string content
        string date
        string date_str
    }

    BLOB_STORAGE {
        string container_name
        string image_url
        string sas_token
        string access_level
    }

    USERS ||--o{ CHAT_MESSAGES : "sends"
    BLOG_POSTS ||--o{ COMMENTS : "has"
    BLOG_POSTS ||--o{ BLOB_STORAGE : "stores_images"
    CHAT_MESSAGES ||--o{ BLOB_STORAGE : "stores_images"
```

##  노이즈 단계별 이미지 검증 결과
![노이즈 단계별 이미지 검증 결과](https://github.com/user-attachments/assets/a07be288-b4ea-4dea-a116-3b32af515e61)
