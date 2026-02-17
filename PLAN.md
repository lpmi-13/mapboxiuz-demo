# Implementation Plan

This plan breaks the PROJECT_SPEC.md into ordered, actionable phases. Each phase lists concrete tasks with checkboxes so we can track progress as we go.

---

## Phase 1 — Project Scaffolding & Local Dev Setup

Set up the directory structure, tooling, and a working local dev loop before touching any infrastructure.

- [x] Create the full directory tree (`backend/`, `frontend/`, `ansible/`, `tiles/`)
- [x] **Backend scaffold**: `django-admin startproject`, create a `api` Django app, install `djangorestframework`, `django-cors-headers`, `httpx` (async Valhalla client), `daphne` (ASGI server for SSE support); wire up a health-check view (`GET /healthz`)
- [x] **Frontend scaffold**: `npm create vite@latest` (React template), install MapLibre GL JS and `pmtiles` protocol plugin, create placeholder `App.jsx`
- [x] Add root-level `docker-compose.dev.yml` for local development (backend + Valhalla + Nominatim against a small OSM extract)
- [ ] Confirm `docker compose up` starts everything and backend responds on `localhost:8000`

---

## Phase 2 — Backend Core (Django + Valhalla Client)

Build the backend service layer first because the frontend depends on it.

**Stack**: Python 3.12, Django 5.x, Django REST Framework, `httpx` (async HTTP), `daphne` (ASGI), `django-cors-headers`.

### Directory layout

```
backend/
├── manage.py
├── requirements.txt
├── Dockerfile
├── config/                  # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py              # ASGI entry point for daphne
└── api/                     # Single Django app
    ├── urls.py
    ├── views/
    │   ├── sse.py           # StreamingHttpResponse SSE view
    │   ├── optimize.py      # Route optimization view
    │   └── isochrone.py     # Isochrone proxy view
    ├── services/
    │   ├── valhalla.py      # httpx Valhalla client
    │   ├── route_generator.py
    │   └── optimizer.py     # TSP solver
    └── utils/
        └── uk_coordinates.py
```

### 2a — Valhalla HTTP client (`api/services/valhalla.py`)
- [x] Implement `get_route(locations, costing)` — calls `POST /route`
- [x] Implement `get_matrix(sources, targets, costing)` — calls `POST /sources_to_targets`
- [x] Implement `get_isochrone(lat, lon, time, costing)` — calls `POST /isochrone`
- [x] Use `httpx.AsyncClient` with a shared client instance; add error handling and response normalization (extract GeoJSON geometry, distance, duration)

### 2b — UK coordinate pool (`api/utils/uk_coordinates.py`)
- [x] Curate a list of ~100 UK city/town coordinates (lat/lon + display name)
- [x] Implement `pick_random_pair()` returning two distinct entries

### 2c — Route generator service (`api/services/route_generator.py`)
- [x] Implement `async generate_routes(n=3)` — picks `n` random origin/destination pairs, calls Valhalla for each concurrently (`asyncio.gather`), returns list of route dicts `{ origin, destination, distance_km, duration_min, geometry }`

### 2d — SSE endpoint (`api/views/sse.py`)
- [x] Django view returning `StreamingHttpResponse` with `content_type="text/event-stream"`
- [x] Use an async generator that `await asyncio.sleep(10)`, calls `generate_routes()`, and yields a properly formatted SSE `data:` frame
- [x] Set `X-Accel-Buffering: no` header for Nginx compatibility
- [x] Wire up to `GET /api/routes/stream` in `api/urls.py`

### 2e — Route optimization endpoint (`api/views/optimize.py`)
- [x] DRF `APIView` for `POST /api/optimize-route`
- [x] Accept `{ stops, fixed_start, round_trip }`
- [x] Implement brute-force TSP solver for ≤12 stops in `api/services/optimizer.py` (`itertools.permutations`)
- [x] Implement nearest-neighbor + 2-opt heuristic for >12 stops
- [x] Call Valhalla `/sources_to_targets` for the distance matrix, solve, then call `/route` with the optimal order
- [x] Return `{ ordered_stops, route: { geometry, distance_km, duration_min, legs } }`

