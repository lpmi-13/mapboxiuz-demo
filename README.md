# Mapboxiuz Demo

A self-hosted mapping platform serving UK-only data, replicating core Mapbox functionality using entirely open-source components. The system displays randomly generated routes on an interactive map, updated in real time via Server-Sent Events, and provides a route optimizer that solves the Travelling Salesman Problem for user-placed stops.

## Features

- **Live route streaming** — 3 random UK driving routes generated and pushed to the browser every 10 seconds via SSE
- **Route optimization** — drop pins on the map, click "Optimize", and get the shortest visit order (exact brute-force for ≤12 stops, nearest-neighbour + 2-opt heuristic beyond that)
- **Isochrones** — travel-time contour polygons from any point
- **Vector tiles from Cloudflare R2** — no tile-server compute; the browser fetches PMTiles directly
- **Estimated cost: ~$15–25/month** on 3 small Hetzner VMs + R2 free tier

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, MapLibre GL JS 4, Vite 5, PMTiles |
| Backend | Python 3.12, Django 5, Django REST Framework, Daphne (ASGI), httpx |
| Routing engine | Valhalla (driving, cycling, pedestrian) |
| Geocoding | Nominatim 4.4, PostgreSQL 16 + PostGIS 3.4 |
| Tile pipeline | Planetiler, SRTM 30m elevation data, Cloudflare R2 |
| Infrastructure | Ansible, Docker & Docker Compose, Nginx |
| CI/CD | GitHub Actions (pytest + Vite build) |

## Architecture

```
┌──────────────────────────────┐
│         Browser              │
│  React + MapLibre GL JS      │
│  SSE client (EventSource)    │
└─────────────┬────────────────┘
              │ HTTPS
              ▼
┌──────────────────────────────┐      ┌────────────────────────┐
│  Machine C — App Server      │      │  Cloudflare R2         │
│                              │      │                        │
│  Nginx (TLS, SSE proxy)     │      │  uk.pmtiles (vectors)  │
│  Django / Daphne :8000       │      │  uk-terrain.pmtiles    │
│  React static build          │      │  style.json, sprites,  │
│                              │      │  glyphs                │
└──────┬───────────┬───────────┘      └────────────────────────┘
       │           │
  private net  private net
       │           │
       ▼           ▼
┌──────────────┐  ┌──────────────────────────┐
│ Machine B    │  │ Machine A                │
│ Routing      │  │ Geocoding                │
│              │  │                          │
│ Valhalla     │  │ PostgreSQL 16 + PostGIS  │
│ :8002        │  │ Nominatim 4.4            │
│ Nginx        │  │ Nginx                    │
└──────────────┘  └──────────────────────────┘
```

**Machine A** (4 vCPU, 8 GB) — PostgreSQL + PostGIS + Nominatim for geocoding.

**Machine B** (4 vCPU, 8 GB) — Valhalla routing engine (route, matrix, isochrone, locate).

**Machine C** (2–4 vCPU, 2–4 GB) — Django backend serving the REST/SSE API, plus the compiled React SPA. Nginx sits in front for TLS termination and SSE-aware proxying (`proxy_buffering off`).

**Cloudflare R2** — stores vector tiles, terrain tiles, map style, sprites, and glyph files. The browser loads these directly via the PMTiles protocol; no tile traffic hits the app server.

All three machines communicate over a private 10.0.0.0/24 network. Only Machine C is publicly accessible.

## Project Structure

```
├── backend/            Django + Daphne backend
│   ├── api/            Main app: views, services, utils, tests
│   └── config/         Django project settings, ASGI entry point
├── frontend/           React + MapLibre GL JS SPA
│   └── src/            Components, hooks, map style config
├── ansible/            Ansible roles & playbooks for all 3 machines
│   ├── roles/          common, geocoding-stack, routing-stack, app-stack
│   └── files/          Docker Compose & Nginx configs per machine
├── tiles/              One-time tile generation & R2 upload scripts
├── docker-compose.dev.yml   Local dev stack (Isle of Wight extract)
└── .github/workflows/  CI pipeline (backend tests + frontend build)
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/healthz` | GET | Health check |
| `/api/routes/stream` | GET | SSE stream — 3 random routes every 10s |
| `/api/optimize-route` | POST | TSP solver + Valhalla routing for ordered stops |
| `/api/isochrone` | GET | Travel-time contour proxy to Valhalla |

## Quick Start (Local Development)

```bash
# Start the local dev stack (uses a small Isle of Wight OSM extract)
docker compose -f docker-compose.dev.yml up

# In a separate terminal, run the frontend dev server
cd frontend && npm install && npm run dev

# Run backend tests
cd backend && pip install -r requirements-dev.txt && python -m pytest api/tests/ -v

# Build the frontend for production
cd frontend && npm run build
```

| Service | URL |
|---|---|
| Frontend (Vite dev) | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Valhalla | http://localhost:8002 |
| Nominatim | http://localhost:8080 |

## Deployment

Deployment is automated with Ansible. After provisioning 3 VMs and configuring `ansible/inventory.yml` with their IPs:

```bash
cd ansible
ansible-playbook playbooks/site.yml
```

Individual machines can be provisioned separately:

```bash
ansible-playbook playbooks/geocoding.yml   # Machine A
ansible-playbook playbooks/routing.yml     # Machine B
ansible-playbook playbooks/app.yml         # Machine C
```

## Tile Generation

Run once to build and upload map tiles to Cloudflare R2:

```bash
cd tiles
./generate-pmtiles.sh        # OSM → vector PMTiles (z0-14)
./generate-terrain.sh        # SRTM → RGB terrain PMTiles
./build-style.sh             # Stamp R2 URL into style template
./upload-r2.sh               # Upload everything to R2
```

## License

See [LICENSE](LICENSE) for details.
