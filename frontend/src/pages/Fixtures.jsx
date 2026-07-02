import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";

const EVENT_ICONS = {
  goal: "⚽",
  yellow: "🟨",
  red: "🟥",
  substitute: "🔄",
  miss: "—",
  save: "🧤",
};

function FixtureCard({ fixture }) {
  const [expanded, setExpanded] = useState(false);
  const finished = fixture.status === "finished";

  return (
    <div className="card cursor-pointer" onClick={() => setExpanded((e) => !e)}>
      <div className="flex items-center gap-4">
        <span className="flex-1 text-right font-display text-base">{fixture.home_club_name}</span>
        <div className="text-center min-w-[64px]">
          {finished ? (
            <span className="font-mono font-bold text-xl text-gold-300 tabular-nums">
              {fixture.home_score} – {fixture.away_score}
            </span>
          ) : (
            <span className="text-xs text-mute-400 uppercase tracking-wide">{fixture.status}</span>
          )}
        </div>
        <span className="flex-1 font-display text-base">{fixture.away_club_name}</span>
        <span className="text-xs text-mute-400 ml-2">{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && finished && fixture.events.length > 0 && (
        <div className="mt-4 border-t border-pitch-700 pt-3">
          <table className="stat-table text-xs">
            <tbody>
              {fixture.events.map((e) => (
                <tr key={e.id}>
                  <td className="num w-10 text-mute-400">{e.minute}'</td>
                  <td className="w-6">{EVENT_ICONS[e.event_type] || ""}</td>
                  <td>{e.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function Fixtures() {
  const { user } = useAuth();
  const [fixtures, setFixtures] = useState([]);
  const [season, setSeason] = useState(null);

  useEffect(() => {
    client.get("/clubs/season/").then((res) => {
      const s = res.data.season || res.data.next_season;
      setSeason(s);
      if (s) client.get(`/api/matches/?season=${s.id}`).then((r) => setFixtures(r.data));
    });
    client.get("/matches/").then((res) => setFixtures(res.data));
  }, []);

  const navItems = user?.role === "manager"
    ? [{ to: "/manager", label: "Scout" }, { to: "/fixtures", label: "Fixtures" }, { to: "/standings", label: "Table" }]
    : [{ to: "/club", label: "Club" }, { to: "/fixtures", label: "Fixtures" }, { to: "/standings", label: "Table" }];

  return (
    <Layout navItems={navItems}>
      <h1 className="text-2xl mb-1">Fixtures</h1>
      {season && <p className="text-mute-400 mb-6">{season.name}</p>}
      {fixtures.length === 0 && <p className="text-mute-400">No fixtures yet this season.</p>}
      {fixtures.map((f) => <FixtureCard key={f.id} fixture={f} />)}
    </Layout>
  );
}
