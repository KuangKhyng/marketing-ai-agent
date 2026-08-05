#!/usr/bin/env bash
# Chụp ảnh giao diện bằng Chrome headless để review bằng mắt.
#
#   bash scripts/shot.sh                      # chụp / và /knowledge
#   bash scripts/shot.sh https://example.com  # chụp một URL bất kỳ
#
# Ảnh lưu vào scripts/../.shots/ — thư mục này nên nằm trong .gitignore.
set -u

CHROME=""
for p in \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Microsoft/Edge/Application/msedge.exe"; do
  [ -f "$p" ] && CHROME="$p" && break
done
[ -z "$CHROME" ] && { echo "Không tìm thấy Chrome hoặc Edge."; exit 1; }

OUT="$(cd "$(dirname "$0")/.." && pwd)/.shots"
mkdir -p "$OUT"

shot () {  # $1=tên  $2=url  $3=kích thước cửa sổ
  local size="${3:-1440,1050}"
  timeout 100 "$CHROME" \
    --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --force-device-scale-factor=1 --virtual-time-budget=9000 \
    --window-size="$size" \
    --screenshot="$(cygpath -w "$OUT/$1.png" 2>/dev/null || echo "$OUT/$1.png")" \
    "$2" 2>&1 | grep -i "written" || echo "  lỗi khi chụp $1"
}

if [ $# -gt 0 ]; then
  shot "custom" "$1" "${2:-1440,1600}"
else
  BASE="${BASE:-http://127.0.0.1:8000}"
  if ! curl -sf -o /dev/null "$BASE/api/health"; then
    echo "Server chưa chạy ở $BASE"
    echo "  ENV=dev .venv/Scripts/python.exe -m uvicorn api.main:app --port 8000"
    exit 1
  fi
  shot "input"     "$BASE/"          "1440,1050"
  shot "knowledge" "$BASE/knowledge" "1440,1050"
fi

echo "Ảnh ở: $OUT"
