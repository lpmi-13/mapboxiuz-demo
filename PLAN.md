# Implementation Plan

This plan breaks the PROJECT_SPEC.md into ordered, actionable phases. Each phase lists concrete tasks with checkboxes so we can track progress as we go.

---

## Phase 1 — Project Scaffolding & Local Dev Setup

Set up the directory structure, tooling, and a working local dev loop before touching any infrastructure.

- [ ] Create the full directory tree from the spec (`backend/`, `frontend/`, `ansible/`, `tiles/`)
- [ ] **Backend scaffold**: `npm init`, install Fastify, add `src/index.js` entry point, wire up a health-check route (`GET /healthz`)
- [ ] **Frontend scaffold**: `npm create vite@latest` (React template), install MapLibre GL JS and `pmtiles` protocol plugin, create placeholder `App.jsx`
- [ ] Add root-level `docker-compose.dev.yml` for local development (backend + Valhalla + Nominatim against a small OSM extract)
- [ ] Confirm `docker compose up` starts everything and backend responds on `localhost:3000`

---

## Phase 2 — Backend Core (Fastify + Valhalla Client)

Build the backend service layer first because the frontend depends on it.

### 2a — Valhalla HTTP client (`services/valhalla.js`)
- [ ] Implement `getRoute(locations, costing)` — calls `POST /route`
- [ ] Implement `getMatrix(sources, targets, costing)` — calls `POST /sources_to_targets`
- [ ] Implement `getIsochrone(lat, lon, time, costing)` — calls `POST /isochrone`
- [ ] Add basic error handling and response normalization (extract GeoJSON geometry, distance, duration)

### 2b — UK coordinate pool (`utils/ukCoordinates.js`)
- [ ] Curate a list of ~100 UK city/town coordinates (lat/lon + display name)
- [ ] Export a helper `pickRandomPair()` that returns two distinct entries

### 2c — Route generator service (`services/routeGenerator.js`)
- [ ] Implement `generateRoutes(n=3)` — picks `n` random origin/destination pairs, calls Valhalla for each, returns array of route objects `{ origin, destination, distance_km, duration_min, geometry }`

### 2d — SSE endpoint (`routes/sse.js`)
- [ ] Register `GET /api/routes/stream` in Fastify
- [ ] Set correct headers (`Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`)
- [ ] Start an interval (10 s) that calls `generateRoutes()` and writes an SSE `data:` frame
- [ ] Clean up interval on client disconnect

### 2e — Route optimization endpoint (`routes/optimize.js`)
- [ ] Register `POST /api/optimize-route`
- [ ] Accept `{ stops, fixed_start, round_trip }`
- [ ] Implement brute-force TSP solver for ≤12 stops (`services/optimizer.js`)
- [ ] Implement nearest-neighbor + 2-opt heuristic for >12 stops
- [ ] Call Valhalla `/sources_to_targets` for the distance matrix, then solve, then call `/route` with the optimal order
- [ ] Return `{ ordered_stops, route: { geometry, distance_km, duration_min, legs } }`

### 2f — Isochrone proxy (`routes/isochrone.js`)
- [ ] Register `GET /api/isochrone`
- [ ] Accept query params `lat, lon, time, costing`
- [ ] Proxy to Valhalla `/isochrone`, return GeoJSON polygon

### 2g — Backend Dockerfile
- [ ] Multi-stage Dockerfile: `node:20-alpine` build → production image
- [ ] Expose port 3000

---

## Phase 3 — Frontend (React + MapLibre GL JS)

### 3a — Map component (`components/Map.jsx`)
- [ ] Initialize MapLibre GL JS map, centered on UK (lat 54.5, lon -2, zoom 6)
- [ ] Load map style JSON (initially use a public demo style; will switch to R2-hosted style later)
- [ ] Register PMTiles protocol for future R2-hosted tiles

### 3b — SSE client hook (`hooks/useRouteStream.js`)
- [ ] Create a React hook wrapping `EventSource` on `/api/routes/stream`
- [ ] Parse incoming JSON, expose `routes` state (array of 3 route objects)
- [ ] Handle reconnection on error

