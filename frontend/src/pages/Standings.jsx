import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Standings() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [season, setSeason] = useState(null);

  useEffect(() => {
    client.get("/clubs/season/").then((res) => {
      const s = res.data.season || res.data.next_season;
      setSeason(s);
    });
    client.get("/matches/standings/").then((res) => setRows(res.data));
  }, []);

  const navItems = user?.role === "manager"
    ? [{ to: "/manager", label: "Scout" }, { to: "/fixtures", label: "Fixtures" }, { to: "/standings", label: "Table" }]
    : [{ to: "/club", label: "Club" }, { to: "/fixtures", label: "Fixtures" }, { to: "/standings", label: "Table" }];

  return (
    <Layout navItems={navItems}>
      <h1 className="text-2xl mb-1">League table</h1>
      {season && <p className="text-mute-400 mb-6">{season.name}</p>}

      {rows.length === 0 && <p className="text-mute-400">No results yet.</p>}
      {rows.length > 0 && (
        <div className="card">
          <table className="stat-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Club</th>
                <th>P</th>
                <th>W</th>
                <th>D</th>
                <th>L</th>
                <th>GF</th>
                <th>GA</th>
                <th>GD</th>
                <th className="text-gold-300">Pts</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={row.club_name} className={i === 0 ? "text-gold-300" : ""}>
                  <td className="num text-mute-400">{i + 1}</td>
                  <td className="font-medium">{row.club_name}</td>
                  <td className="num">{row.played}</td>
                  <td className="num">{row.won}</td>
                  <td className="num">{row.drawn}</td>
                  <td className="num">{row.lost}</td>
                  <td className="num">{row.gf}</td>
                  <td className="num">{row.ga}</td>
                  <td className="num">{row.gd > 0 ? `+${row.gd}` : row.gd}</td>
                  <td className="num font-bold">{row.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
