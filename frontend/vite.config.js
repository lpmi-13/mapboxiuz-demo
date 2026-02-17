import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward API and SSE calls to the Django backend in dev
      "/api": "http://localhost:8000",
      "/healthz": "http://localhost:8000",
    },
  },
});
