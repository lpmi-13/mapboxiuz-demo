#!/usr/bin/env bash
# Upload PMTiles, map style, sprites, and glyphs to Cloudflare R2.
# Requires: wrangler (npm install -g wrangler) authenticated to your CF account,
#           or rclone configured with an R2 remote.
set -euo pipefail

BUCKET="${R2_BUCKET:-mapboxiuz-tiles}"
OUTDIR="$(dirname "$0")/output"

upload_wrangler() {
  local src="$1" dest="$2"
  wrangler r2 object put "${BUCKET}/${dest}" --file="$src"
}

echo "Uploading uk.pmtiles…"
upload_wrangler "$OUTDIR/uk.pmtiles" "uk.pmtiles"

echo "Uploading uk-terrain.pmtiles…"
upload_wrangler "$OUTDIR/uk-terrain.pmtiles" "uk-terrain.pmtiles"

if [[ -f "$OUTDIR/style.json" ]]; then
  echo "Uploading style.json…"
  upload_wrangler "$OUTDIR/style.json" "styles/osm-bright.json"
fi

if [[ -d "$OUTDIR/sprites" ]]; then
  echo "Uploading sprites…"
  for f in "$OUTDIR/sprites"/*; do
    upload_wrangler "$f" "sprites/$(basename "$f")"
  done
fi

if [[ -d "$OUTDIR/glyphs" ]]; then
  echo "Uploading glyphs…"
  for f in "$OUTDIR/glyphs"/**/*; do
    [[ -f "$f" ]] || continue
    rel="${f#$OUTDIR/glyphs/}"
    upload_wrangler "$f" "glyphs/${rel}"
  done
fi

echo "All assets uploaded to R2 bucket: $BUCKET"
