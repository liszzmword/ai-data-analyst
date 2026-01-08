"""
배포 전 체크리스트 자동 확인
"""
import os
import sys
from pathlib import Path

print("=" * 80)
print("🔍 배포 준비 상태 확인")
print("=" * 80)

checks = []
warnings = []
errors = []

# 1. .gitignore 파일 확인
print("\n1. .gitignore 파일 확인...")
gitignore_path = Path(".gitignore")
if gitignore_path.exists():
    content = gitignore_path.read_text()
    if ".env" in content:
        checks.append("✅ .gitignore에 .env 포함됨")
    else:
        errors.append("❌ .gitignore에 .env가 없음!")

    if "config.py" in content:
        checks.append("✅ .gitignore에 config.py 포함됨")
    else:
        warnings.append("⚠️ .gitignore에 config.py가 없음 (권장)")
else:
    errors.append("❌ .gitignore 파일이 없음!")

# 2. .env 파일 확인
print("2. .env 파일 확인...")
env_path = Path(".env")
if env_path.exists():
    checks.append("✅ .env 파일 존재")

    # API 키 확인
    content = env_path.read_text()
    if "GOOGLE_API_KEY" in content:
        checks.append("✅ .env에 GOOGLE_API_KEY 포함됨")
    else:
        errors.append("❌ .env에 GOOGLE_API_KEY가 없음!")
else:
    warnings.append("⚠️ .env 파일이 없음 (로컬 개발 시 필요)")

# 3. .env.example 파일 확인
print("3. .env.example 파일 확인...")
example_path = Path(".env.example")
if example_path.exists():
    checks.append("✅ .env.example 파일 존재 (다른 개발자를 위한 템플릿)")
else:
    warnings.append("⚠️ .env.example 파일 없음 (있으면 좋음)")

# 4. config.py 확인
print("4. config.py 확인...")
config_path = Path("config.py")
if config_path.exists():
    content = config_path.read_text()

    # API 키가 하드코딩되어 있는지 확인
    if "AIzaSy" in content and 'os.getenv("GOOGLE_API_KEY")' in content:
        warnings.append("⚠️ config.py에 API 키 흔적이 남아있을 수 있음")
    elif 'os.getenv("GOOGLE_API_KEY")' in content:
        checks.append("✅ config.py가 환경 변수 사용")
    else:
        errors.append("❌ config.py가 API 키를 하드코딩하고 있음!")
else:
    errors.append("❌ config.py 파일이 없음!")

# 5. requirements.txt 확인
print("5. requirements.txt 확인...")
req_path = Path("requirements.txt")
if req_path.exists():
    content = req_path.read_text()
    if "python-dotenv" in content:
        checks.append("✅ requirements.txt에 python-dotenv 포함됨")
    else:
        errors.append("❌ requirements.txt에 python-dotenv가 없음!")

    if "streamlit" in content:
        checks.append("✅ requirements.txt에 streamlit 포함됨")
    else:
        errors.append("❌ requirements.txt에 streamlit이 없음!")
else:
    errors.append("❌ requirements.txt 파일이 없음!")

# 6. app.py 확인
print("6. app.py 확인...")
app_path = Path("app.py")
if app_path.exists():
    checks.append("✅ app.py 파일 존재")
else:
    errors.append("❌ app.py 파일이 없음!")

# 7. Git 상태 확인 (선택사항)
print("7. Git 상태 확인...")
if Path(".git").exists():
    checks.append("✅ Git 저장소 초기화됨")

    # git status 확인
    import subprocess
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            errors.append("❌ .env 파일이 Git에 추적되고 있음! (즉시 제거 필요)")
        else:
            checks.append("✅ .env 파일이 Git에서 제외됨")
    except:
        warnings.append("⚠️ Git 명령어 실행 실패 (수동 확인 필요)")
else:
    warnings.append("⚠️ Git 저장소가 없음 (배포 시 필요)")

# 8. API 키 로드 테스트
print("8. API 키 로드 테스트...")
try:
    from config import GOOGLE_API_KEY
    if GOOGLE_API_KEY:
        checks.append("✅ API 키 로드 성공")
    else:
        errors.append("❌ API 키가 None임!")
except Exception as e:
    errors.append(f"❌ config.py 로드 실패: {e}")

# 결과 출력
print("\n" + "=" * 80)
print("📊 검사 결과")
print("=" * 80)

if checks:
    print("\n✅ 통과한 검사:")
    for check in checks:
        print(f"  {check}")

if warnings:
    print("\n⚠️ 경고:")
    for warning in warnings:
        print(f"  {warning}")

if errors:
    print("\n❌ 오류 (배포 전 반드시 수정 필요):")
    for error in errors:
        print(f"  {error}")

# 최종 판정
print("\n" + "=" * 80)
if errors:
    print("❌ 배포 준비 미완료")
    print("   위의 오류를 수정한 후 다시 확인하세요.")
    sys.exit(1)
elif warnings:
    print("⚠️ 배포 가능하지만 권장사항 확인 필요")
    print("   경고 항목을 검토하고 필요시 수정하세요.")
    sys.exit(0)
else:
    print("✅ 배포 준비 완료!")
    print("   안전하게 배포할 수 있습니다.")
    sys.exit(0)
