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
    %% 👨‍💻 개발자 상세 구성
    subgraph Developer ["👨‍💻 개발자"]
        dev1(["🧪 StarGAN-v2<br/>노이즈 모델 구현"])
        dev2(["🎨 Flask 앱<br/>제어 UI 및 API 개발"])
        dev3(["💾 코드 푸시"])
        dev1 --> dev3
        dev2 --> dev3
    end

    %% CI/CD
    subgraph GitHub_CI_CD ["🛠️ GitHub Actions (CI/CD)"]
        repo["📁 GitHub<br/>Noise Model + Flask Web"]
        workflow["⚙️ 빌드/테스트<br/>+ 배포"]
        repo --> workflow
    end

    %% Azure
    subgraph Azure_Cloud ["☁️ Azure 클라우드"]
        subgraph App_Service ["🚀 Azure App Service (Linux)"]
            app["🌐 Flask 웹 앱<br/>(제어 패널 + API)"]
        end
        db["🗄️ Cosmos DB"]
        kv["🔐 Key Vault"]
    end

    user(["🙋 사용자"]) -->|🌐 요청| app
    app -->|📡 예측 및 데이터| db
    app -->|🔑 시크릿 참조| kv
    dev3 -->|🔁 코드 반영| repo
    workflow -->|🔐 인증 및 배포| app

    %% 스타일
    classDef developer fill:#e6f7ff,stroke:#1890ff,stroke-width:2px;
    classDef github fill:#fffbe6,stroke:#faad14,stroke-width:2px;
    classDef azure fill:#f6ffed,stroke:#52c41a,stroke-width:2px;
    classDef user fill:#fff0f6,stroke:#eb2f96,stroke-width:2px;

    class dev1,dev2,dev3 developer;
    class repo,workflow github;
    class app,db,kv azure;
    class user user;
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
