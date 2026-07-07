const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "/api").replace(/\/$/, "");

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ========== 数据转换层：后端格式 → 前端期望格式 ==========

function transformIndices(indices: any[]): any[] {
  if (!Array.isArray(indices)) return [];
  return indices.map((idx) => ({
    symbol: idx.code || idx.symbol || "",
    name: idx.name || "",
    price: idx.close || idx.price || 0,
    change: idx.change || 0,
    change_percent: idx.change_pct || idx.change_percent || 0,
    volume: idx.volume || 0,
  }));
}

function transformSectors(sectors: any[]): any[] {
  if (!Array.isArray(sectors)) return [];
  return sectors.map((s) => ({
    name: s.name || "",
    change_percent: s.change_pct || s.change_percent || 0,
    volume: s.volume || 0,
    leading_stocks: s.leading_stocks || [],
    net_inflow: s.net_inflow || 0,
  }));
}

function transformHotTopics(topics: any[]): string[] {
  if (!Array.isArray(topics)) return [];
  return topics.map((t) => (typeof t === "string" ? t : t.name || "")).filter(Boolean);
}

function transformFundFlow(flow: any): any {
  if (!flow) return { north_bound: 0, south_bound: 0, main_force: 0 };
  return {
    north_bound: flow.northbound_inflow || flow.north_bound || 0,
    south_bound: flow.southbound_inflow || flow.south_bound || 0,
    main_force: flow.main_inflow || flow.main_force || 0,
  };
}

function transformNews(news: any[]): any[] {
  if (!Array.isArray(news)) return [];
  return news.map((n, i) => ({
    id: n.id || i,
    title: n.title || "",
    source: n.source || "",
    published_at: n.published_at || n.date || new Date().toISOString(),
    summary: n.summary || n.title || "",
    tags: n.tags || [],
    sentiment: n.sentiment || "neutral",
    category: n.category || "",
    impact: n.impact || "",
  }));
}

function getSentimentLabel(score: number): string {
  if (score > 60) return "Bullish";
  if (score < 40) return "Bearish";
  return "Neutral";
}

// ========== Auth ==========

export function login(credentials: { username: string; password: string }) {
  return fetchApi<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function register(data: {
  username: string;
  email: string;
  password: string;
  full_name: string;
}) {
  return fetchApi<{ message: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getMe() {
  return fetchApi<{ id: string; username: string; email: string; full_name: string }>("/auth/me");
}

// ========== Dashboard & Market (with data transformation) ==========

export async function getDashboard() {
  const raw = await fetchApi<any>("/dashboard");
  const mo = raw.market_overview || {};
  return {
    date: raw.date || "",
    market_status: raw.market_status || "closed",
    market_overview: {
      date: mo.date || raw.date || "",
      market: mo.market || "A",
      indices: transformIndices(mo.indices || []),
      sectors: transformSectors(mo.sectors_up || mo.sectors || []),
      sentiment: mo.sentiment_score || mo.sentiment || 50,
      sentiment_label: getSentimentLabel(mo.sentiment_score || mo.sentiment || 50),
      hot_topics: transformHotTopics(mo.hot_topics || []),
      data_source: mo.data_source || "mock",
      up_count: mo.up_count || 0,
      down_count: mo.down_count || 0,
    },
    ai_summary: raw.ai_summary || null,
    watchlist_summary: raw.watchlist_summary || null,
    portfolio_summary: raw.portfolio_summary || null,
    tomorrow_watchlist: raw.tomorrow_watchlist || [],
  };
}

export async function getMarketOverview() {
  const raw = await fetchApi<any>("/market/overview");
  return {
    indices: transformIndices(raw.indices || []),
    sectors: transformSectors(raw.sectors || raw.sectors_up || []),
    sentiment: raw.sentiment_score || raw.sentiment || 50,
    sentiment_label: getSentimentLabel(raw.sentiment_score || raw.sentiment || 50),
    hot_topics: transformHotTopics(raw.hot_topics || []),
    fund_flow: transformFundFlow(raw.fund_flow || raw),
  };
}

export async function getIndices() {
  const raw = await fetchApi<any[]>("/market/indices");
  return transformIndices(raw || []);
}

export async function getSectors() {
  const raw = await fetchApi<any[]>("/market/sectors");
  return transformSectors(raw || []);
}

export async function getHotTopics() {
  const raw = await fetchApi<any[]>("/market/hot-topics");
  return transformHotTopics(raw || []);
}

export async function getNews() {
  const raw = await fetchApi<any[]>("/market/news");
  return transformNews(raw || []);
}

// Watchlist
export function getWatchlist() {
  return fetchApi<any[]>("/watchlist/");
}

export function addWatchlist(data: { ticker: string; note?: string; target_price?: number; alert_price?: number }) {
  return fetchApi<any>("/watchlist/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function removeWatchlist(id: string) {
  return fetchApi<void>(`/watchlist/${id}`, {
    method: "DELETE",
  });
}

// Portfolio
export function getPortfolio() {
  return fetchApi<any[]>("/portfolio/");
}

export function getPortfolioSummary() {
  return fetchApi<any>("/portfolio/summary");
}

export function addPortfolio(data: {
  ticker: string;
  quantity: number;
  avg_cost: number;
  sector?: string;
}) {
  return fetchApi<any>("/portfolio/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deletePortfolio(id: string) {
  return fetchApi<void>(`/portfolio/${id}`, {
    method: "DELETE",
  });
}

// Journal
export function getJournals() {
  return fetchApi<any[]>("/journal/");
}

export function createJournal(data: {
  date: string;
  ticker: string;
  action: string;
  price: number;
  quantity: number;
  reason: string;
  thesis: string;
  risk_assessment: string;
  emotion: string;
}) {
  return fetchApi<any>("/journal/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deleteJournal(id: string) {
  return fetchApi<void>(`/journal/${id}`, {
    method: "DELETE",
  });
}

// Asset Allocation
export function getAssetAllocations() {
  return fetchApi<any[]>("/assets/");
}

export function addAllocation(data: {
  category?: string;
  asset_type?: string;
  asset_name?: string;
  current_percent?: number;
  target_percent?: number;
  target_ratio?: number;
  amount: number;
  currency?: string;
  liquidity_level?: string;
  risk_level?: string;
}) {
  // Map frontend field names to backend field names
  const backendData: any = {
    asset_type: data.asset_type || data.category || "",
    asset_name: data.asset_name || data.category || "",
    amount: data.amount || 0,
    currency: data.currency || "CNY",
    liquidity_level: data.liquidity_level || "medium",
    risk_level: data.risk_level || "medium",
    target_ratio: data.target_ratio || data.target_percent || 0,
  };
  return fetchApi<any>("/assets/", {
    method: "POST",
    body: JSON.stringify(backendData),
  });
}

// AI
export function aiChat(question: string) {
  return fetchApi<{ answer: string }>("/ai/chat", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function analyzeAnnouncement(content: string) {
  return fetchApi<{ analysis: string }>("/ai/analyze-announcement", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function generateDailyReview() {
  return fetchApi<{ review: string }>("/ai/daily-market-review", {
    method: "POST",
  });
}

export function generateStockReview(ticker: string) {
  return fetchApi<{ review: string }>(`/ai/stock-review/${ticker}`, {
    method: "POST",
  });
}
