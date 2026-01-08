# 🚀 온라인 배포 가이드

## ⚠️ 배포 전 필수 확인사항

### 1. API Key 보안 ✅ (완료)
- ✅ `.env` 파일로 API 키 분리
- ✅ `.gitignore`에 `.env`, `config.py` 추가
- ✅ `config.py`에서 환경 변수로 API 키 로드

### 2. CSV 파일 업로드 ✅ (가능)
**결론: 온라인 배포 후에도 CSV 파일 업로드 가능합니다!**

Streamlit의 `st.file_uploader()`는:
- ✅ 로컬에서 작동
- ✅ Streamlit Cloud에서도 작동
- ✅ 사용자가 브라우저에서 직접 파일 업로드
- ✅ 서버 메모리에 임시 저장 → 세션 종료 시 자동 삭제

---

## 📦 배포 방법 (3가지)

### 방법 1: Streamlit Community Cloud (무료, 추천) ⭐

**장점**:
- ✅ 완전 무료
- ✅ GitHub 연동 자동 배포
- ✅ HTTPS 자동 제공
- ✅ 파일 업로드 지원

**단점**:
- ❌ 무료 플랜: 리소스 제한 (1GB RAM, 800MB 저장소)
- ❌ 공개 저장소만 무료 (비공개는 유료)

**배포 단계**:

#### 1. GitHub Repository 생성
```bash
cd /Users/inseoplee/Desktop/rag_Test

# Git 초기화 (아직 안 했다면)
git init

# .gitignore 확인 (.env가 포함되어 있는지)
cat .gitignore

# 파일 추가
git add .
git commit -m "Initial commit - AI Data Analyst v2.1"

# GitHub에서 새 저장소 생성 후
git remote add origin https://github.com/your-username/ai-data-analyst.git
git branch -M main
git push -u origin main
```

**⚠️ 중요: GitHub에 푸시하기 전 확인**:
```bash
# API 키가 포함된 파일이 있는지 확인
git status

# .env 파일이 staging area에 없는지 확인
# 만약 있다면:
git reset HEAD .env
```

