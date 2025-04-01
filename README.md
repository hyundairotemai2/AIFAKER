# **AIFAKER**
## PGD 기반 적대적 노이즈를 활용한 딥페이크 방지 필터
[코드 깃허브](https://github.com/hyundairotemai2/AIFAKER/blob/main/AIFAKER.ipynb)

[웹페이지](https://aifaker-a7c9ehd0bzbxfpcy.koreasouth-01.azurewebsites.net/)

[프레젠테이션](https://www.canva.com/design/DAGim4xNjVM/OS5Z3hfUzYSrRb0oreUEyw/edit?utm_content=DAGim4xNjVM&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)


---
# 배경
![image](https://github.com/user-attachments/assets/453aa3b5-57aa-41bb-a935-d75b765a75df)
## 딥페이크만 검색하더라도 관련 범죄에 대해 뉴스가 많다. -> 딥페이크를 방지하는 방법이 없을까?

# 기술
## 딥페이크
### StarGANv2 란?
<li>GAN(생성적 적대 신경망)을 기반으로 한 이미지 변환 모델</li>

![image](https://github.com/user-attachments/assets/53db1040-883c-443b-83d9-4c8554eb601e)

- StarGAN v2의 핵심 기능은 다중 도메인 이미지 변환 ex) 사람 얼굴을 "금발 여성 스타일", "고양이 얼굴 스타일" 등으로 바꾸는 작업.
- 기본 GAN은 단순히 가짜 이미지를 만드는 데 초점이 맞춰져 있다면, StarGAN 시리즈는 이미지 간 변환에 특화
- 작동방식

```mermaid
graph TD
    %% 입력 및 적대적 공격
    A[입력 이미지<br>검은 머리 남성] -->|원본| B[스타일 인코더]
    A -->|적대적 교란| A_adv[적대적 이미지<br>교란된 입력]
    A_adv --> B
    
    %% 스타일 코드 생성
    B --> C[스타일 코드<br>금발 스타일]
    D[랜덤 노이즈] --> E[매핑 네트워크]
    E --> F[스타일 코드<br>새로운 금발 스타일]
    
    %% 이미지 생성
    A --> G[생성자]
    A_adv --> G
    C --> G
    F --> G
    
    %% 판별 과정
    G --> H[출력 이미지<br>금발 남성]
    H --> I[판별자]
    I --> J[진짜/가짜 판단<br>스타일 일치 여부]

    %% 스타일 강조 (수수한 색상 적용)
    classDef attack fill:#e8ecef,stroke:#6c757d,stroke-width:2px;
    class A_adv attack;
```
- **StarGANv2를 딥페이크에 사용하는 이유** 

ㄴ 얼굴 스타일을 자유롭게 바꿀 수 있어서 딥페이크 제작에 활용됨   
                          ㄴ 최신 이미지 변환 모델 중 하나라, 딥페이크 방지 기술을 테스트하기에 적합한 강력한 상대                                                                              
         ㄴ 다양한 스타일을 다룰 수 있고, 결과가 자연스러워서 실제 딥페이크 시나리오를 시뮬레이션하기 좋음
         
## PGD ( 적대적 노이즈 기법 )  

### 정의
-PGD는 적대적 공격 기법으로, 입력 이미지에 작은 노이즈를 반복적으로 추가하여 모델을 속이거나 성능을 저하시키는 방법

-경사 하강법을 사용하며, 교란 크기를 epsilon 범위로 제한

### 작동 방식
-초기 노이즈 추가 후, 손실 함수의 경사를 계산

-경사 방향으로 교란을 업데이트하고, epsilon 내로 투영

-지정된 반복 횟수(num_iter) 동안 최적화

### PGD의 장점
-강력함: 단일 단계 공격보다 효과적인 교란 생성

-조정 가능: epsilon, alpha로 교란 강도 제어

-유연성: LPIPS, MSE 등 다양한 손실 함수 결합 가능

-안정성: 반복적 최적화로 신뢰할 수 있는 결과 제공

# 결과

## 필터 적용 Before vs After

## Before vs After

<div style="display: flex; justify-content: space-around;">
  <div style="text-align: center;">
    <p><strong>Before</strong></p>
    <img src="https://github.com/user-attachments/assets/a6efe100-85c4-4b50-927e-0a377a42f2be" width="45%" alt="Before">
  </div>
  <div style="text-align: center;">
    <p><strong>After</strong></p>
    <img src="https://github.com/user-attachments/assets/dc603cf1-46f9-4842-a3aa-98a7df9e96dd" width="45%" alt="After">
  </div>
</div>

- **Before**: 적대적 노이즈 적용 전
- **After**: 적대적 노이즈 적용 후 결과

## 검증 - StarGANv2를 이용한 딥페이크

## 웹 - SNS 서비스 플로우
![image](https://github.com/user-attachments/assets/a9b5ad76-9c19-4c83-b06e-29150a9ce59e)


## 웹 - 블로그 서비스 플로우
![image](https://github.com/user-attachments/assets/7daf3bd6-be50-4734-af78-a3af44ca9494)



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

    %% PGD 필터링 여부 선택
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

# 🔧 프로젝트 스택

> Flask 기반 웹 애플리케이션 + 노이즈 모델 + 프론트엔드 통합 프로젝트  
> GitHub Actions를 활용한 CI/CD와 Azure 배포까지 전 과정 포함


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



