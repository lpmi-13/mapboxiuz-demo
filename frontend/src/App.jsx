import { useRef, useState } from "react";
import Map from "./components/Map.jsx";
import RouteLayer from "./components/RouteLayer.jsx";
import StopPicker from "./components/StopPicker.jsx";
import { useRouteStream } from "./hooks/useRouteStream.js";

export default function App() {
  const mapRef = useRef(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const { routes, connected, error: streamError } = useRouteStream();

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <Map mapRef={mapRef} onLoad={() => setMapLoaded(true)} />

      {mapLoaded && mapRef.current && (
        <>
          <RouteLayer map={mapRef.current} routes={routes} />
          <StopPicker map={mapRef.current} />
        </>
      )}

      {/* Status bar */}
      <div
        style={{
          position: "absolute",
          bottom: 16,
          left: 16,
          background: "rgba(255,255,255,0.9)",
          padding: "4px 12px",
          borderRadius: 16,
          fontSize: 12,
          boxShadow: "0 1px 4px rgba(0,0,0,.15)",
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: connected ? "#22c55e" : "#94a3b8",
            display: "inline-block",
          }}
        />
        {connected ? "Live — routes update every 10 s" : "Connecting…"}
        {streamError && (
          <span style={{ color: "#dc2626", marginLeft: 4 }}>{streamError}</span>
        )}
      </div>
    </div>
  );
}
