import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import client from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await client.post("/auth/login/", { username, password });
      login(res.data.token, res.data.user);
      navigate(res.data.user.role === "manager" ? "/manager" : "/club");
    } catch (err) {
      setError(err.response?.data?.non_field_errors?.[0] || "Login failed -- check your credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-screen flex items-center justify-center min-h-screen">
      <form onSubmit={handleSubmit} className="auth-card w-90 bg-pitch-800 border border-pitch-600 rounded-md p-8">
        <h1 className="text-xl text-gold-300 mb-6">Maminho</h1>

        <div className="field">
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <div className="field">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="btn-primary w-full mt-2" disabled={submitting}>
          {submitting ? "Logging in..." : "Log in"}
        </button>

        <p className="text-sm text-mute-400 mt-5">
          No account? <Link to="/register">Register</Link>
        </p>
      </form>
    </div>
  );
}
