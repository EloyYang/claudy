#!/bin/bash
# Homebrew tap 저장소 초기 설정 (최초 1회만 실행)
set -e

TAP_REPO="EloyYang/homebrew-claudy"
TAP_DIR="$HOME/homebrew-claudy"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Homebrew tap 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# GitHub repo 생성
echo ""
echo "▶ GitHub 저장소 생성 중..."
gh repo create "$TAP_REPO" \
    --public \
    --description "Homebrew tap for Claudy — Claude Code companion app" \
    --clone "$TAP_DIR" 2>/dev/null || {
    echo "  (이미 존재하거나 클론 중...)"
    [ -d "$TAP_DIR" ] || git clone "https://github.com/$TAP_REPO" "$TAP_DIR"
}

# 디렉터리 구조 생성
mkdir -p "$TAP_DIR/Casks"

# README
cat > "$TAP_DIR/README.md" << 'MD'
# homebrew-claudy

Homebrew tap for [Claudy](https://github.com/EloyYang/claudy) — Claude Code 메뉴바 컴패니언 앱

## 설치

```bash
brew tap EloyYang/claudy
brew install --cask claudy
```

> **참고**: Claudy는 Apple 공증 없이 배포됩니다.
> 처음 실행 시 Gatekeeper 경고가 뜨면:
> 시스템 설정 → 개인정보 보호 및 보안 → "확인 없이 열기"
MD

cd "$TAP_DIR"
git add .
git commit -m "chore: init homebrew tap" 2>/dev/null || true
git push

echo "✓ tap 저장소 생성 완료: https://github.com/$TAP_REPO"
echo ""
echo "이제 release.sh 를 실행하면 tap이 자동으로 업데이트됩니다."
echo ""
echo "사용자 설치 명령:"
echo "  brew tap EloyYang/claudy"
echo "  brew install --cask claudy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
