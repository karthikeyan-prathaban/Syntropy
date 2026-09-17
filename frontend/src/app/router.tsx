import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./AppShell";
import { LandingPage } from "../pages/LandingPage";
import { LoginPage } from "../pages/LoginPage";
import { SignupPage } from "../pages/SignupPage";
import { OverviewPage } from "../pages/OverviewPage";
import { CashflowPage } from "../pages/CashflowPage";
import { SpendingPage } from "../pages/SpendingPage";
import { AccountsPage } from "../pages/AccountsPage";
import { TransactionsPage } from "../pages/TransactionsPage";
import { RecallPage } from "../pages/RecallPage";
import { InsightsPage } from "../pages/InsightsPage";
import { SettingsPage } from "../pages/SettingsPage";
import { ConsentCallbackPage } from "../pages/ConsentCallbackPage";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("novaa_token");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/consent/callback" element={<ConsentCallbackPage />} />
        <Route
          path="/app"
          element={
            <PrivateRoute>
              <AppShell />
            </PrivateRoute>
          }
        >
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="cashflow" element={<CashflowPage />} />
          <Route path="spending" element={<SpendingPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="recall" element={<RecallPage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
