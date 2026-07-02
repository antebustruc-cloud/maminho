import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import client from "../api/client";

const FACILITY_TYPES = ["soccer_field","sports_hall","swimming_pool","tennis_court","gym","medical_center"];

const NAV = [
  { to: "/club",      label: "Club" },
  { to: "/fixtures",  label: "Fixtures" },
  { to: "/standings", label: "Table" },
];

export default function ClubDashboard() {
  const [club, setClub] = useState(null);
  const [offseason, setOffseason] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    client.get("/clubs/me/").then((res) => setClub(res.data));
    client.get("/clubs/season/").then((res) => setOffseason(res.data.status === "offseason"));
  }

  useEffect(load, []);

  async function buildFacility(facilityType) {
    setError(""); setBusy(true);
    try {
      await client.post("/clubs/facilities/build/", { facility_type: facilityType });
      load();
    } catch (err) {
      setError(err.response?.data?.[0] || "Couldn't build that facility.");
    } finally { setBusy(false); }
  }

  async function upgradeFacility(id) {
    setError(""); setBusy(true);
    try {
      await client.post(`/clubs/facilities/${id}/upgrade/`);
      load();
    } catch (err) {
      setError(err.response?.data?.[0] || "Couldn't upgrade.");
    } finally { setBusy(false); }
  }

  async function buyLicense(sport) {
    setError(""); setBusy(true);
    try {
      await client.post("/clubs/licenses/purchase/", { sport });
      load();
    } catch (err) {
      setError(err.response?.data?.[0] || "Couldn't purchase license.");
    } finally { setBusy(false); }
  }

  if (!club) return null;

  const ownedTypes = new Set(club.facilities.map((f) => f.facility_type));
  const hasFootballLicense = club.sport_licenses.some((l) => l.sport === "football");

  return (
    <Layout kcBalance={club.kc_balance} navItems={NAV}>
      <h1 className="text-2xl mb-1">{club.name}</h1>
      <p className="text-mute-400 mb-1">{club.city}, {club.country}</p>
      {!offseason && (
        <p className="text-xs text-gold-500 mb-6">⚠️ Season active — facility builds/upgrades locked until offseason</p>
      )}
      {offseason && <p className="text-xs text-mute-400 mb-6">Offseason — free to build and upgrade</p>}

      {error && <p className="error-text mb-4">{error}</p>}

      <div className="card">
        <h2>Facilities</h2>
        <table className="stat-table mb-4">
          <thead><tr><th>Type</th><th>Level</th><th>Stat bonus</th><th></th></tr></thead>
          <tbody>
            {club.facilities.map((f) => (
              <tr key={f.id}>
                <td>{f.facility_type_display}</td>
                <td className="num">{f.level}/10</td>
                <td className="num text-mute-400">+{f.level}%</td>
                <td>
                  {f.level < 10 && offseason && (
                    <button className="btn-primary text-xs py-1 px-2.5" disabled={busy} onClick={() => upgradeFacility(f.id)}>
                      Upgrade
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {offseason && (
          <div className="flex flex-wrap gap-2">
            {FACILITY_TYPES.filter((t) => !ownedTypes.has(t)).map((t) => (
              <button key={t} className="btn-primary text-xs py-1.5 px-3" disabled={busy} onClick={() => buildFacility(t)}>
                Build {t.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2>Sport licenses</h2>
        {club.sport_licenses.length === 0 && <p className="text-sm text-mute-400 mb-3">No licenses yet.</p>}
        {!hasFootballLicense && (
          <button className="btn-primary text-sm" disabled={busy} onClick={() => buyLicense("football")}>
            Buy football license (700 KC)
          </button>
        )}
        {hasFootballLicense && <p className="text-sm text-gold-300">⚽ Football license active</p>}
      </div>
    </Layout>
  );
}
