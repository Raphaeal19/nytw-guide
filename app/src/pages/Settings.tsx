import { useNavigate } from "react-router-dom";
import { useConnections } from "../hooks/useConnections";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function Settings() {
  const navigate = useNavigate();
  const { connections, loading } = useConnections();

  const partiful = connections.find((c) => c.service_name === "partiful");
  const isConnected = partiful?.status === "connected";

  return (
    <div className="settings-page">
      <div className="settings-header">
        <button className="btn settings-back" onClick={() => navigate(-1)}>
          &larr;
        </button>
        <h1 className="settings-title">Settings</h1>
      </div>

      <section className="settings-section">
        <h2 className="settings-section-title">Connections</h2>

        {loading ? (
          <div className="loading">Loading...</div>
        ) : (
          <div className="connection-card">
            <div className="connection-card__header">
              <div className="connection-card__icon">P</div>
              <div className="connection-card__info">
                <span className="connection-card__name">Partiful</span>
                <span className="connection-card__desc">
                  Import events and guest lists
                </span>
              </div>
              <span
                className={`connection-status ${isConnected ? "connection-status--on" : "connection-status--off"}`}
              >
                {isConnected ? "Connected" : "Not connected"}
              </span>
            </div>

            {partiful?.last_connected_at && (
              <p className="connection-card__meta">
                Last connected: {timeAgo(partiful.last_connected_at)}
              </p>
            )}

            <div className="connection-card__instructions">
              <p>Run on your Mac to connect:</p>
              <code>python3 agent/setup_partiful_auth.py</code>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
