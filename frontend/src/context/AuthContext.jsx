import { createContext, useContext, useEffect, useState } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("maminho_token");
    if (!token) {
      setLoading(false);
      return;
    }
    client.get("/auth/me/")
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem("maminho_token"))
      .finally(() => setLoading(false));
  }, []);

  function login(token, userData) {
    localStorage.setItem("maminho_token", token);
    setUser(userData);
  }

  function logout() {
    localStorage.removeItem("maminho_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
