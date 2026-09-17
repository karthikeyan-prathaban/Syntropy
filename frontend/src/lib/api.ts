import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE
  ? `${import.meta.env.VITE_API_BASE}/api/v1`
  : "/api/v1";

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("novaa_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("novaa_token");
      localStorage.removeItem("novaa_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export type User = {
  id: number;
  name: string;
  mobile: string;
  vua: string;
  email?: string;
  avatar_initials?: string;
};

export type DashboardData = {
  user: User;
  total_balance: number;
  health_score: number;
  total_income: number;
  total_expense: number;
  savings_rate: number;
  category_breakdown: { category: string; amount: number; percentage: number; count: number }[];
  monthly_trend: { month: string; income: number; expense: number }[];
  recommendations: { title: string; description: string; priority: string; saving_potential: number }[];
  recent_transactions: Transaction[];
  consent_status: string | null;
  accounts: { id: number; masked_acc_number: string; account_type: string; current_balance: number; currency: string; fip_id?: string }[];
};

export type Transaction = {
  id: number;
  txn_id: string;
  amount: number;
  txn_type: string;
  narration: string;
  mode: string;
  category: string;
  transaction_timestamp: string;
  balance_after?: number;
  masked_acc_number?: string;
};

export const authApi = {
  login: (email: string, password: string) => api.post("/auth/login", { email, password }),
  signup: (data: { name: string; email: string; mobile: string; password: string }) =>
    api.post("/auth/signup", data),
  demoLogin: (name = "Demo User", mobile = "9876543210") =>
    api.post(`/auth/demo-login?name=${encodeURIComponent(name)}&mobile=${mobile}`),
  me: () => api.get<User>("/auth/me"),
};

export const dashboardApi = {
  get: () => api.get<DashboardData>("/dashboard"),
  loadMock: () => api.post("/mock/load"),
};

export const consentApi = {
  create: () => api.post("/consent/create"),
  status: (requestId: string) => api.get(`/consent/${requestId}/status`),
  fetch: (requestId: string) => api.post(`/consent/${requestId}/fetch`),
  revoke: (consentId: string) => api.post(`/consent/${consentId}/revoke`),
};

export const analyticsApi = {
  cashflow: () => api.get("/analytics/cashflow"),
  categories: () => api.get("/analytics/categories"),
  merchants: () => api.get("/analytics/merchants"),
  recurring: () => api.get("/analytics/recurring"),
  calendar: () => api.get("/analytics/calendar"),
  anomalies: () => api.get("/analytics/anomalies"),
  forecast: () => api.get("/analytics/forecast"),
};

export const transactionsApi = {
  list: (params?: { limit?: number; category?: string; txn_type?: string }) =>
    api.get<Transaction[]>("/transactions", { params }),
};

export const marketingApi = {
  waitlist: (email: string) => api.post("/waitlist", { email }),
  waitlistCount: () => api.get<{ count: number }>("/waitlist/count"),
};

export async function streamText(endpoint: string, body: object, onChunk: (text: string) => void) {
  const token = localStorage.getItem("novaa_token");
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  const reader = res.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    onChunk(decoder.decode(value));
  }
}
