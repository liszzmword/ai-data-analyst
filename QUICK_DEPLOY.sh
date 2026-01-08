#!/bin/bash
# AI 데이터 분석 챗봇 - 빠른 배포 스크립트

echo "=================================="
echo "🚀 AI 데이터 분석 챗봇 배포 준비"
echo "=================================="
echo ""

# 1. Git 초기화
echo "1️⃣ Git 저장소 초기화..."
git init
echo "✅ Git 초기화 완료"
echo ""

# 2. 사용자 정보 확인
echo "2️⃣ Git 사용자 정보 설정..."
echo "GitHub 사용자 이름을 입력하세요 (예: Hong Gildong):"
read git_name
echo "GitHub 이메일을 입력하세요 (예: hong@example.com):"
read git_email

git config user.name "$git_name"
git config user.email "$git_email"
echo "✅ 사용자 정보 설정 완료"
echo ""

# 3. .env 파일 확인
echo "3️⃣ 보안 파일 확인..."
if git check-ignore .env > /dev/null 2>&1; then
    echo "✅ .env 파일이 Git에서 제외됨 (안전)"
else
    echo "⚠️ 경고: .env 파일이 Git에 포함될 수 있습니다!"
    echo ".gitignore 파일을 확인하세요."
fi
echo ""

# 4. 파일 추가 및 커밋
echo "4️⃣ 파일 추가 및 커밋..."
git add .
git commit -m "Initial commit - AI Data Analyst v2.1"
echo "✅ 커밋 완료"
echo ""

# 5. GitHub 저장소 URL 입력
echo "5️⃣ GitHub 저장소 연결..."
echo "GitHub 저장소 URL을 입력하세요:"
echo "(예: https://github.com/your-username/ai-data-analyst.git)"
read repo_url

git remote add origin "$repo_url"
git branch -M main
echo "✅ 저장소 연결 완료"
echo ""

# 6. GitHub에 업로드
echo "6️⃣ GitHub에 코드 업로드..."
echo "GitHub에 로그인이 필요합니다."
echo "Username: GitHub 아이디"
echo "Password: Personal Access Token (비밀번호 아님!)"
echo ""
echo "Token이 없다면 다음 페이지에서 생성:"
echo "https://github.com/settings/tokens"
echo ""

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✅ GitHub 업로드 완료!"
    echo "=================================="
    echo ""
    echo "다음 단계:"
    echo "1. https://share.streamlit.io 접속"
    echo "2. Sign in with GitHub"
    echo "3. New app 클릭"
    echo "4. 저장소 선택 및 app.py 지정"
    echo "5. Secrets에 API 키 추가:"
    echo '   GOOGLE_API_KEY = "AIzaSyDerwkzYbYNJwuAQivHACGrVS9_2kuoV7E"'
    echo "6. Deploy 클릭!"
    echo ""
else
    echo ""
    echo "=================================="
    echo "❌ 업로드 실패"
    echo "=================================="
    echo ""
    echo "문제 해결:"
    echo "1. Personal Access Token이 올바른지 확인"
    echo "2. 저장소 URL이 정확한지 확인"
    echo "3. 저장소가 생성되었는지 확인"
    echo ""
fi