#### 2. Streamlit Cloud 배포
1. [share.streamlit.io](https://share.streamlit.io) 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. Repository 선택: `your-username/ai-data-analyst`
5. Branch: `main`
6. Main file path: `app.py`
7. **Advanced settings** 클릭 → **Secrets** 추가:
   ```toml
   GOOGLE_API_KEY = "AIzaSyDerwkzYbYNJwuAQivHACGrVS9_2kuoV7E"
   ```
8. "Deploy!" 클릭

#### 3. 배포 완료
- URL: `https://your-app-name.streamlit.app`
- 자동 HTTPS 적용
- GitHub push 시 자동 재배포

---

### 방법 2: Hugging Face Spaces (무료, 대안)

**장점**:
- ✅ 완전 무료
- ✅ 비공개 저장소 지원
- ✅ GPU 지원 (유료)

**배포 단계**:
1. [huggingface.co/spaces](https://huggingface.co/spaces) 접속
2. "Create new Space" 클릭
3. SDK: **Streamlit** 선택
4. Git clone 후 코드 업로드
5. Settings → Repository secrets에 API 키 추가:
   - Name: `GOOGLE_API_KEY`
   - Value: `your-api-key`

---

### 방법 3: 자체 서버 (VPS/AWS/GCP)

**필요한 경우**:
- 대용량 데이터 처리
- 커스텀 도메인
- 완전한 제어 필요

**간단한 배포 (Ubuntu 예시)**:
```bash
# 서버 접속 후
git clone https://github.com/your-username/ai-data-analyst.git
cd ai-data-analyst

# Python 환경 설정
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env 파일 생성
echo "GOOGLE_API_KEY=your-api-key-here" > .env

# Streamlit 실행
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

**NGINX 리버스 프록시 설정** (HTTPS):
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 🔒 보안 체크리스트

배포 전 반드시 확인:

- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는가?
- [ ] `config.py`가 `.gitignore`에 포함되어 있는가?
- [ ] GitHub 저장소에 API 키가 노출되지 않았는가?
- [ ] Streamlit Cloud Secrets에 API 키를 추가했는가?
- [ ] 로컬에서 `.env` 파일이 제대로 로드되는가?

**확인 방법**:
```bash
# GitHub에 푸시된 파일 확인
git ls-files | grep -E "\\.env|config\\.py"
# 아무것도 출력되지 않아야 함!

# 로컬 테스트
python3 -c "from config import GOOGLE_API_KEY; print('✅ API Key loaded:', bool(GOOGLE_API_KEY))"
```

---

## 💾 파일 업로드 제한사항

### Streamlit Cloud 무료 플랜
- **메모리**: 1GB RAM
- **파일 크기**: 개당 200MB 제한 (Streamlit 기본값)
- **동시 업로드**: 여러 파일 가능
- **저장**: 세션 메모리에만 저장 (영구 저장 안됨)

### 큰 파일 처리 방법
1GB 이상의 CSV 파일:
- **청크 처리**: `pandas.read_csv(chunksize=10000)`
- **샘플링**: 처음 N개 행만 로드
- **유료 플랜**: Pro 플랜 ($20/month) - 8GB RAM

---

## 🌐 배포 후 사용법

### 사용자 관점
1. 배포된 URL 접속 (예: `https://ai-analyst.streamlit.app`)
2. 사이드바에서 CSV 파일 업로드
3. 질문 입력 → AI 분석 결과 확인

### 데이터 보안
- ✅ 업로드된 파일은 **서버 메모리에만 임시 저장**
- ✅ 세션 종료 시 **자동 삭제**
- ✅ 다른 사용자와 **공유되지 않음**
- ⚠️ 민감한 데이터는 **로컬에서만 사용** 권장

---

## 🐛 배포 후 디버깅

### 로그 확인
**Streamlit Cloud**:
- Dashboard → App → "Manage app" → "Logs" 탭

### 일반적인 오류

#### 1. "GOOGLE_API_KEY not found"
**원인**: Secrets에 API 키가 없음
**해결**: Streamlit Cloud → Settings → Secrets에 추가

#### 2. "Module not found"
**원인**: `requirements.txt` 누락
**해결**: 필요한 패키지 추가 후 재배포

#### 3. "Memory limit exceeded"
**원인**: 큰 파일 업로드
**해결**: 파일 크기 제한 또는 청크 처리

---

## 📊 비용 예상

### 무료 옵션
- **Streamlit Cloud** (Community): 무료
- **Hugging Face Spaces**: 무료
- **Google Gemini API**: 무료 할당량 (월 60회 요청)

### 유료 옵션
- **Streamlit Cloud Pro**: $20/월
- **Google Gemini API** (초과 시):
  - Gemini 2.5 Pro: $3.50 / 1M tokens (입력)
  - 대략 월 100회 분석 ≈ $5~10

**예상 총 비용** (월):
- 소규모 사용: **$0** (무료 플랜)
- 중규모 사용: **$20~30** (Pro 플랜 + API)

---

## ✅ 최종 체크리스트

배포 전:
- [ ] `.gitignore` 파일 확인
- [ ] `.env` 파일 로컬에만 존재
- [ ] `requirements.txt` 최신 버전
- [ ] 로컬 테스트 완료
- [ ] API 키 노출 여부 확인

배포 후:
- [ ] 배포된 URL 접속 확인
- [ ] 파일 업로드 테스트
- [ ] 질문/답변 테스트
- [ ] 다중 파일 조인 테스트
- [ ] 에러 로그 확인

---

## 🎉 결론

**질문에 대한 답변**:

1. **API Key 문제 생기나?**
   - ✅ **해결됨**: `.env` + `.gitignore`로 안전하게 보호
   - ✅ Streamlit Cloud Secrets로 안전하게 관리

2. **온라인에서 CSV 업로드 가능한가?**
   - ✅ **100% 가능**: Streamlit의 기본 기능
   - ✅ 로컬과 동일하게 작동
   - ✅ 사용자별 세션 분리

**추천 배포 방법**:
- 🥇 **Streamlit Community Cloud** (무료, 쉬움)
- 🥈 Hugging Face Spaces (무료, 비공개 가능)
- 🥉 자체 서버 (완전한 제어)

**지금 바로 배포 가능합니다!** 🚀
