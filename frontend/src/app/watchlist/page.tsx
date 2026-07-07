"use client";

import React, { useEffect, useState } from "react";
import { getWatchlist, addWatchlist, removeWatchlist, generateStockReview } from "@/lib/api";
import { cn, formatNumber, formatPercent } from "@/lib/utils";
import {
  Loader2,
  Plus,
  Trash2,
  Bot,
  Search,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

export default function WatchlistPage() {
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tickerInput, setTickerInput] = useState("");
  const [adding, setAdding] = useState(false);
  const [reviewLoading, setReviewLoading] = useState<string | null>(null);
  const [reviewResult, setReviewResult] = useState<string | null>(null);

  const fetchWatchlist = async () => {
    try {
      const data = await getWatchlist();
      setWatchlist(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tickerInput.trim()) return;
    setAdding(true);
    try {
      await addWatchlist({ ticker: tickerInput.trim().toUpperCase() });
      setTickerInput("");
      await fetchWatchlist();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (id: string) => {
    try {
      await removeWatchlist(id);
      await fetchWatchlist();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleReview = async (ticker: string) => {
    setReviewLoading(ticker);
    setReviewResult(null);
    try {
      const res = await generateStockReview(ticker);
      setReviewResult(res.review);
    } catch (err: any) {
      setReviewResult(`Error: ${err.message}`);
    } finally {
      setReviewLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Watchlist</h1>

      {/* Add Form */}
      <form onSubmit={handleAdd} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value)}
            placeholder="Enter stock ticker (e.g. 000001)"
            className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <button
          type="submit"
          disabled={adding || !tickerInput.trim()}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          Add
        </button>
      </form>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Watchlist Table */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="px-4 py-2 text-left font-medium">Ticker</th>
              <th className="px-4 py-2 text-left font-medium hidden sm:table-cell">Name</th>
              <th className="px-4 py-2 text-right font-medium">Price</th>
              <th className="px-4 py-2 text-right font-medium">Change</th>
              <th className="px-4 py-2 text-right font-medium hidden md:table-cell">Volume</th>
              <th className="px-4 py-2 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {watchlist.map((item) => (
              <tr key={item.id} className="border-t border-border hover:bg-muted/50">
                <td className="px-4 py-2 font-semibold">{item.ticker}</td>
                <td className="px-4 py-2 text-muted-foreground hidden sm:table-cell">{item.name}</td>
                <td className="px-4 py-2 text-right font-medium">{formatNumber(item.price)}</td>
                <td className="px-4 py-2 text-right">
                  <span className={cn("inline-flex items-center gap-1 font-bold", item.change_percent > 0 ? "text-up" : item.change_percent < 0 ? "text-down" : "text-neutral")}>
                    {item.change_percent > 0 ? <TrendingUp className="h-3 w-3" /> : item.change_percent < 0 ? <TrendingDown className="h-3 w-3" /> : null}
                    {formatPercent(item.change_percent)}
                  </span>
                </td>
                <td className="px-4 py-2 text-right text-muted-foreground hidden md:table-cell">
                  {formatNumber(item.volume, 0)}
                </td>
                <td className="px-4 py-2 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => handleReview(item.ticker)}
                      disabled={reviewLoading === item.ticker}
                      className="inline-flex items-center gap-1 rounded-md bg-accent px-2 py-1 text-xs font-medium text-accent-foreground hover:bg-accent/80 disabled:opacity-50"
                    >
                      {reviewLoading === item.ticker ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Bot className="h-3 w-3" />
                      )}
                      AI Review
                    </button>
                    <button
                      onClick={() => handleRemove(item.id)}
                      className="inline-flex items-center rounded-md p-1.5 text-muted-foreground hover:bg-destructive hover:text-destructive-foreground"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {watchlist.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                  Your watchlist is empty. Add stocks to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Review Result */}
      {reviewResult && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            AI Stock Review
          </h3>
          <p className="text-sm whitespace-pre-wrap text-foreground">{reviewResult}</p>
          <button
            onClick={() => setReviewResult(null)}
            className="mt-3 text-xs text-muted-foreground hover:text-foreground underline"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
