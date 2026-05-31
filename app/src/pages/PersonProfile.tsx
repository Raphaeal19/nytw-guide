import { useState, useEffect } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { ProfileHero } from "../components/ProfileHero";
import { TalkingPoints } from "../components/TalkingPoints";
import { ReconData } from "../components/ReconData";
import { OutreachPanel } from "../components/OutreachPanel";
import { MetModal } from "../components/MetModal";
import { usePeople } from "../hooks/usePeople";

type Tab = "overview" | "recon" | "outreach";

export function PersonProfile() {
  const { eventId, personId } = useParams<{ eventId: string; personId: string }>();
  const [searchParams] = useSearchParams();
  const attendanceId = searchParams.get("attendanceId");
  const navigate = useNavigate();

  const { people, loading, toggleMet, refetch } = usePeople(eventId);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [showMetModal, setShowMetModal] = useState(false);

  const person = people.find(
    (p) => p.person_id === personId || p.attendance_id === attendanceId
  );

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [personId]);

  if (loading) return <div className="loading">Loading…</div>;
  if (!person) return <div className="loading">Person not found.</div>;

  const handleMetToggle = () => {
    if (person.met) {
      toggleMet(person.attendance_id, false);
    } else {
      setShowMetModal(true);
    }
  };

  const handleMetMarked = async (notes: string) => {
    await toggleMet(person.attendance_id, true, notes);
  };

  const handleModalClose = () => {
    setShowMetModal(false);
    refetch();
  };

  return (
    <div className="profile-layout">
      <button
        className="back-btn"
        onClick={() => navigate(`/events/${eventId}`)}
      >
        ← Back
      </button>

      <ProfileHero person={person} onMetToggle={handleMetToggle} />

      <div className="profile-tabs">
        {(["overview", "recon", "outreach"] as Tab[]).map((t) => (
          <button
            key={t}
            className={`profile-tab ${activeTab === t ? "profile-tab--active" : ""}`}
            onClick={() => setActiveTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div className="profile-content">
        {activeTab === "overview" && <TalkingPoints person={person} />}
        {activeTab === "recon" && <ReconData person={person} />}
        {activeTab === "outreach" && (
          <OutreachPanel person={person} onSent={refetch} />
        )}
      </div>

      {!person.met && (
        <div className="profile-cta">
          <button
            className="btn btn--primary btn--full"
            onClick={() => setShowMetModal(true)}
          >
            Mark as met &amp; send follow-up
          </button>
        </div>
      )}

      {showMetModal && (
        <MetModal
          person={person}
          onMetMarked={handleMetMarked}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
}
