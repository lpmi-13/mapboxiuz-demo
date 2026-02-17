# Self-Hosted Mapbox Alternative — Project Specification

## Overview

Build a self-hosted mapping platform serving UK-only data, replicating core Mapbox functionality using open-source components. The system displays 3 randomly generated fastest routes on a map, updated every 10 seconds via SSE, rendered in a React + MapLibre GL JS frontend.

## Infrastructure

### Machine A — "Data & Geocoding" (4 vCPU, 8 GB RAM)
- **PostgreSQL 16 + PostGIS 3.4** — backing store for OSM data
- **Nominatim** — geocoding API (forward/reverse), uses its own PG database
- **Nginx** — reverse proxy + TLS termination
- Accessible only from private network (Machine C connects to it)

### Machine B — "Routing" (4 vCPU, 8 GB RAM)
- **Valhalla** — routing engine (driving/walking/cycling, isochrones, map matching, matrix, optimized route)
- **Nginx** — reverse proxy
- Accessible only from private network (Machine C connects to it)

### Machine C — "App Server" (2-4 vCPU, 2-4 GB RAM)
- **Custom backend** (Node.js/Fastify) — route generation timer, SSE streaming, Valhalla client, route optimization
- **React frontend** (static build) — MapLibre GL JS map, SSE client, route visualization
- **Nginx** — TLS termination, static file serving, SSE reverse proxy
- Public-facing entry point

### Cloudflare R2 — "Static Tile & Asset Hosting"
- Pre-rendered UK PMTiles (vector tiles, z0-14, ~8-15 GB)
- RGB-encoded terrain/elevation tiles (UK SRTM, ~2-5 GB)
- Map style JSON (e.g., OSM Bright with source URLs pointing at R2)
- Sprite sheets (map icons)
- Glyph/font PBF files
- Browser fetches tiles directly from R2 — Machine C never proxies tile requests

## Data Sources

- **OSM UK extract**: https://download.geofabrik.de/europe/united-kingdom.html (~2 GB PBF)
- **Elevation**: SRTM 30m or OS Terrain 50 for UK
- **Map styles**: OSM Bright, Positron, or custom (JSON, open licensed)
- **Sprites/Glyphs**: Pre-built packages from OpenMapTiles or MapLibre

## Configuration Management

### Approach: Ansible → Docker Compose

Ansible SSHes into each VM, installs Docker, deploys docker-compose.yml files, and manages data import. VMs are provisioned externally (not managed by Ansible).

### Directory Structure

```
project-root/
├── ansible/
│   ├── inventory.yml
│   ├── group_vars/
│   │   ├── all.yml              # shared vars (domain, R2 URLs, network)
│   │   ├── geocoding.yml        # PG tuning, Nominatim config
│   │   ├── routing.yml          # Valhalla config
│   │   └── app.yml              # backend config, Valhalla URL
│   ├── roles/
│   │   ├── common/              # base packages, firewall, users, SSH hardening, Docker install
│   │   ├── geocoding-stack/     # deploys compose file, triggers OSM import
│   │   ├── routing-stack/       # deploys compose file, triggers tile build
│   │   └── app-stack/           # deploys compose file, builds app image
│   ├── playbooks/
│   │   ├── site.yml             # full deploy (all machines)
│   │   ├── geocoding.yml        # Machine A only
│   │   ├── routing.yml          # Machine B only
│   │   ├── app.yml              # Machine C only
│   │   └── update-osm.yml      # re-import fresh OSM data
│   └── files/
│       ├── geocoding/
│       │   ├── docker-compose.yml
│       │   ├── postgresql.conf
│       │   └── nginx.conf
│       ├── routing/
│       │   ├── docker-compose.yml
│       │   └── nginx.conf
│       └── app/
│           ├── docker-compose.yml
│           └── nginx.conf
├── backend/                     # Custom Node.js backend
│   ├── package.json
│   ├── Dockerfile
│   └── src/
│       ├── index.js             # Fastify server entry point
│       ├── routes/
│       │   ├── sse.js           # SSE endpoint: /api/routes/stream
│       │   └── optimize.js      # Route optimization: POST /api/optimize-route
│       ├── services/
│       │   ├── valhalla.js      # Valhalla HTTP client (route, matrix, isochrone)
│       │   ├── routeGenerator.js # Random UK coordinate pair generation + route fetching
│       │   └── optimizer.js     # TSP brute-force solver for ≤12 stops
│       └── utils/
│           └── ukCoordinates.js # List of ~100 UK city/town coordinates for random sampling
├── frontend/                    # React + MapLibre GL JS
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx              # Main app with MapLibre map
│       ├── hooks/
│       │   └── useRouteStream.js # SSE client hook (EventSource)
│       ├── components/
│       │   ├── Map.jsx          # MapLibre GL JS map initialization
│       │   ├── RouteLayer.jsx   # GeoJSON route rendering (3 colored lines)
│       │   └── StopPicker.jsx   # UI for dropping pins + triggering optimize-route
│       └── lib/
│           └── mapStyle.js      # Style URL config pointing at R2
└── tiles/                       # Tile generation scripts (run once)
    ├── generate-pmtiles.sh      # OSM → vector tiles via Planetiler or tilemaker → PMTiles
    ├── generate-terrain.sh      # SRTM → RGB terrain tiles → PMTiles
    └── upload-r2.sh             # Upload PMTiles + styles + sprites + glyphs to R2
```

## Docker Compose — Machine A (Geocoding)