### 3c — Route layer (`components/RouteLayer.jsx`)
- [ ] Render 3 GeoJSON line layers on the map with distinct colors (e.g. `#e6194b`, `#3cb44b`, `#4363d8`)
- [ ] Update sources when `routes` state changes
- [ ] Show origin/destination markers with name labels

### 3d — Stop picker (`components/StopPicker.jsx`)
- [ ] Click-to-drop-pin functionality on the map
- [ ] List of current stops in a sidebar/panel
- [ ] "Optimize Route" button → `POST /api/optimize-route`
- [ ] Render the optimized route and ordered stops on the map

### 3e — Map style config (`lib/mapStyle.js`)
- [ ] Centralize the style URL / object so it's easy to swap between dev (public tiles) and prod (R2)

### 3f — Frontend build
- [ ] Confirm `vite build` produces a working `dist/` folder
- [ ] Verify the production build works with the backend behind Nginx (path proxying)

---

## Phase 4 — Tile Generation Pipeline

These scripts run once (or on OSM update) to produce the static assets hosted on R2.

- [ ] `tiles/generate-pmtiles.sh` — Download UK PBF from Geofabrik → run Planetiler or tilemaker → output `uk.pmtiles`
- [ ] `tiles/generate-terrain.sh` — Download SRTM tiles for UK → RGB-encode → package as `uk-terrain.pmtiles`
- [ ] `tiles/upload-r2.sh` — Upload `uk.pmtiles`, `uk-terrain.pmtiles`, style JSON, sprites, and glyphs to Cloudflare R2 using `wrangler` or `rclone`
- [ ] Prepare/customize map style JSON (e.g. OSM Bright) with source URLs pointing at R2 bucket
- [ ] Obtain or generate sprite sheets and glyph PBF files

---

## Phase 5 — Ansible & Infrastructure

### 5a — Ansible skeleton
- [ ] Create `ansible/inventory.yml` with host groups `geocoding`, `routing`, `app`
- [ ] Create `group_vars/all.yml` (domain, R2 URLs, private network IPs)
- [ ] Create group var files: `geocoding.yml`, `routing.yml`, `app.yml`

### 5b — Common role (`roles/common/`)
- [ ] Install base packages, configure firewall (UFW/iptables)
- [ ] SSH hardening, create deploy user
- [ ] Install Docker + Docker Compose plugin

### 5c — Geocoding stack role (`roles/geocoding-stack/`)
- [ ] Template and deploy `docker-compose.yml`, `postgresql.conf`, `nginx.conf` for Machine A
- [ ] Download UK OSM PBF if not present
- [ ] Trigger Nominatim initial import
- [ ] Post-import: adjust `maintenance_work_mem` down to 256 MB

### 5d — Routing stack role (`roles/routing-stack/`)
- [ ] Template and deploy `docker-compose.yml`, `nginx.conf` for Machine B
- [ ] Download UK OSM PBF if not present
- [ ] Trigger Valhalla tile build

### 5e — App stack role (`roles/app-stack/`)
- [ ] Template and deploy `docker-compose.yml`, `nginx.conf` for Machine C
- [ ] Build and deploy backend Docker image
- [ ] Deploy frontend `dist/` for Nginx to serve
- [ ] Configure Nginx for SSE proxying, API reverse proxy, and SPA fallback

### 5f — Playbooks
- [ ] `site.yml` — orchestrate full deploy across all machines
- [ ] `geocoding.yml`, `routing.yml`, `app.yml` — per-machine playbooks
- [ ] `update-osm.yml` — re-import fresh OSM data on Machine A & rebuild Valhalla tiles on Machine B

### 5g — Nginx config files (`ansible/files/`)
- [ ] Machine A: reverse proxy to Nominatim on 8080, TLS termination
- [ ] Machine B: reverse proxy to Valhalla on 8002
- [ ] Machine C: SSE proxy config, API proxy, static file serving, TLS termination

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

**Active phase**: Not started
**Last updated**: 2026-02-17
