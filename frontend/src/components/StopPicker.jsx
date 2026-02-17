import maplibregl from "maplibre-gl";
import { useEffect, useRef, useState } from "react";

const OPTIMIZED_COLOR = "#ff6b35";

const panelStyle = {
  position: "absolute",
  top: 16,
  right: 16,
  background: "white",
  padding: 16,
  borderRadius: 8,
  width: 260,
  boxShadow: "0 2px 12px rgba(0,0,0,0.2)",
  fontFamily: "system-ui, sans-serif",
  zIndex: 10,
};

/**
 * Sidebar panel for dropping stop pins and calling the optimize-route API.
 *
 * Props:
 *   map — maplibregl.Map instance
 */
export default function StopPicker({ map }) {
  const [stops, setStops] = useState([]);
  const [optimizedRoute, setOptimizedRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const markersRef = useRef([]);

  // Click-to-add-stop
  useEffect(() => {
    if (!map) return;
    const handler = (e) => {
      const { lat, lng: lon } = e.lngLat;
      setStops((prev) => [
        ...prev,
        { lat, lon, name: `Stop ${prev.length + 1}` },
      ]);
    };
    map.on("click", handler);
    return () => map.off("click", handler);
  }, [map]);

  // Sync markers to stops list
  useEffect(() => {
    if (!map) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = stops.map((stop, i) => {
      const el = document.createElement("div");
      el.textContent = String(i + 1);
      el.style.cssText = `
        width:24px;height:24px;border-radius:50%;
        background:#334155;color:white;font-size:12px;font-weight:600;
        display:flex;align-items:center;justify-content:center;
        border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4);
        cursor:pointer;
      `;
      return new maplibregl.Marker({ element: el })
        .setLngLat([stop.lon, stop.lat])
        .addTo(map);
    });
    return () => markersRef.current.forEach((m) => m.remove());
  }, [map, stops]);

  const handleOptimize = async () => {
    if (stops.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/optimize-route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stops, fixed_start: false, round_trip: false }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setOptimizedRoute(data);

      // Render optimized route on the map
      if (map.getLayer("optimized-route")) map.removeLayer("optimized-route");
      if (map.getSource("optimized-route")) map.removeSource("optimized-route");
      map.addSource("optimized-route", {
        type: "geojson",
        data: { type: "Feature", geometry: data.route.geometry },
      });
      map.addLayer({
        id: "optimized-route",
        type: "line",
        source: "optimized-route",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": OPTIMIZED_COLOR,
          "line-width": 5,
          "line-dasharray": [2, 1],
        },
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setStops([]);
    setOptimizedRoute(null);
    setError(null);
    if (map) {
      if (map.getLayer("optimized-route")) map.removeLayer("optimized-route");
      if (map.getSource("optimized-route")) map.removeSource("optimized-route");
    }
  };

  return (
    <div style={panelStyle}>
      <h3 style={{ margin: "0 0 6px", fontSize: 15 }}>Route Optimizer</h3>
      <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 10px" }}>
        Click the map to add stops, then press Optimize.
      </p>

      <ul style={{ listStyle: "none", padding: 0, margin: "0 0 10px", maxHeight: 160, overflowY: "auto" }}>
        {stops.map((s, i) => (
          <li key={i} style={{ fontSize: 13, padding: "3px 0", borderBottom: "1px solid #f1f5f9" }}>
            <strong>{i + 1}.</strong> {s.name}{" "}
            <span style={{ color: "#94a3b8" }}>
              ({s.lat.toFixed(3)}, {s.lon.toFixed(3)})
            </span>
          </li>
        ))}
        {stops.length === 0 && (
          <li style={{ fontSize: 12, color: "#94a3b8", padding: "4px 0" }}>
            No stops yet
          </li>
        )}
      </ul>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={handleOptimize}
          disabled={stops.length < 2 || loading}
          style={{
            flex: 1, padding: "7px 0", borderRadius: 6, border: "none",
            background: stops.length < 2 ? "#e2e8f0" : "#334155",
            color: stops.length < 2 ? "#94a3b8" : "white",
            cursor: stops.length < 2 ? "default" : "pointer", fontSize: 13,
          }}
        >
          {loading ? "Optimizing…" : "Optimize"}
        </button>
        <button
          onClick={handleClear}
          style={{
            padding: "7px 12px", borderRadius: 6, border: "1px solid #e2e8f0",
            background: "white", cursor: "pointer", fontSize: 13,
          }}
        >
          Clear
        </button>
      </div>

      {error && (
        <p style={{ color: "#dc2626", fontSize: 12, margin: "8px 0 0" }}>
          {error}
        </p>
      )}

      {optimizedRoute && (
        <div style={{ marginTop: 10, fontSize: 12, color: "#334155" }}>
          <strong>Optimized result</strong>
          <div style={{ marginTop: 4 }}>
            Distance: {optimizedRoute.route.distance_km} km
            {" · "}
            Duration: {optimizedRoute.route.duration_min} min
          </div>
          <ol style={{ margin: "6px 0 0", paddingLeft: 16 }}>
            {optimizedRoute.ordered_stops.map((s, i) => (
              <li key={i} style={{ padding: "1px 0" }}>
                {s.name}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
