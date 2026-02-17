#!/usr/bin/env bash
# Substitute __R2_BASE_URL__ in style-template.json with the actual R2 URL.
#
# Usage:
#   R2_BASE_URL=https://pub-xxxx.r2.dev ./tiles/build-style.sh
#
# Produces tiles/output/style.json ready to upload to R2.
set -euo pipefail

R2_BASE_URL="${R2_BASE_URL:?Set R2_BASE_URL to your R2 public bucket URL (no trailing slash)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$SCRIPT_DIR/style-template.json"
OUTDIR="$SCRIPT_DIR/output"
OUT="$OUTDIR/style.json"

mkdir -p "$OUTDIR"
sed "s|__R2_BASE_URL__|${R2_BASE_URL}|g" "$TEMPLATE" > "$OUT"
echo "Style written to $OUT"
echo "Upload with:  wrangler r2 object put YOUR_BUCKET/styles/osm-bright.json --file=$OUT"
