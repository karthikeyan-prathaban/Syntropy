import { Route, Routes, Navigate } from "react-router-dom";
import ConsentCallbackPage from "./pages/ConsentCallbackPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";

function PrivateRoute({ children }: { children: JSX.Element }) {
  const userId = localStorage.getItem("syntropy_user_id");
  return userId ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/consent/callback" element={<ConsentCallbackPage />} />
      <Route path="/dashboard" element={
        <PrivateRoute>
          <DashboardPage />
        </PrivateRoute>
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
