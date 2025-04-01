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

## 웹 - SNS 서비스 플로우
![image](https://github.com/user-attachments/assets/a9b5ad76-9c19-4c83-b06e-29150a9ce59e)


## 웹 - 블로그 서비스 플로우
![image](https://github.com/user-attachments/assets/7daf3bd6-be50-4734-af78-a3af44ca9494)


## SNS 아키텍쳐
```mermaid
flowchart LR
    %% 앱 - 메시저 앱
    subgraph App ["📱 앱 - 메시저 앱"]
        login["🔐 로그인<br/>ID/Password 입력"]
        message["💬 메시지 앱<br/>대화창"]
        login --> message
    end

    %% 이미지 파일 선택
    subgraph Image_Selection ["🖼️ 이미지 파일 선택"]
        select_image["📸 이미지 선택<br/>사진 업로드"]
        message --> select_image
    end

    %% PGD 공격
    subgraph PGD_Attack ["⚔️ PGD 공격"]
        noise_model["🧪 PGD 노이즈 모델<br/>이미지 공격 수행"]
        select_image --> noise_model
    end

    %% 변경된 이미지 전송
    subgraph Modified_Image ["📤 변경된 이미지 전송"]
        modified_message["💬 변경된 이미지<br/>대화창에 전송"]
        noise_model --> modified_message
        modified_message --> message
    end

    %% 스타일
    classDef app fill:#fffbe6,stroke:#faad14,stroke-width:2px;
    classDef image fill:#e6f7ff,stroke:#1890ff,stroke-width:2px;
    classDef attack fill:#f6ffed,stroke:#52c41a,stroke-width:2px;
    classDef modified fill:#fff0f6,stroke:#eb2f96,stroke-width:2px;

    class login,message app;
    class select_image image;
    class noise_model attack;
    class modified_message modified;
```
## Blog 아키텍쳐
``` mermaid
flowchart LR
    %% 앱 - 블로그 앱
    subgraph App ["📱 앱 - 블로그 앱"]
        blog["📝 My Blog<br/>글 목록"]
        write_button["✏️ 글쓰기 버튼"]
        blog --> write_button
    end

    %% 글쓰기
    subgraph Writing ["📄 글쓰기"]
        write_post["🖼️ 이미지 업로드<br/>글 작성"]
        write_button --> write_post
    end

    %% 확인/취소 선택
    subgraph Choice ["🔄 확인/취소 선택"]
        confirm["✅ 확인 버튼"]
        cancel["❌ 취소 버튼"]
        write_post --> confirm
        write_post --> cancel
    end

    %% 확인 버튼: PGD 공격 및 변경된 이미지 업로드
    subgraph Confirm_Path ["✅ 확인: PGD 공격"]
        noise_model["🧪 PGD 노이즈 모델<br/>이미지 공격 수행"]
        modified_post["📜 변경된 이미지 포함<br/>글 업로드"]
        confirm --> noise_model --> modified_post
    end

    %% 취소 버튼: 원본 이미지 업로드
    subgraph Cancel_Path ["❌ 취소: 원본 업로드"]
        original_post["📜 원본 이미지 포함<br/>글 업로드"]
        cancel --> original_post
    end

    %% 서브그래프 스타일
    style App fill:#F5F6F5,stroke:#03C75A,stroke-width:2px; 
    style Writing fill:#FFFFFF,stroke:#03C75A,stroke-width:2px;
    style Choice fill:#E8ECEF,stroke:#333333,stroke-width:1px; 
    style Confirm_Path fill:#E6F5EC,stroke:#03C75A,stroke-width:2px; 
    style Cancel_Path fill:#F5F6F5,stroke:#FF4D4F,stroke-width:2px; 

    %% 노드 스타일
    classDef node_style fill:#FFFFFF,stroke:#333333,stroke-width:1px;
    class blog,write_button,write_post,confirm,cancel,noise_model,modified_post,original_post node_style;
```
## 통합 아키텍쳐
```mermaid
flowchart LR
    %% 앱 진입 (SNS/Blog 통합)
    subgraph App_Entry ["📱 앱 진입 (SNS/Blog)"]
        app_start["📱 앱 시작<br/>(SNS: 메시지 앱, Blog: 글 목록)"]
    end

    %% 이미지 업로드
    subgraph Image_Upload ["🖼️ 이미지 업로드"]
        upload_image["📸 이미지 업로드"]
        app_start --> upload_image
    end

    %% PGD 공격 여부 선택
    subgraph Choice ["🔄 PGD 공격 여부"]
        upload_image -->|✅ PGD 적용| Confirm_Path
        upload_image -->|❌ 원본 유지| Cancel_Path
    end

    %% 확인 경로: PGD 공격
    subgraph Confirm_Path ["✅ PGD 공격"]
        noise_model["🧪 PGD 공격"]
        modified_result["📤 결과<br/>(SNS: 전송, Blog: 업로드)"]
        noise_model --> modified_result
    end

    %% 취소 경로: 원본 이미지
    subgraph Cancel_Path ["❌ 원본 이미지"]
        original_result["📤 결과<br/>(SNS: 전송, Blog: 업로드)"]
    end

    %% 결과 반영
    modified_result --> app_start
    original_result --> app_start

    user(["🙋 사용자"]) -->|🌐 사용| app_start
    
    %% 서브그래프 스타일 (네이버 블로그 테마 간소화)
    style App_Entry fill:#F5F6F5,stroke:#03C75A,stroke-width:1px; %% Naver Blog background and green border
    style Image_Upload fill:#FFFFFF,stroke:#03C75A,stroke-width:1px; %% White background for upload section
    style Choice fill:#E8ECEF,stroke:#333333,stroke-width:1px; %% Light gray for choice section
    style Confirm_Path fill:#E6F5EC,stroke:#03C75A,stroke-width:1px; %% Light green for confirm path
    style Cancel_Path fill:#F5F6F5,stroke:#FF4D4F,stroke-width:1px; %% Default background with red border for cancel path

    %% 노드 스타일 (간소화)
    classDef node_style fill:#FFFFFF,stroke:#333333,stroke-width:1px;
    class app_start,upload_image,noise_model,modified_result,original_result node_style;
```
## 🗂️ CI/CD 파이프라인

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



