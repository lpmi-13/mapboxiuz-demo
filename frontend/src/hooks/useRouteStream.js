import { useEffect, useState } from "react";

const RETRY_DELAY_MS = 3000;

/**
 * Opens an SSE connection to /api/routes/stream and returns the latest
 * array of route objects plus connection state.
 *
 * Automatically reconnects after RETRY_DELAY_MS on error.
 */
export function useRouteStream() {
  const [routes, setRoutes] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let es = null;
    let retryTimeout = null;

    function connect() {
      es = new EventSource("/api/routes/stream");

      es.onopen = () => {
        setConnected(true);
        setError(null);
      };

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (Array.isArray(data)) {
            setRoutes(data);
          }
        } catch {
          // Ignore parse errors — stream continues
        }
      };

      es.onerror = () => {
        setConnected(false);
        setError("Connection lost — reconnecting…");
        es.close();
        retryTimeout = setTimeout(connect, RETRY_DELAY_MS);
      };
    }

    connect();

    return () => {
      if (es) es.close();
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, []);

  return { routes, connected, error };
}
