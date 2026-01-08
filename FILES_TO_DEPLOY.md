# 📦 배포 시 필요한 파일 목록

## ✅ 반드시 필요한 파일 (11개)

### 핵심 코드 (4개)
- `app.py` - Streamlit 메인 앱
- `smart_analyst.py` - AI 분석 엔진
- `upload_handler.py` - 파일 업로드 처리
- `config.py` - 설정 파일

### 설정 파일 (3개)
- `requirements.txt` - Python 패키지 목록
- `.gitignore` - Git 제외 파일 목록
- `.env.example` - API 키 템플릿 (다른 사람을 위한)

### 문서 (4개)
- `README.md` - 프로젝트 설명
- `DEPLOYMENT_GUIDE.md` - 배포 가이드
- `SUMMARY_V2.1.md` - 기능 설명
- `LICENSE` - 라이센스 (선택사항)

---

## ❌ 업로드하면 안 되는 파일

### 보안 관련
- ❌ `.env` - API 키 포함 (절대 업로드 금지!)
- ❌ `config.py` (만약 하드코딩된 API 키가 있다면)

### 데이터 파일 (선택)
- ❌ `sales data.csv` - 예시 데이터
- ❌ `거래처 데이터.csv` - 예시 데이터
- ❌ `영업일지.csv` - 예시 데이터
- ❌ `데이터 db.csv` - 코드북

**이유**: 사용자가 직접 업로드하는 앱이므로 예시 데이터 불필요

### 테스트/임시 파일
- ❌ `test_*.py` - 테스트 스크립트
- ❌ `debug_*.py` - 디버그 스크립트
- ❌ `diagnose_*.py` - 진단 스크립트
- ❌ `check_deployment.py` - 배포 체크 스크립트
- ❌ `QUICK_DEPLOY.sh` - 로컬 배포 스크립트
- ❌ `__pycache__/` - Python 캐시
- ❌ `.DS_Store` - macOS 시스템 파일
- ❌ `*.pyc` - Python 컴파일 파일

### 구버전 파일 (old_files/)
- ❌ `old_files/` 폴더 전체 - 이전 버전 백업

### Vector Store (사용 안 함)
- ❌ `vector_store/` - 현재 사용 안 함
- ❌ `.cache/` - 캐시 폴더

---

## 📊 파일 크기 최적화

### 현재 폴더 크기 확인
```bash
cd /Users/inseoplee/Desktop/rag_Test
du -sh *
```

### 필수 파일만 선택하면
- **전체 폴더**: ~100MB (CSV 포함)
- **필수 파일만**: ~1MB

---

## 🎯 .gitignore 최종 버전

모든 불필요한 파일 자동 제외:

```gitignore
# API Keys and Secrets
.env
config.py

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual Environment
venv/
env/
ENV/

# Streamlit
.streamlit/secrets.toml

# Data Files (예시 데이터 제외)
*.csv
*.xlsx
*.xls
!.env.example

# Test Files
test_*.py
debug_*.py
diagnose_*.py
check_deployment.py
QUICK_DEPLOY.sh

# IDE
.vscode/
.idea/
*.swp
*.swo

# macOS
.DS_Store

# Logs
*.log

# Temporary files
tmp/
temp/

# Old files
old_files/

# Vector Store
vector_store/
.cache/

# Deployment checklist (로컬용)
DEPLOYMENT_CHECKLIST.md
FILES_TO_DEPLOY.md
BEFORE_AFTER_TEST.md
FIX_SUMMARY.md
```

---

## ✅ 최종 업로드 파일 목록

```
rag_Test/
├── app.py                      ✅ 필수
├── smart_analyst.py            ✅ 필수
├── upload_handler.py           ✅ 필수
├── config.py                   ✅ 필수 (API 키 하드코딩 제거됨)
├── requirements.txt            ✅ 필수
├── .gitignore                  ✅ 필수
├── .env.example                ✅ 권장
├── README.md                   ✅ 권장
├── DEPLOYMENT_GUIDE.md         ✅ 권장
└── SUMMARY_V2.1.md             ✅ 권장
```

**총 10개 파일** (전체 크기: ~1MB)

---

## 🚀 배포 시 파일 확인 방법

### Git으로 자동 필터링
`.gitignore`가 자동으로 불필요한 파일 제외:

```bash
# 업로드될 파일 목록 확인
git add .
git status

# CSV 파일이 없는지 확인
git status | grep csv
# 아무것도 출력되지 않으면 ✅ 성공!
```

### 수동 확인
```bash
# 필수 파일만 보기
ls -lh app.py smart_analyst.py upload_handler.py config.py requirements.txt
```

---

## 💾 데이터 파일은 어떻게?

**온라인 배포 후**:
1. 사용자가 브라우저에서 직접 CSV 업로드
2. 서버 메모리에만 임시 저장
3. 분석 수행
4. 세션 종료 시 자동 삭제

**예시 데이터가 필요하다면**:
- GitHub README에 다운로드 링크 추가
- 또는 Google Drive/Dropbox 링크 제공
- 코드에는 포함하지 않음

---

## 🔒 보안 체크

배포 전 확인:

```bash
# 1. .env 파일이 제외되었는지
git check-ignore .env
# 출력: .env ✅

# 2. API 키가 코드에 없는지
grep -r "AIzaSy" app.py smart_analyst.py upload_handler.py
# 아무것도 출력되지 않으면 ✅

# 3. CSV 파일이 제외되었는지
git ls-files | grep csv
# 아무것도 출력되지 않으면 ✅
```

---

## 📌 요약

**업로드 필요**: 10개 파일 (~1MB)
**업로드 불필요**: CSV, 테스트 파일, 캐시 등

**자동 필터링**: `.gitignore`가 모두 처리 ✅
