"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import MarketCard from "@/components/MarketCard";
import { getDashboard } from "@/lib/api";
import { cn, formatDate, formatNumber, formatPercent, getRiskColor } from "@/lib/utils";
import {
  Loader2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Activity,
  Flame,
  Eye,
  ArrowRight,
  Calendar,
  Clock,
} from "lucide-react";

interface DashboardState {
  data: any;
  loading: boolean;
  error: string | null;
}

export default function DashboardPage() {
  const { isAuthenticated } = useAuth();
  const [state, setState] = useState<DashboardState>({ data: null, loading: true, error: null });

  useEffect(() => {
    let mounted = true;
    getDashboard()
      .then((data) => {
        if (mounted) setState({ data, loading: false, error: null });
      })
      .catch((err) => {
        if (mounted) setState({ data: null, loading: false, error: err.message });
      });
    return () => {
      mounted = false;
    };
  }, []);

  const isMarketOpen = () => {
    const now = new Date();
    const hour = now.getHours();
    const minute = now.getMinutes();
    const day = now.getDay();
    if (day === 0 || day === 6) return false;
    const time = hour * 60 + minute;
    return (time >= 570 && time <= 690) || (time >= 780 && time <= 900);
  };

  if (state.loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-2 text-destructive">
        <AlertTriangle className="h-8 w-8" />
        <p>Failed to load dashboard: {state.error}</p>
      </div>
    );
  }

  const { data } = state;
  const marketOpen = isMarketOpen();

  return (
    <div className="space-y-6">
      {/* Market Status Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg border border-border bg-card p-4">
        <div className="flex items-center gap-3">
          <Calendar className="h-5 w-5 text-muted-foreground" />
          <span className="text-sm font-medium">{formatDate(new Date().toISOString())}</span>
          <div className="flex items-center gap-1.5">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold",
                marketOpen
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400"
              )}
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", marketOpen ? "bg-green-500 animate-pulse" : "bg-gray-400")} />
              {marketOpen ? "Market Open" : "Market Closed"}
            </span>
          </div>
        </div>
      </div>

      {/* AI Summary Card */}
      {data?.ai_summary && (
        <div className="rounded-lg border border-border bg-gradient-to-r from-primary/5 to-accent/5 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-5 w-5 text-primary" />
            <h2 className="text-sm font-semibold">AI Market Summary</h2>
          </div>
          <p className="text-sm text-foreground leading-relaxed">{data.ai_summary}</p>
        </div>
      )}

      {/* Sentiment Gauge */}
      {data?.market_overview?.sentiment !== undefined && (
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              Market Sentiment
            </h2>
            <span
              className={cn(
                "text-xs font-bold px-2 py-0.5 rounded-full",
                data.market_overview.sentiment > 60
                  ? "bg-red-100 text-red-700 dark:bg-red-900/30"
                  : data.market_overview.sentiment < 40
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800"
              )}
            >
              {data.market_overview.sentiment_label}
            </span>
          </div>
          <div className="relative h-4 rounded-full bg-muted overflow-hidden">
            <div
              className={cn(
                "absolute top-0 left-0 h-full rounded-full transition-all",
                data.market_overview.sentiment > 60
                  ? "bg-up"
                  : data.market_overview.sentiment < 40
                  ? "bg-down"
                  : "bg-neutral"
              )}
              style={{ width: `${data.market_overview.sentiment}%` }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[10px] text-muted-foreground">Bearish</span>
            <span className="text-xs font-bold">{data.market_overview.sentiment}/100</span>
            <span className="text-[10px] text-muted-foreground">Bullish</span>
          </div>
        </div>
      )}

      {/* Index Performance Grid */}
      <div>
        <h2 className="text-lg font-bold mb-3">Index Performance</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {data?.market_overview?.indices?.map((index: any) => (
            <MarketCard
              key={index.symbol}
              title={index.name}
              subtitle={index.symbol}
              price={index.price}
              change={index.change}
              changePercent={index.change_percent}
            />
          ))}
          {(!data?.market_overview?.indices || data.market_overview.indices.length === 0) && (
            <div className="col-span-full text-center py-8 text-muted-foreground text-sm">
              No index data available
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sector Leaders / Laggards */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            Sector Performance
          </h2>
          <div className="space-y-2">
            {data?.market_overview?.sectors?.slice(0, 8).map((sector: any) => (
              <div key={sector.name} className="flex items-center justify-between text-sm">
                <span className="font-medium">{sector.name}</span>
                <span
                  className={cn(
                    "font-bold",
                    sector.change_percent > 0 ? "text-up" : sector.change_percent < 0 ? "text-down" : "text-neutral"
                  )}
                >
                  {formatPercent(sector.change_percent)}
                </span>
              </div>
            ))}
            {(!data?.market_overview?.sectors || data.market_overview.sectors.length === 0) && (
              <p className="text-sm text-muted-foreground text-center py-4">No sector data available</p>
            )}
          </div>
        </div>

        {/* Hot Topics */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Flame className="h-4 w-4 text-orange-500" />
            Hot Topics
          </h2>
          <div className="flex flex-wrap gap-2">
            {data?.market_overview?.hot_topics?.map((topic: string, idx: number) => (
              <span
                key={idx}
                className="rounded-full bg-accent px-3 py-1 text-xs font-medium text-accent-foreground"
              >
                {topic}
              </span>
            ))}
            {(!data?.market_overview?.hot_topics || data.market_overview.hot_topics.length === 0) && (
              <p className="text-sm text-muted-foreground text-center py-4 w-full">No hot topics today</p>
            )}
          </div>
        </div>
      </div>

      {/* Watchlist Summary */}
      {isAuthenticated && data?.watchlist_summary && (
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <Eye className="h-4 w-4 text-muted-foreground" />
              Watchlist Summary
            </h2>
            <Link href="/watchlist" className="text-xs text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-md bg-muted p-3 text-center">
              <p className="text-xs text-muted-foreground">Total Stocks</p>
              <p className="text-xl font-bold">{data.watchlist_summary.total_items}</p>
            </div>
            {data.watchlist_summary.top_gainer && (
              <div className="rounded-md bg-red-50 dark:bg-red-950/20 p-3 text-center">
                <p className="text-xs text-muted-foreground">Top Gainer</p>
                <p className="text-sm font-bold">{data.watchlist_summary.top_gainer.ticker}</p>
                <p className="text-xs text-up font-bold">
                  {formatPercent(data.watchlist_summary.top_gainer.change_percent)}
                </p>
              </div>
            )}
            {data.watchlist_summary.top_loser && (
              <div className="rounded-md bg-green-50 dark:bg-green-950/20 p-3 text-center">
                <p className="text-xs text-muted-foreground">Top Loser</p>
                <p className="text-sm font-bold">{data.watchlist_summary.top_loser.ticker}</p>
                <p className="text-xs text-down font-bold">
                  {formatPercent(data.watchlist_summary.top_loser.change_percent)}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Portfolio Risk Warning */}
      {isAuthenticated && data?.portfolio_summary && (
        <div
          className={cn(
            "rounded-lg border p-4",
            data.portfolio_summary.risk_level === "high"
              ? "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/20"
              : data.portfolio_summary.risk_level === "medium"
              ? "border-yellow-200 bg-yellow-50 dark:border-yellow-900 dark:bg-yellow-950/20"
              : "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/20"
          )}
        >
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle
              className={cn(
                "h-5 w-5",
                getRiskColor(data.portfolio_summary.risk_level)
              )}
            />
            <h2 className="text-sm font-semibold">Portfolio Risk Alert</h2>
          </div>
          <p className="text-sm">
            Total Value: <span className="font-bold">{formatNumber(data.portfolio_summary.total_value)}</span>
            {" "}&middot;{" "}
            Total P&L:{" "}
            <span
              className={cn(
                "font-bold",
                data.portfolio_summary.total_pnl >= 0 ? "text-up" : "text-down"
              )}
            >
              {data.portfolio_summary.total_pnl >= 0 ? "+" : ""}
              {formatNumber(data.portfolio_summary.total_pnl)}
            </span>
            {" "}&middot;{" "}
            Risk Level:{" "}
            <span className={cn("font-bold capitalize", getRiskColor(data.portfolio_summary.risk_level))}>
              {data.portfolio_summary.risk_level}
            </span>
          </p>
        </div>
      )}

      {/* Tomorrow's Watchlist */}
      {(() => {
        const tw = data?.tomorrow_watchlist;
        const items = Array.isArray(tw) ? tw : (typeof tw === 'string' ? tw.split(/[、,;]/).filter(Boolean) : []);
        if (!items.length) return null;
        return (
          <div className="rounded-lg border border-border bg-card p-4">
            <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Eye className="h-4 w-4 text-muted-foreground" />
              明日关注
            </h2>
            <div className="flex flex-wrap gap-2">
              {items.map((item: string, idx: number) => (
                <Link key={idx} href="/watchlist" className="rounded-md bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground hover:bg-secondary/80">
                  {item.trim()}
                </Link>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
