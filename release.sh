#!/bin/bash
# Claudy 릴리즈 스크립트
# 사용: ./release.sh <버전>   예) ./release.sh 1.0.1
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${1:?사용법: ./release.sh <버전>  예) ./release.sh 1.0.1}"
APP_BUNDLE="$SCRIPT_DIR/Claudy.app"
ZIP_NAME="Claudy-${VERSION}.zip"
ZIP_PATH="$SCRIPT_DIR/$ZIP_NAME"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Claudy v$VERSION 릴리즈"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. VERSION 파일 업데이트 & 빌드
echo ""
echo "▶ 버전 설정: $VERSION"
echo "$VERSION" > "$SCRIPT_DIR/VERSION"

echo ""
echo "▶ 앱 빌드 중..."
"$SCRIPT_DIR/build_app.sh"

# ── 2. ZIP 생성
echo ""
echo "▶ ZIP 패키징 중..."
rm -f "$ZIP_PATH"
cd "$SCRIPT_DIR"
zip -r "$ZIP_NAME" "Claudy.app" > /dev/null
echo "✓ $ZIP_NAME 생성됨"

# ── 3. SHA256
SHA256=$(shasum -a 256 "$ZIP_PATH" | awk '{print $1}')
echo "✓ SHA256: $SHA256"

# ── 4. git 커밋 + 태그
echo ""
echo "▶ git 커밋 & 태그..."
cd "$SCRIPT_DIR"
git add VERSION
git commit -m "chore: release v$VERSION" || echo "  (변경 없음, 태그만 추가)"
git tag -f "v$VERSION"
git push origin main --tags
echo "✓ v$VERSION 태그 푸시됨"

# ── 5. GitHub Release 생성
echo ""
echo "▶ GitHub Release 생성 중..."
gh release create "v$VERSION" \
    "$ZIP_PATH#Claudy.zip" \
    --title "Claudy v$VERSION" \
    --notes "## 설치 방법

1. **Claudy.zip** 다운로드 후 압축 해제
2. **Claudy.app** 을 Applications 폴더로 드래그
3. 처음 실행 시 Gatekeeper 경고가 나오면:
   - **시스템 설정 → 개인정보 보호 및 보안 → '확인 없이 열기'** 클릭
   - 또는 터미널에서: \`xattr -dr com.apple.quarantine /Applications/Claudy.app\`

## Claude Code 훅 설정

\`\`\`bash
claude hooks add
\`\`\`
README를 참고하세요."

RELEASE_URL="https://github.com/EloyYang/claudy/releases/tag/v$VERSION"
echo "✓ 릴리즈 완료: $RELEASE_URL"

# ── 6. Homebrew tap 업데이트 (tap repo가 있을 때만)
TAP_DIR="$HOME/homebrew-claudy"
if [ -d "$TAP_DIR" ]; then
    echo ""
    echo "▶ Homebrew tap 업데이트 중..."
    cat > "$TAP_DIR/Casks/claudy.rb" << RUBY
cask "claudy" do
  version "$VERSION"
  sha256 "$SHA256"

  url "https://github.com/EloyYang/claudy/releases/download/v#{version}/Claudy.zip"
  name "Claudy"
  desc "Claude Code 메뉴바 컴패니언 앱"
  homepage "https://github.com/EloyYang/claudy"

  app "Claudy.app"

  zap trash: [
    "~/Library/Preferences/com.claudy.companion.plist",
    "/tmp/claude-companion-events.jsonl",
  ]

  caveats <<~EOS
    Claudy는 Apple 공증 없이 배포됩니다.
    처음 실행 시 Gatekeeper 경고가 뜨면:
      시스템 설정 → 개인정보 보호 및 보안 → '확인 없이 열기'
    또는: xattr -dr com.apple.quarantine /Applications/Claudy.app
  EOS
end
RUBY
    cd "$TAP_DIR"
    git add Casks/claudy.rb
    git commit -m "claudy $VERSION"
    git push
    echo "✓ Homebrew tap 업데이트됨"
else
    echo ""
    echo "ℹ Homebrew tap 미설정 (선택사항)"
    echo "  tap을 만들려면: ./setup_homebrew_tap.sh"
fi

# ── 7. 임시 ZIP 정리
rm -f "$ZIP_PATH"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Claudy v$VERSION 릴리즈 완료!"
echo "  $RELEASE_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
