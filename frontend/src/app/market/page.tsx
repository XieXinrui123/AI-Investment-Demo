"use client";

import React, { useEffect, useState } from "react";
import { getMarketOverview, getIndices, getSectors, getNews } from "@/lib/api";
import { cn, formatNumber, formatPercent, formatDate } from "@/lib/utils";
import {
  Loader2,
  TrendingUp,
  TrendingDown,
  Newspaper,
  ArrowUpDown,
  Activity,
  DollarSign,
} from "lucide-react";

type Tab = "indices" | "sectors" | "movers" | "fundflow" | "news";

export default function MarketPage() {
  const [activeTab, setActiveTab] = useState<Tab>("indices");
  const [overview, setOverview] = useState<any>(null);
  const [indices, setIndices] = useState<any[]>([]);
  const [sectors, setSectors] = useState<any[]>([]);
  const [news, setNews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sectorSort, setSectorSort] = useState<{ key: string; desc: boolean }>({
    key: "change_percent",
    desc: true,
  });
  const [newsFilter, setNewsFilter] = useState<string>("all");

  useEffect(() => {
    let mounted = true;
    Promise.all([getMarketOverview(), getIndices(), getSectors(), getNews()])
      .then(([ov, idx, sec, nws]) => {
        if (!mounted) return;
        setOverview(ov);
        setIndices(idx);
        setSectors(sec);
        setNews(nws);
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message);
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const tabs: { id: Tab; label: string }[] = [
    { id: "indices", label: "Indices" },
    { id: "sectors", label: "Sectors" },
    { id: "movers", label: "Movers" },
    { id: "fundflow", label: "Fund Flow" },
    { id: "news", label: "News" },
  ];

  const sortedSectors = [...sectors].sort((a, b) => {
    const aVal = a[sectorSort.key] ?? 0;
    const bVal = b[sectorSort.key] ?? 0;
    return sectorSort.desc ? bVal - aVal : aVal - bVal;
  });

  const filteredNews = newsFilter === "all" ? news : news.filter((n) => n.sentiment === newsFilter);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-96 items-center justify-center text-destructive">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Market Overview</h1>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Indices Tab */}
      {activeTab === "indices" && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Name</th>
                <th className="px-4 py-2 text-right font-medium">Price</th>
                <th className="px-4 py-2 text-right font-medium">Change</th>
                <th className="px-4 py-2 text-right font-medium">Change %</th>
                <th className="px-4 py-2 text-right font-medium hidden sm:table-cell">Volume</th>
              </tr>
            </thead>
            <tbody>
              {indices.map((idx) => (
                <tr key={idx.symbol} className="border-t border-border hover:bg-muted/50">
                  <td className="px-4 py-2">
                    <div className="font-medium">{idx.name}</div>
                    <div className="text-xs text-muted-foreground">{idx.symbol}</div>
                  </td>
                  <td className="px-4 py-2 text-right font-medium">{formatNumber(idx.price)}</td>
                  <td className={cn("px-4 py-2 text-right font-medium", idx.change > 0 ? "text-up" : idx.change < 0 ? "text-down" : "text-neutral")}>
                    {idx.change > 0 ? "+" : ""}{formatNumber(idx.change)}
                  </td>
                  <td className={cn("px-4 py-2 text-right font-bold", idx.change_percent > 0 ? "text-up" : idx.change_percent < 0 ? "text-down" : "text-neutral")}>
                    {formatPercent(idx.change_percent)}
                  </td>
                  <td className="px-4 py-2 text-right text-muted-foreground hidden sm:table-cell">
                    {formatNumber(idx.volume, 0)}
                  </td>
                </tr>
              ))}
              {indices.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                    No index data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Sectors Tab */}
      {activeTab === "sectors" && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Sector</th>
                <th
                  className="px-4 py-2 text-right font-medium cursor-pointer hover:text-foreground"
                  onClick={() =>
                    setSectorSort({ key: "change_percent", desc: sectorSort.key === "change_percent" ? !sectorSort.desc : true })
                  }
                >
                  <span className="inline-flex items-center gap-1">
                    Change % <ArrowUpDown className="h-3 w-3" />
                  </span>
                </th>
                <th className="px-4 py-2 text-right font-medium hidden md:table-cell">Volume</th>
                <th className="px-4 py-2 text-left font-medium hidden lg:table-cell">Leading Stocks</th>
              </tr>
            </thead>
            <tbody>
              {sortedSectors.map((sector) => (
                <tr key={sector.name} className="border-t border-border hover:bg-muted/50">
                  <td className="px-4 py-2 font-medium">{sector.name}</td>
                  <td className={cn("px-4 py-2 text-right font-bold", sector.change_percent > 0 ? "text-up" : sector.change_percent < 0 ? "text-down" : "text-neutral")}>
                    {formatPercent(sector.change_percent)}
                  </td>
                  <td className="px-4 py-2 text-right text-muted-foreground hidden md:table-cell">
                    {formatNumber(sector.volume, 0)}
                  </td>
                  <td className="px-4 py-2 hidden lg:table-cell">
                    <div className="flex flex-wrap gap-1">
                      {sector.leading_stocks?.map((s: string) => (
                        <span key={s} className="rounded bg-secondary px-1.5 py-0.5 text-xs">
                          {s}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {sortedSectors.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                    No sector data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Movers Tab */}
      {activeTab === "movers" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-up">
              <TrendingUp className="h-4 w-4" /> Top Gainers
            </h3>
            {overview?.sectors?.slice(0, 5).map((s: any) => (
              <div key={s.name} className="flex justify-between py-1.5 border-b border-border/50 last:border-0">
                <span className="text-sm">{s.name}</span>
                <span className="text-sm font-bold text-up">{formatPercent(s.change_percent)}</span>
              </div>
            ))}
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-down">
              <TrendingDown className="h-4 w-4" /> Top Losers
            </h3>
            {[...(overview?.sectors || [])].sort((a, b) => a.change_percent - b.change_percent).slice(0, 5).map((s: any) => (
              <div key={s.name} className="flex justify-between py-1.5 border-b border-border/50 last:border-0">
                <span className="text-sm">{s.name}</span>
                <span className="text-sm font-bold text-down">{formatPercent(s.change_percent)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fund Flow Tab */}
      {activeTab === "fundflow" && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-lg border border-border bg-card p-4 text-center">
            <DollarSign className="h-6 w-6 mx-auto mb-2 text-blue-500" />
            <p className="text-xs text-muted-foreground">North Bound</p>
            <p className={cn("text-xl font-bold", (overview?.fund_flow?.north_bound || 0) >= 0 ? "text-up" : "text-down")}>
              {formatNumber(overview?.fund_flow?.north_bound || 0, 0)}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4 text-center">
            <DollarSign className="h-6 w-6 mx-auto mb-2 text-purple-500" />
            <p className="text-xs text-muted-foreground">South Bound</p>
            <p className={cn("text-xl font-bold", (overview?.fund_flow?.south_bound || 0) >= 0 ? "text-up" : "text-down")}>
              {formatNumber(overview?.fund_flow?.south_bound || 0, 0)}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4 text-center">
            <Activity className="h-6 w-6 mx-auto mb-2 text-orange-500" />
            <p className="text-xs text-muted-foreground">Main Force</p>
            <p className={cn("text-xl font-bold", (overview?.fund_flow?.main_force || 0) >= 0 ? "text-up" : "text-down")}>
              {formatNumber(overview?.fund_flow?.main_force || 0, 0)}
            </p>
          </div>
        </div>
      )}

      {/* News Tab */}
      {activeTab === "news" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            {["all", "positive", "negative", "neutral"].map((f) => (
              <button
                key={f}
                onClick={() => setNewsFilter(f)}
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium capitalize",
                  newsFilter === f
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-accent"
                )}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="space-y-3">
            {filteredNews.map((item) => (
              <div key={item.id} className="rounded-lg border border-border bg-card p-4 hover:shadow-sm transition-shadow">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold">{item.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1">{item.source} &middot; {formatDate(item.published_at)}</p>
                    <p className="text-sm text-foreground mt-2">{item.summary}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {item.tags?.map((tag: string) => (
                        <span key={tag} className="rounded bg-secondary px-1.5 py-0.5 text-[10px] text-secondary-foreground">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold capitalize",
                      item.sentiment === "positive"
                        ? "bg-red-100 text-red-700 dark:bg-red-900/30"
                        : item.sentiment === "negative"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30"
                        : "bg-gray-100 text-gray-700 dark:bg-gray-800"
                    )}
                  >
                    {item.sentiment}
                  </span>
                </div>
              </div>
            ))}
            {filteredNews.length === 0 && (
              <p className="text-center text-muted-foreground py-8 text-sm">No news available</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
