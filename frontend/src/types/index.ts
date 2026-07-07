export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface Stock {
  ticker: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap?: number;
  pe_ratio?: number;
  pb_ratio?: number;
}

export interface IndexData {
  name: string;
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  turnover: number;
}

export interface SectorData {
  name: string;
  change_percent: number;
  leading_stocks: string[];
  volume: number;
  turnover: number;
}

export interface WatchlistItem {
  id: string;
  ticker: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  added_at: string;
  notes?: string;
}

export interface PortfolioItem {
  id: string;
  ticker: string;
  name: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  weight: number;
  sector?: string;
  added_at: string;
}

export interface JournalEntry {
  id: string;
  date: string;
  ticker: string;
  action: 'buy' | 'sell' | 'hold' | 'watch' | 'review';
  price: number;
  quantity: number;
  reason: string;
  thesis: string;
  risk_assessment: string;
  emotion: string;
  created_at: string;
}

export interface AssetAllocation {
  id: string;
  category: string;
  current_percent: number;
  target_percent: number;
  amount: number;
  color?: string;
}

export interface DailyReview {
  id: string;
  date: string;
  summary: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  sentiment_score: number;
  key_events: string[];
  market_commentary: string;
  portfolio_commentary?: string;
  tomorrow_watchlist: string[];
  created_at: string;
}

export interface NewsItem {
  id: string;
  title: string;
  source: string;
  url: string;
  summary: string;
  published_at: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  tags: string[];
}

export interface AIChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface MarketOverview {
  indices: IndexData[];
  sectors: SectorData[];
  sentiment: number;
  sentiment_label: string;
  hot_topics: string[];
  fund_flow: {
    north_bound: number;
    south_bound: number;
    main_force: number;
  };
}

export interface DashboardData {
  market_overview: MarketOverview;
  ai_summary: string;
  watchlist_summary?: {
    total_items: number;
    top_gainer: WatchlistItem | null;
    top_loser: WatchlistItem | null;
  };
  portfolio_summary?: {
    total_value: number;
    total_pnl: number;
    risk_level: 'low' | 'medium' | 'high';
  };
  tomorrow_watchlist: string[];
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  full_name: string;
}
