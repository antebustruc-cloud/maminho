import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const [role, setRole] = useState("club_owner");
  const [form, setForm] = useState({ username: "", email: "", password: "", club_name: "", country: "", city: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await client.post("/auth/register/", { ...form, role });
      login(res.data.token, res.data.user);
      navigate(role === "manager" ? "/manager" : "/club");
    } catch (err) {
      const data = err.response?.data;
      setError(data ? Object.values(data).flat().join(" ") : "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-screen flex items-center justify-center min-h-screen">
      <form onSubmit={handleSubmit} className="auth-card w-90 bg-pitch-800 border border-pitch-600 rounded-md p-8">
        <h1 className="text-xl text-gold-300 mb-6">Join Maminho</h1>

        <div className="role-toggle">
          <button type="button" className={role === "club_owner" ? "active" : ""} onClick={() => setRole("club_owner")}>
            Club owner
          </button>
          <button type="button" className={role === "manager" ? "active" : ""} onClick={() => setRole("manager")}>
            Manager
          </button>
        </div>

        <div className="field">
          <label>Username</label>
          <input value={form.username} onChange={(e) => update("username", e.target.value)} required />
        </div>
        <div className="field">
          <label>Email</label>
          <input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} required />
        </div>
        <div className="field">
          <label>Password</label>
          <input type="password" value={form.password} onChange={(e) => update("password", e.target.value)} required minLength={8} />
        </div>

        {role === "club_owner" && (
          <>
            <div className="field">
              <label>Club name</label>
              <input value={form.club_name} onChange={(e) => update("club_name", e.target.value)} required />
            </div>
            <div className="field">
              <label>Country</label>
              <input value={form.country} onChange={(e) => update("country", e.target.value)} />
            </div>
            <div className="field">
              <label>City</label>
              <input value={form.city} onChange={(e) => update("city", e.target.value)} />
            </div>
          </>
        )}

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="btn-primary w-full mt-2" disabled={submitting}>
          {submitting ? "Creating account..." : "Create account"}
        </button>

        <p className="text-sm text-mute-400 mt-5">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
