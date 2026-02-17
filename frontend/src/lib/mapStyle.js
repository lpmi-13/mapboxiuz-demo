/**
 * Map style URL configuration.
 *
 * In development this points at MapLibre's free demo tile service.
 * In production set VITE_MAP_STYLE_URL to the R2-hosted style JSON URL.
 */
export const MAP_STYLE =
  import.meta.env.VITE_MAP_STYLE_URL ||
  "https://demotiles.maplibre.org/style.json";
