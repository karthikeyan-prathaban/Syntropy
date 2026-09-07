import axios from "axios";

export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  }
  return err instanceof Error ? err.message : "Request failed";
}

const api = axios.create({ baseURL: "/api" });

// Attach JWT token to every request if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("syntropy_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      const isAuthRoute = err.config?.url?.includes("/auth/");
      if (!isAuthRoute) {
        localStorage.removeItem("syntropy_token");
        localStorage.removeItem("syntropy_user");
        window.location.href = "/";
      }
    }
    return Promise.reject(err);
  }
);

// ── Types ──────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  name: string;
  mobile: string;
  vua: string;
  email?: string;
  avatar_initials?: string;
  created_at?: string;
}

export interface DashboardData {
  user: User;
  total_balance: number;
  health_score: number;
  total_income: number;
  total_expense: number;
  savings_rate: number;
  category_breakdown: { category: string; amount: number; percentage: number; count?: number }[];
  monthly_trend: { month: string; income: number; expense: number }[];
  recommendations: { title: string; description: string; priority: string; saving_potential?: number }[];
  recent_transactions: Transaction[];
  consent_status: string | null;
  accounts: BankAccount[];
}

export interface Transaction {
  id: number;
  txn_id: string;
  amount: number;
  txn_type: string;
  narration: string;
  mode: string;
  category: string;
  transaction_timestamp: string;
  balance_after: number | null;
  masked_acc_number: string | null;
}

export interface BankAccount {
  id: number;
  masked_acc_number: string;
  account_type: string;
  current_balance: number;
  currency: string;
  fip_id?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ── Auth ───────────────────────────────────────────────────────────────────

export async function signup(name: string, email: string, mobile: string, password: string) {
  const { data } = await api.post<AuthResponse>("/auth/signup", { name, email, mobile, password });
  return data;
}

export async function login(email: string, password: string) {
  const { data } = await api.post<AuthResponse>("/auth/login", { email, password });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

// ── Legacy / Demo ──────────────────────────────────────────────────────────

export async function createUser(name: string, mobile: string) {
  const { data } = await api.post<User>("/users", { name, mobile });
  return data;
}

export async function demoLogin(name: string, mobile: string) {
  const { data } = await api.post<AuthResponse>(`/auth/demo-login?name=${encodeURIComponent(name)}&mobile=${mobile}`);
  return data;
}

// ── Consent ────────────────────────────────────────────────────────────────

export async function createConsent() {
  const { data } = await api.post<{ request_id: string; consent_url: string; status: string }>(
    `/consent/create`
  );
  return data;
}

export async function createConsentForUser(userId: number) {
  const { data } = await api.post<{ request_id: string; consent_url: string; status: string }>(
    `/consent/create-for-user?user_id=${userId}`
  );
  return data;
}

export async function getConsentStatus(requestId: string) {
  const { data } = await api.get<{ request_id: string; status: string; consent_id: string | null }>(
    `/consent/${requestId}/status`
  );
  return data;
}

export async function fetchFinancialData(requestId: string) {
  const { data } = await api.post(`/consent/${requestId}/fetch`);
  return data;
}

// ── Dashboard ──────────────────────────────────────────────────────────────

export async function getDashboard(userId: number) {
  const { data } = await api.get<DashboardData>(`/dashboard/${userId}`);
  return data;
}

export async function getMyDashboard() {
  const { data } = await api.get<DashboardData>(`/dashboard`);
  return data;
}

export async function getMyTransactions(params?: { category?: string; txn_type?: string; limit?: number }) {
  const { data } = await api.get<Transaction[]>("/transactions", { params });
  return data;
}

export async function pingSetu() {
  const { data } = await api.get("/setu/ping");
  return data;
}

export async function loadMockData(userId: number) {
  const { data } = await api.post(`/mock/load/${userId}`);
  return data;
}
