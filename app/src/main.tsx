import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
} from "react-router-dom";
import { EventDetail } from "./pages/EventDetail";
import { PersonProfile } from "./pages/PersonProfile";
import { OfflineBanner } from "./components/OfflineBanner";
import { useEvents } from "./hooks/useEvents";
import { flush } from "./lib/offlineQueue";
import "./index.css";

// Flush any mutations that were queued during a previous offline session
if (navigator.onLine) {
  flush();
}

function RootRedirect() {
  const navigate = useNavigate();
  const { events, loading } = useEvents();

  const lastEventId =
    typeof localStorage !== "undefined"
      ? localStorage.getItem("lastEventId")
      : null;

  useEffect(() => {
    if (loading) return;
    if (events.length === 0) return;
    const target =
      (lastEventId && events.find((e) => e.id === lastEventId)?.id) ||
      events[0].id;
    navigate(`/events/${target}`, { replace: true });
  }, [loading, events, lastEventId, navigate]);

  if (loading) return <div className="loading">Loading…</div>;
  if (events.length === 0) return <Navigate to="/events" replace />;
  return null;
}

function App() {
  return (
    <BrowserRouter>
      <OfflineBanner />
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/events" element={<EventDetail />} />
        <Route path="/events/:eventId" element={<EventDetail />} />
        <Route
          path="/events/:eventId/people/:personId"
          element={<PersonProfile />}
        />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
