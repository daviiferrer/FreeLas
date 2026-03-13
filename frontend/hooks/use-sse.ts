import { useEffect, useState, useRef } from "react";

export type PipelineEvent = {
  type: string;
  message?: string;
  [key: string]: any;
};

export function useSSE(url: string) {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [activeThinking, setActiveThinking] = useState<Record<string, any>>({});
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Connect to SSE
    const sse = new EventSource(url);
    eventSourceRef.current = sse;

    sse.onopen = () => setIsConnected(true);
    sse.onerror = () => {
      setIsConnected(false);
      sse.close();
      // Auto-reconnect after 3s
      setTimeout(() => {
        if (!eventSourceRef.current || eventSourceRef.current.readyState === EventSource.CLOSED) {
          eventSourceRef.current = new EventSource(url);
        }
      }, 3000);
    };

    sse.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as PipelineEvent;

        // Skip heartbeats
        if (data.type === "heartbeat") return;

        // Handle specific event types for state
        if (data.type === "agent_thinking_start" || data.type === "agent_thinking") {
          setActiveThinking((prev) => ({
            ...prev,
            [data.agent]: {
              ...data,
              full_thinking: data.full_thinking || prev[data.agent]?.full_thinking || "",
            },
          }));
        } else if (data.type === "agent_thinking_end" || data.type === "agent_result") {
          setActiveThinking((prev) => {
            const next = { ...prev };
            delete next[data.agent];
            return next;
          });
        }

        // Add to chronological log for the live feed, keeping last 50
        setEvents((prev) => [data, ...prev].slice(0, 50));
      } catch (err) {
        console.error("Failed to parse SSE event", err);
      }
    };

    return () => {
      sse.close();
    };
  }, [url]);

  const clearEvents = () => setEvents([]);

  return { events, isConnected, activeThinking, clearEvents };
}
