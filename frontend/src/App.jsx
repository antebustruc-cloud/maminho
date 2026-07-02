import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ClubDashboard from "./pages/ClubDashboard";
import ManagerDashboard from "./pages/ManagerDashboard";
import Fixtures from "./pages/Fixtures";
import Standings from "./pages/Standings";

function PrivateRoute({ children, role }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" />;
  if (role && user.role !== role) return <Navigate to={user.role === "manager" ? "/manager" : "/club"} />;
  return children;
}

function Home() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" />;
  return <Navigate to={user.role === "manager" ? "/manager" : "/club"} />;
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/"          element={<Home />} />
          <Route path="/login"     element={<Login />} />
          <Route path="/register"  element={<Register />} />
          <Route path="/club"      element={<PrivateRoute role="club_owner"><ClubDashboard /></PrivateRoute>} />
          <Route path="/manager"   element={<PrivateRoute role="manager"><ManagerDashboard /></PrivateRoute>} />
          <Route path="/fixtures"  element={<PrivateRoute><Fixtures /></PrivateRoute>} />
          <Route path="/standings" element={<PrivateRoute><Standings /></PrivateRoute>} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}