```yaml
services:
  postgres:
    image: postgis/postgis:16-3.4
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./postgresql.conf:/etc/postgresql/postgresql.conf
    shm_size: 1g
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    restart: unless-stopped

  nominatim:
    image: mediagis/nominatim:4.4
    volumes:
      - nominatim_data:/nominatim/data
      - ./osm-data:/data
    environment:
      - PBF_PATH=/data/united-kingdom-latest.osm.pbf
      - NOMINATIM_DATABASE_DSN=pgsql:host=postgres;dbname=nominatim
    depends_on:
      - postgres
    ports:
      - "127.0.0.1:8080:8080"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - certs:/etc/letsencrypt
    ports:
      - "443:443"
      - "80:80"
    restart: unless-stopped

volumes:
  pg_data:
  nominatim_data:
  certs:
```

### PostgreSQL Tuning (8 GB machine, shared with Nominatim)

```
shared_buffers = 2GB
effective_cache_size = 5GB
maintenance_work_mem = 1GB
work_mem = 64MB
wal_buffers = 64MB
checkpoint_completion_target = 0.9
random_page_cost = 1.1
```

After initial import, drop maintenance_work_mem to 256MB.

## Docker Compose — Machine B (Routing)

```yaml
services:
  valhalla:
    image: ghcr.io/gis-ops/valhalla:latest
    volumes:
      - valhalla_tiles:/custom_files
      - ./osm-data:/data
    environment:
      - tile_urls=file:///data/united-kingdom-latest.osm.pbf
    ports:
      - "127.0.0.1:8002:8002"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "443:443"
      - "80:80"
    restart: unless-stopped

volumes:
  valhalla_tiles:
```

## Docker Compose — Machine C (App Server)

```yaml
services:
  app:
    build: ./app
    environment:
      - VALHALLA_URL=http://<machine-b-private-ip>:8002
      - NOMINATIM_URL=http://<machine-a-private-ip>:8080
      - PORT=3000
    ports:
      - "127.0.0.1:3000:3000"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ../frontend/dist:/usr/share/nginx/html
      - certs:/etc/letsencrypt
    ports:
      - "443:443"
      - "80:80"
    restart: unless-stopped

volumes:
  certs:
```

### Nginx SSE proxy config (Machine C)

```nginx
location /api/routes/stream {
    proxy_pass http://app:3000;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_set_header Connection '';
    chunked_transfer_encoding off;
}

location /api/ {
    proxy_pass http://app:3000;
}

location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}
```

## Backend API Endpoints

### GET /api/routes/stream (SSE)
- Content-Type: text/event-stream
- Every ~10 seconds, emits a message with 3 randomly generated UK routes
- Each route: origin name, destination name, distance, duration, GeoJSON geometry
- Random points selected from a curated list of ~100 UK cities/towns
- Each route fetched from Valhalla POST /route

### POST /api/optimize-route
- Request body: `{ stops: [{lat, lon, name}], fixed_start: bool, round_trip: bool }`
- Step 1: Call Valhalla /sources_to_targets for N×N distance matrix
- Step 2: Brute-force all permutations (≤12 stops) to find shortest total distance
- Step 3: Call Valhalla /route with stops in optimal order
- Response: `{ ordered_stops: [...], route: { geometry: GeoJSON, distance_km, duration_min, legs: [...] } }`
- For >12 stops: use nearest-neighbor + 2-opt heuristic instead of brute force

### GET /api/isochrone?lat=X&lon=Y&time=N&costing=auto
- Proxies to Valhalla /isochrone endpoint
- Returns GeoJSON polygon of reachable area

## Frontend Features

- MapLibre GL JS map centered on UK, zoom 6
- PMTiles source loaded directly from R2 (pmtiles:// protocol)
- SSE connection to /api/routes/stream
- On each SSE message: update 3 GeoJSON line layers with different colors
- Stop picker: click map to drop pins, button to call /api/optimize-route, render result
- Geocoding search bar calling Nominatim on Machine A (optional, nice to have)

## Tile Generation Pipeline (run once, before deployment)

1. Download UK OSM PBF from Geofabrik
2. Generate vector tiles using Planetiler or tilemaker → output as PMTiles
3. Generate terrain tiles from SRTM → RGB encoding → PMTiles
4. Obtain map style JSON (OSM Bright), edit source URLs to point at R2
5. Obtain sprite sheets and glyph PBFs
6. Upload all to Cloudflare R2

## Valhalla API Reference (endpoints used)

- `POST /route` — point-to-point or multi-stop routing
- `POST /sources_to_targets` — N×N travel time/distance matrix
- `POST /optimized_route` — built-in stop order optimization (nearest-neighbor)
- `POST /isochrone` — travel time contour polygons
- `POST /trace_route` — GPS trace map matching
- `POST /locate` — snap coordinates to nearest road

## Key Decisions

- SSE over WebSockets (unidirectional push, simpler infra, auto-reconnect)
- PMTiles on R2 over running a tile server (zero compute for tile serving)
- Valhalla over OSRM (memory-maps tiles, degrades gracefully with less RAM, more features)
- Nominatim over Pelias (simpler, lower resource needs, sufficient for UK-scale)
- Docker Compose over bare-metal installs (reproducible, community images handle import complexity)
- Ansible for configuration management (VMs provisioned externally)
- Brute-force TSP for ≤12 stops, nearest-neighbor + 2-opt for more

## Estimated Costs

- Machine A + B: ~€9-15/month total (Hetzner CX22 or similar, 4 vCPU / 8 GB each)
- Machine C: ~€4-5/month (2 vCPU / 2-4 GB)
- Cloudflare R2: ~$0-5/month (free tier covers 10 GB storage, free egress)
- **Total: ~$15-25/month**