### 2f — Isochrone proxy (`api/views/isochrone.py`)
- [x] DRF `APIView` for `GET /api/isochrone`
- [x] Accept query params `lat, lon, time, costing`
- [x] Proxy to Valhalla `/isochrone` and return GeoJSON polygon

### 2g — Django settings & wiring
- [x] `config/settings.py`: configure `INSTALLED_APPS`, `CORS_ALLOWED_ORIGINS`, `REST_FRAMEWORK` defaults, env-var-driven `VALHALLA_URL` / `NOMINATIM_URL`
- [x] `config/asgi.py`: ASGI application for daphne
- [x] `config/urls.py`: include `api/urls.py` under `/api/`

### 2h — Backend Dockerfile
- [x] `python:3.12-slim` base image
- [x] Install requirements, collect static files
- [x] Entrypoint: `daphne -b 0.0.0.0 -p 8000 config.asgi:application`
- [x] Expose port 8000

### 2i — Tests (`api/tests/`)
- [x] `test_uk_coordinates.py` — pool size, bounding box, no duplicates, `pick_random_pair` randomness
- [x] `test_optimizer.py` — brute-force exactness, nearest-neighbour greedy, 2-opt improvement, `solve_tsp` dispatcher
- [x] `test_valhalla.py` — `_decode_polyline`, mocked `get_route` / `get_matrix` / `get_isochrone`
- [x] `test_route_generator.py` — concurrent fetch, graceful error dropping, `n` parameter
- [x] `test_health.py` — 200, JSON body, content-type
- [x] `test_sse_view.py` — SSE frame format, JSON payload, error frame, response headers
- [x] `test_optimize_view.py` — happy path, validation errors, 405 for GET
- [x] `test_isochrone_view.py` — happy path, missing params, type errors, 502 propagation, 405 for POST

---

## Phase 3 — Frontend (React + MapLibre GL JS)

### 3a — Map component (`components/Map.jsx`)
- [x] Initialize MapLibre GL JS map, centered on UK (lat 54.5, lon -2, zoom 6)
- [x] Load map style JSON (initially use a public demo style; will switch to R2-hosted style later)
- [x] Register PMTiles protocol for future R2-hosted tiles

### 3b — SSE client hook (`hooks/useRouteStream.js`)
- [x] Create a React hook wrapping `EventSource` on `/api/routes/stream`
- [x] Parse incoming JSON, expose `routes` state (array of 3 route objects)
- [x] Handle reconnection on error

### 3c — Route layer (`components/RouteLayer.jsx`)
- [x] Render 3 GeoJSON line layers on the map with distinct colors (e.g. `#e6194b`, `#3cb44b`, `#4363d8`)
- [x] Update sources when `routes` state changes
- [x] Show origin/destination markers with name labels

### 3d — Stop picker (`components/StopPicker.jsx`)
- [x] Click-to-drop-pin functionality on the map
- [x] List of current stops in a sidebar/panel
- [x] "Optimize Route" button → `POST /api/optimize-route`
- [x] Render the optimized route and ordered stops on the map

### 3e — Map style config (`lib/mapStyle.js`)
- [x] Centralize the style URL / object so it's easy to swap between dev (public tiles) and prod (R2)

### 3f — Frontend build
- [ ] Confirm `vite build` produces a working `dist/` folder
- [ ] Verify the production build works with the backend behind Nginx (path proxying)

---

## Phase 4 — Tile Generation Pipeline

These scripts run once (or on OSM update) to produce the static assets hosted on R2.

- [x] `tiles/generate-pmtiles.sh` — Download UK PBF from Geofabrik → run Planetiler or tilemaker → output `uk.pmtiles`
- [x] `tiles/generate-terrain.sh` — Download SRTM tiles for UK → RGB-encode → package as `uk-terrain.pmtiles`
- [x] `tiles/upload-r2.sh` — Upload `uk.pmtiles`, `uk-terrain.pmtiles`, style JSON, sprites, and glyphs to Cloudflare R2 using `wrangler` or `rclone`
- [x] `tiles/style-template.json` — MapLibre style with vector + terrain-rgb sources, road/water/label layers; `tiles/build-style.sh` stamps in the R2 base URL at deploy time
- [ ] Obtain or generate sprite sheets and glyph PBF files (download from OpenMapTiles project)

