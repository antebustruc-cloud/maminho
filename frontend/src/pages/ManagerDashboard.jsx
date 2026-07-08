import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import client from "../api/client";

const NAV = [
  { to: "/manager",   label: "Scout" },
  { to: "/fixtures",  label: "Fixtures" },
  { to: "/standings", label: "Table" },
];

function PlayerRow({ player, onBid, busy }) {
  const [wage, setWage] = useState(50);
  const [years, setYears] = useState(2);
  return (
    <tr>
      <td>{player.name}</td>
      <td className="num">{player.age}</td>
      <td className="num">{player.finishing}</td>
      <td className="num">{player.passing}</td>
      <td className="num">{player.dribbling}</td>
      <td>
        <div className="flex gap-1.5 items-center">
          <input type="number" min={1} value={wage} onChange={(e) => setWage(e.target.value)} className="w-16 text-xs py-1 px-1.5" />
          <select value={years} onChange={(e) => setYears(e.target.value)} className="text-xs py-1 px-1.5">
            {[1,2,3,4,5].map((y) => <option key={y} value={y}>{y}y</option>)}
          </select>
          <button className="btn-primary text-xs py-1 px-2.5" disabled={busy} onClick={() => onBid(player.id, wage, years)}>
            Bid
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function ManagerDashboard() {
  const [profile, setProfile] = useState(null);
  const [freeAgents, setFreeAgents] = useState([]);
  const [roster, setRoster] = useState([]);
  const [view, setView] = useState("scout");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function loadAll() {
    client.get("/players/manager/me/").then((res) => setProfile(res.data));
    client.get("/players/free-agents/?sport=football").then((res) => setFreeAgents(res.data));
    client.get("/players/mine/").then((res) => setRoster(res.data));
  }

  useEffect(loadAll, []);

  async function placeBid(playerId, wage, years) {
    setError(""); setBusy(true);
    try {
      await client.post(`/players/${playerId}/bid/`, { wage_offer: Math.round(wage * 100), contract_length_years: years });
      loadAll();
    } catch (err) {
      setError(err.response?.data?.[0] || "Bid failed.");
    } finally { setBusy(false); }
  }

  if (!profile) return null;

  return (
    <Layout kcBalance={profile.kc_balance} navItems={NAV}>
      <h1 className="text-2xl mb-1">Manager</h1>
      <p className="text-mute-400 mb-6">{profile.username}</p>

      {error && <p className="error-text mb-4">{error}</p>}

      <div className="flex gap-2 mb-6">
        <button onClick={() => setView("scout")} className={`nav-link w-auto px-4 ${view === "scout" ? "active" : ""}`}>
          Free agents ({freeAgents.length})
        </button>
        <button onClick={() => setView("roster")} className={`nav-link w-auto px-4 ${view === "roster" ? "active" : ""}`}>
          My roster ({roster.length})
        </button>
      </div>

      {view === "scout" && (
        <div className="card">
          <h2>Free agent pool — football</h2>
          <p className="text-xs text-mute-400 mb-3">Bidding opens a 24h window. Highest offer when it closes wins — outbid anytime before then.</p>
          <table className="stat-table">
            <thead><tr><th>Name</th><th>Age</th><th>Fin</th><th>Pas</th><th>Dri</th><th>Bid (KC/mo, years)</th></tr></thead>
            <tbody>
              {freeAgents.map((p) => <PlayerRow key={p.id} player={p} onBid={placeBid} busy={busy} />)}
            </tbody>
          </table>
        </div>
      )}

      {view === "roster" && (
        <div className="card">
          <h2>My players</h2>
          {roster.length === 0 && <p className="text-sm text-mute-400">No contracted players yet.</p>}
          {roster.length > 0 && (
            <table className="stat-table">
              <thead><tr><th>Name</th><th>Age</th><th>Fin</th><th>Pas</th><th>Dri</th></tr></thead>
              <tbody>
                {roster.map((p) => (
                  <tr key={p.id}>
                    <td>{p.name}</td>
                    <td className="num">{p.age}</td>
                    <td className="num">{p.finishing}</td>
                    <td className="num">{p.passing}</td>
                    <td className="num">{p.dribbling}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </Layout>
  );
}
