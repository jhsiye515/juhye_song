#!/bin/bash
# 문서 사이트 갱신: main 이 바뀌었으면 사이트를 다시 만든다.
#   tools/site/refresh.sh <저장소 폴더> <사이트 폴더>
# 5분마다 실행하면 머지 뒤 5분 안에 사이트가 바뀐다.
set -euo pipefail
REPO="${1:?저장소 폴더}"
SITE="${2:?사이트 폴더}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${SITE}.work"
STAMP="${SITE}.commit"

git -C "$REPO" fetch -q origin main
NOW="$(git -C "$REPO" rev-parse --short origin/main)"
if [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$NOW" ] && [ -d "$SITE" ] && [ -z "${FORCE:-}" ]; then
  exit 0
fi

rm -rf "${WORK:?}" && mkdir -p "$WORK/main"
git -C "$REPO" archive origin/main | tar -x -C "$WORK/main"
LOG="$(git -C "$REPO" log -10 --format='%ad%x09%an%x09%s' --date=format:'%m/%d %H:%M' origin/main)"
# main 에 들어 있는 도구로 만든다 (도구를 고친 PR 이 머지되면 바로 쓰인다). 없으면 이 스크립트 옆 도구
BUILD="$WORK/main/tools/site/build.py"
[ -f "$BUILD" ] || BUILD="$HERE/build.py"
python3 "$BUILD" "$WORK/main" "$WORK/site" "$NOW" "$LOG"
rm -rf "${SITE:?}.old"
[ -d "$SITE" ] && mv "$SITE" "${SITE}.old"
mv "$WORK/site" "$SITE"
rm -rf "${SITE:?}.old" "${WORK:?}"
echo "$NOW" > "$STAMP"
echo "$(date '+%m/%d %H:%M') 사이트 갱신: $NOW"