---

## Phase 5 — Ansible & Infrastructure

### 5a — Ansible skeleton
- [x] Create `ansible/inventory.yml` with host groups `geocoding`, `routing`, `app`
- [x] Create `group_vars/all.yml` (domain, R2 URLs, private network IPs)
- [x] Create group var files: `geocoding.yml`, `routing.yml`, `app.yml`

### 5b — Common role (`roles/common/`)
- [x] Install base packages, configure firewall (UFW)
- [x] Create deploy user (SSH hardening handled externally — VMs are ephemeral snapshots)
- [x] Install Docker + Docker Compose plugin

### 5c — Geocoding stack role (`roles/geocoding-stack/`)
- [x] Template and deploy `docker-compose.yml`, `postgresql.conf`, `nginx.conf` for Machine A
- [x] Download UK OSM PBF if not present
- [x] Trigger Nominatim initial import
- [x] Post-import: adjust `maintenance_work_mem` down to 256 MB

### 5d — Routing stack role (`roles/routing-stack/`)
- [x] Template and deploy `docker-compose.yml`, `nginx.conf` for Machine B
- [x] Download UK OSM PBF if not present
- [x] Trigger Valhalla tile build

### 5e — App stack role (`roles/app-stack/`)
- [x] Template and deploy `docker-compose.yml`, `nginx.conf` for Machine C
- [x] Build and deploy backend Docker image
- [x] Deploy frontend `dist/` for Nginx to serve (syncs source, runs `npm run build`, copies dist)
- [x] Configure Nginx for SSE proxying, API reverse proxy, and SPA fallback

### 5f — Playbooks
- [x] `site.yml` — orchestrate full deploy across all machines
- [x] `geocoding.yml`, `routing.yml`, `app.yml` — per-machine playbooks
- [x] `update-osm.yml` — re-import fresh OSM data on Machine A & rebuild Valhalla tiles on Machine B

### 5g — Nginx config files (`ansible/files/`)
- [x] Machine A: reverse proxy to Nominatim on 8080, TLS termination
- [x] Machine B: reverse proxy to Valhalla on 8002
- [x] Machine C: SSE proxy config, API proxy, static file serving, TLS termination

---

## Phase 6 — Integration & Testing

- [ ] End-to-end test: local `docker compose up` → frontend connects SSE → routes appear on map
- [ ] Test optimize-route flow: drop pins → call API → optimal route renders
- [ ] Test isochrone endpoint
- [ ] Verify Valhalla client handles errors gracefully (bad coordinates, service down)
- [ ] Test SSE reconnection behavior in the browser
- [ ] Verify frontend build serves correctly behind Nginx with correct path routing

---

## Phase 7 — Production Deployment

- [ ] Provision 3 VMs (Hetzner or similar)
- [ ] Run `ansible-playbook playbooks/site.yml`
- [ ] Upload tiles/styles/sprites/glyphs to R2 (via `tiles/upload-r2.sh`)
- [ ] Update frontend style config to point at R2 URLs
- [ ] Set up TLS certificates (Let's Encrypt via certbot or Nginx ACME)
- [ ] Smoke-test: visit public URL, verify map loads, SSE streams routes, optimizer works
- [ ] Monitor resource usage on all 3 machines

---

## Implementation Order & Dependencies

```
Phase 1 (scaffolding)
  └─► Phase 2 (backend)
        ├─► Phase 3 (frontend)  ← can start once SSE endpoint exists
        └─► Phase 6 (testing)   ← ongoing as features land
Phase 4 (tiles)                 ← independent, can run in parallel with 2 & 3
Phase 5 (ansible)               ← can start once docker-compose files are stable
Phase 7 (deploy)                ← requires all above
```

---

## Current Status

**Active phase**: Phases 1–5 complete; Phase 6 requires live VMs (manual integration testing)
**Last updated**: 2026-02-17
