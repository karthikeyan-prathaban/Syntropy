import { Route, Routes, Navigate } from "react-router-dom";
import ConsentCallbackPage from "./pages/ConsentCallbackPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import LandingPage from "./pages/LandingPage";

function PrivateRoute({ children }: { children: JSX.Element }) {
  const userId = localStorage.getItem("syntropy_user_id");
  return userId ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/consent/callback" element={<ConsentCallbackPage />} />
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <DashboardPage />
          </PrivateRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
