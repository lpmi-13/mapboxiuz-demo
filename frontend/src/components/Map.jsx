import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import { useEffect, useRef } from "react";
import { MAP_STYLE } from "../lib/mapStyle";

/**
 * Renders a full-screen MapLibre GL JS map centred on the UK.
 *
 * Props:
 *   mapRef  — ref that will be populated with the maplibregl.Map instance
 *   onLoad  — called once the map's 'load' event fires
 */
export default function Map({ mapRef, onLoad }) {
  const containerRef = useRef(null);

  useEffect(() => {
    // Register PMTiles protocol so pmtiles:// sources work
    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [-2.0, 54.5], // UK centre
      zoom: 6,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-left");
    map.addControl(new maplibregl.ScaleControl(), "bottom-left");

    map.once("load", () => {
      mapRef.current = map;
      if (onLoad) onLoad();
    });

    return () => {
      maplibregl.removeProtocol("pmtiles");
      map.remove();
      mapRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      ref={containerRef}
      style={{ position: "absolute", inset: 0 }}
    />
  );
}
