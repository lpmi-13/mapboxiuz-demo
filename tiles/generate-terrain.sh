#!/usr/bin/env bash
# Generate RGB-encoded terrain tiles (PMTiles) from SRTM 1-arc-second data.
# Requires: gdal, rio-cogeo (pip install rio-cogeo), and pmtiles CLI.
set -euo pipefail

OUTDIR="$(dirname "$0")/output"
mkdir -p "$OUTDIR"

# UK SRTM tiles bounding box (approx): lon -8.5..2, lat 49..61
# Download via USGS EarthExplorer or OpenTopography. Place .hgt files in OUTDIR/srtm/
SRTM_DIR="$OUTDIR/srtm"
MERGED_TIF="$OUTDIR/uk-elevation.tif"
RGB_TIF="$OUTDIR/uk-elevation-rgb.tif"
PMTILES="$OUTDIR/uk-terrain.pmtiles"

if [[ ! -d "$SRTM_DIR" ]]; then
  echo "ERROR: Place SRTM .hgt files in $SRTM_DIR before running this script."
  exit 1
fi

echo "Merging SRTM tiles…"
gdal_merge.py -o "$MERGED_TIF" "$SRTM_DIR"/*.hgt

echo "Encoding elevation as RGB (Mapbox terrain-rgb)…"
# Each channel encodes 8 bits of the elevation value in 0.1 m resolution
gdal_translate -of GTiff -ot Byte \
  -scale -500 9000 0 255 \
  "$MERGED_TIF" "$RGB_TIF"

echo "Converting to PMTiles…"
# pmtiles CLI: https://github.com/protomaps/go-pmtiles
pmtiles convert "$RGB_TIF" "$PMTILES" \
  --maxzoom=12 \
  --bounds=-8.5,49,2,61

echo "Done: $PMTILES"
