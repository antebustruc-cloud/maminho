import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout({ kcBalance, navItems, children }) {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-pitch-800 border-r border-pitch-600 p-6 flex flex-col gap-6">
        <div className="font-display text-2xl text-gold-300 tracking-wide">MAMINHO</div>

        {kcBalance !== undefined && (
          <div className="kc-ticker">
            <div className="label">KunaCoins</div>
            <div className="value">{kcBalance.toLocaleString()} KC</div>
          </div>
        )}

        <nav className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto text-xs text-mute-400">
          <div className="mb-2">{user?.username} · {user?.role.replace("_", " ")}</div>
          <button onClick={logout} className="nav-link">Log out</button>
        </div>
      </aside>

      <main className="flex-1 p-10 max-w-4xl">{children}</main>
    </div>
  );
}
