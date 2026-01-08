# 🚀 배포 준비 체크리스트

## 필요한 것들

### 1. GitHub 계정
- [ ] GitHub 계정이 있나요? (없으면 [github.com](https://github.com)에서 무료 가입)
- [ ] GitHub에 로그인되어 있나요?

### 2. 로컬 환경
- [ ] Git이 설치되어 있나요? (`git --version` 확인)
  - 없으면: `brew install git` (macOS)
- [ ] 현재 폴더 위치: `/Users/inseoplee/Desktop/rag_Test`

### 3. 코드 준비 (✅ 이미 완료됨!)
- [x] API 키 보안 처리 완료
- [x] .gitignore 설정 완료
- [x] requirements.txt 준비 완료

---

## 📝 단계별 배포 가이드 (복사해서 실행만 하세요)

### Step 1: GitHub 계정 확인

**질문**: GitHub 계정이 있나요?
- **있음** → Step 2로 이동
- **없음** → [github.com](https://github.com) 접속 후 가입 (1분)

---

### Step 2: Git 설치 확인

터미널에서 실행:
```bash
git --version
```

**결과**:
- ✅ `git version 2.x.x` 출력 → Step 3으로 이동
- ❌ 오류 발생 → Git 설치 필요:
  ```bash
  # macOS
  brew install git

  # 또는 Xcode Command Line Tools
  xcode-select --install
  ```

---

### Step 3: Git 초기화 및 커밋 (복사 & 붙여넣기)

터미널에서 다음 명령어를 **한 줄씩** 실행:

```bash
# 1. rag_Test 폴더로 이동
cd /Users/inseoplee/Desktop/rag_Test

# 2. Git 초기화
git init

# 3. 사용자 정보 설정 (처음 한 번만)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 4. .env 파일이 Git에 포함되지 않았는지 확인 (중요!)
git status | grep .env
# 아무것도 출력되지 않으면 ✅ 성공!

# 5. 모든 파일 추가
git add .

# 6. 커밋
git commit -m "Initial commit - AI Data Analyst v2.1"
```

**예상 결과**:
```
[main (root-commit) abc1234] Initial commit - AI Data Analyst v2.1
 XX files changed, XXX insertions(+)
```

---

### Step 4: GitHub에 저장소 생성

1. **브라우저에서** [github.com/new](https://github.com/new) 접속
2. **Repository name**: `ai-data-analyst` (또는 원하는 이름)
3. **Description**: "AI 데이터 분석 챗봇 (Gemini 2.5 Pro)"
4. **Public** 선택 (무료 배포를 위해)
5. **Add a README file** ❌ 체크 해제 (이미 있음)
6. **Add .gitignore** ❌ 체크 해제 (이미 있음)
7. **Create repository** 클릭

**결과**: 저장소 URL이 생성됨
- 예: `https://github.com/your-username/ai-data-analyst`

---

### Step 5: GitHub에 코드 업로드

**중요**: Step 4에서 생성된 저장소 URL을 사용하세요!

터미널에서 실행 (your-username을 본인 GitHub 아이디로 변경):

```bash
# 1. GitHub 저장소 연결
git remote add origin https://github.com/your-username/ai-data-analyst.git

# 2. 브랜치 이름 설정
git branch -M main

# 3. GitHub에 업로드
git push -u origin main
```

**GitHub 로그인 요청 시**:
- Username: GitHub 아이디 입력
- Password: **Personal Access Token** 입력 (비밀번호 아님!)

**Token이 없다면**:
1. [github.com/settings/tokens](https://github.com/settings/tokens) 접속
2. "Generate new token (classic)" 클릭
3. Note: "Streamlit Deploy"
4. Expiration: 90 days
5. **repo** 체크박스 선택
6. "Generate token" 클릭
7. 토큰 복사 (다시 볼 수 없으니 메모장에 저장!)

---

### Step 6: Streamlit Cloud 배포

1. **브라우저에서** [share.streamlit.io](https://share.streamlit.io) 접속
2. **Sign in with GitHub** 클릭
3. **New app** 클릭
4. 다음 정보 입력:
   - **Repository**: `your-username/ai-data-analyst` 선택
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. **Advanced settings** 클릭
6. **Secrets** 탭에서 다음 입력:
   ```toml
   GOOGLE_API_KEY = "AIzaSyDerwkzYbYNJwuAQivHACGrVS9_2kuoV7E"
   ```
7. **Deploy!** 클릭

**배포 시간**: 2~3분

**완료 후**:
- URL 생성: `https://your-app-name.streamlit.app`
- 자동 HTTPS 적용
- 바로 사용 가능!

---

## 🆘 문제 해결

### "git: command not found"
```bash
# macOS
xcode-select --install

# 또는
brew install git
```

### "Permission denied (publickey)"
→ HTTPS URL 사용 (SSH 말고)
```bash
git remote set-url origin https://github.com/your-username/ai-data-analyst.git
```

### ".env 파일이 Git에 포함됨" 오류
```bash
# .env 제거
git rm --cached .env
git commit -m "Remove .env from git"
git push
```

### Streamlit Cloud에서 "Module not found"
→ `requirements.txt` 확인
→ 해당 패키지 추가 후 Git push

---

## 📞 도움 요청

막히는 부분이 있으면:
1. **정확한 에러 메시지** 복사
2. **어느 단계**에서 막혔는지 알려주세요
3. 제가 즉시 해결 방법 알려드리겠습니다!

---

## ✅ 예상 소요 시간

- Git 설치: 2분
- GitHub 저장소 생성: 1분
- 코드 업로드: 2분
- Streamlit Cloud 배포: 3분

**총 8분** (처음 하시는 경우 15분)
