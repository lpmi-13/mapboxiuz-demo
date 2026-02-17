import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";

const ROUTE_COLORS = ["#e6194b", "#3cb44b", "#4363d8"];

/**
 * Renders up to 3 GeoJSON route lines on the map.
 * Also places origin/destination markers with name labels.
 *
 * Props:
 *   map    — maplibregl.Map instance (may be null on first render)
 *   routes — array of route objects from the SSE stream
 */
export default function RouteLayer({ map, routes }) {
  const markersRef = useRef([]);

  useEffect(() => {
    if (!map) return;

    // Clean up previous markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    // Remove previous layers / sources
    routes.forEach((_, i) => {
      const id = `sse-route-${i}`;
      if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource(id)) map.removeSource(id);
    });

    // Add current routes
    routes.forEach((route, i) => {
      if (!route.geometry?.coordinates?.length) return;

      const id = `sse-route-${i}`;
      const color = ROUTE_COLORS[i % ROUTE_COLORS.length];

      map.addSource(id, {
        type: "geojson",
        data: { type: "Feature", geometry: route.geometry },
      });

      map.addLayer({
        id,
        type: "line",
        source: id,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": color,
          "line-width": 4,
          "line-opacity": 0.85,
        },
      });

      // Origin marker
      const originEl = document.createElement("div");
      originEl.title = route.origin?.name ?? "Origin";
      originEl.style.cssText = `
        width:10px;height:10px;border-radius:50%;
        background:${color};border:2px solid white;
        box-shadow:0 1px 3px rgba(0,0,0,.4);
      `;
      markersRef.current.push(
        new maplibregl.Marker({ element: originEl })
          .setLngLat(route.geometry.coordinates[0])
          .setPopup(
            new maplibregl.Popup({ offset: 8 }).setText(
              route.origin?.name ?? "Origin"
            )
          )
          .addTo(map)
      );

      // Destination marker
      const destCoords =
        route.geometry.coordinates[route.geometry.coordinates.length - 1];
      const destEl = document.createElement("div");
      destEl.title = route.destination?.name ?? "Destination";
      destEl.style.cssText = `
        width:12px;height:12px;border-radius:50%;
        background:${color};border:3px solid white;
        box-shadow:0 1px 3px rgba(0,0,0,.4);
      `;
      markersRef.current.push(
        new maplibregl.Marker({ element: destEl })
          .setLngLat(destCoords)
          .setPopup(
            new maplibregl.Popup({ offset: 8 }).setText(
              `${route.destination?.name ?? "Destination"} — ${route.distance_km} km / ${route.duration_min} min`
            )
          )
          .addTo(map)
      );
    });

    return () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      routes.forEach((_, i) => {
        const id = `sse-route-${i}`;
        if (map.getLayer(id)) map.removeLayer(id);
        if (map.getSource(id)) map.removeSource(id);
      });
    };
  }, [map, routes]);

  return null;
}
