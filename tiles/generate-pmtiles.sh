#!/usr/bin/env bash
# Generate UK vector tiles (PMTiles) from the Geofabrik OSM extract.
# Requires: java (for Planetiler) and curl.
set -euo pipefail

OUTDIR="$(dirname "$0")/output"
PBF="$OUTDIR/united-kingdom-latest.osm.pbf"
PMTILES="$OUTDIR/uk.pmtiles"
PLANETILER_JAR="$OUTDIR/planetiler.jar"
PLANETILER_VERSION="0.8.3"

mkdir -p "$OUTDIR"

# Download OSM extract if not present
if [[ ! -f "$PBF" ]]; then
  echo "Downloading UK OSM extract (~2 GB)…"
  curl -L -o "$PBF" \
    "https://download.geofabrik.de/europe/united-kingdom-latest.osm.pbf"
fi

# Download Planetiler if not present
if [[ ! -f "$PLANETILER_JAR" ]]; then
  echo "Downloading Planetiler ${PLANETILER_VERSION}…"
  curl -L -o "$PLANETILER_JAR" \
    "https://github.com/onthegomap/planetiler/releases/download/v${PLANETILER_VERSION}/planetiler.jar"
fi

echo "Generating PMTiles…"
java -Xmx6g -jar "$PLANETILER_JAR" \
  --osm-path="$PBF" \
  --output="$PMTILES" \
  --bounds=uk \
  --minzoom=0 \
  --maxzoom=14

echo "Done: $PMTILES"
