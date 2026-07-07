"use client";

import React, { useEffect, useState } from "react";
import { getPortfolio, getPortfolioSummary, addPortfolio, deletePortfolio } from "@/lib/api";
import { cn, formatNumber, formatPercent, getRiskColor } from "@/lib/utils";
import {
  Loader2,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Wallet,
  BarChart3,
  RefreshCw,
} from "lucide-react";

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const [formData, setFormData] = useState({
    ticker: "",
    quantity: "",
    avg_cost: "",
    sector: "",
  });

  const fetchData = async () => {
    try {
      const [port, sum] = await Promise.all([getPortfolio(), getPortfolioSummary()]);
      setPortfolio(port);
      setSummary(sum);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.ticker.trim() || !formData.quantity || !formData.avg_cost) return;
    setAdding(true);
    try {
      await addPortfolio({
        ticker: formData.ticker.trim().toUpperCase(),
        quantity: Number(formData.quantity),
        avg_cost: Number(formData.avg_cost),
        sector: formData.sector || undefined,
      });
      setFormData({ ticker: "", quantity: "", avg_cost: "", sector: "" });
      setShowForm(false);
      await fetchData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deletePortfolio(id);
      await fetchData();
    } catch (err: any) {
      setError(err.message);
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        <button
          onClick={() => setShowForm((p) => !p)}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Add Holding
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Wallet className="h-4 w-4" />
              <span className="text-xs font-medium">Total Value</span>
            </div>
            <p className="text-2xl font-bold">{formatNumber(summary.total_value)}</p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <BarChart3 className="h-4 w-4" />
              <span className="text-xs font-medium">Total P&L</span>
            </div>
            <p className={cn("text-2xl font-bold", summary.total_pnl >= 0 ? "text-up" : "text-down")}>
              {summary.total_pnl >= 0 ? "+" : ""}{formatNumber(summary.total_pnl)}
            </p>
            <p className={cn("text-xs font-bold", summary.total_pnl_percent >= 0 ? "text-up" : "text-down")}>
              {formatPercent(summary.total_pnl_percent)}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs font-medium">Win / Loss</span>
            </div>
            <p className="text-2xl font-bold">
              <span className="text-up">{summary.win_count}</span>
              <span className="text-muted-foreground text-lg mx-1">/</span>
              <span className="text-down">{summary.loss_count}</span>
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-xs font-medium">Risk Level</span>
            </div>
            <p className={cn("text-2xl font-bold capitalize", getRiskColor(summary.risk_level))}>
              {summary.risk_level}
            </p>
          </div>
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <form onSubmit={handleAdd} className="rounded-lg border border-border bg-card p-4 space-y-3">
          <h3 className="text-sm font-semibold">Add New Holding</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <input
              type="text"
              placeholder="Ticker"
              value={formData.ticker}
              onChange={(e) => setFormData((p) => ({ ...p, ticker: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              required
            />
            <input
              type="number"
              placeholder="Quantity"
              value={formData.quantity}
              onChange={(e) => setFormData((p) => ({ ...p, quantity: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Avg Cost"
              value={formData.avg_cost}
              onChange={(e) => setFormData((p) => ({ ...p, avg_cost: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              required
            />
            <input
              type="text"
              placeholder="Sector (optional)"
              value={formData.sector}
              onChange={(e) => setFormData((p) => ({ ...p, sector: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={adding}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Save
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Holdings Table */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="px-4 py-2 text-left font-medium">Ticker</th>
              <th className="px-4 py-2 text-right font-medium">Qty</th>
              <th className="px-4 py-2 text-right font-medium hidden sm:table-cell">Avg Cost</th>
              <th className="px-4 py-2 text-right font-medium">Price</th>
              <th className="px-4 py-2 text-right font-medium hidden md:table-cell">Value</th>
              <th className="px-4 py-2 text-right font-medium">P&L</th>
              <th className="px-4 py-2 text-right font-medium hidden lg:table-cell">Weight</th>
              <th className="px-4 py-2 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.map((item) => (
              <tr key={item.id} className="border-t border-border hover:bg-muted/50">
                <td className="px-4 py-2">
                  <div className="font-semibold">{item.ticker}</div>
                  <div className="text-xs text-muted-foreground">{item.name}</div>
                </td>
                <td className="px-4 py-2 text-right">{formatNumber(item.quantity, 0)}</td>
                <td className="px-4 py-2 text-right text-muted-foreground hidden sm:table-cell">{formatNumber(item.avg_cost)}</td>
                <td className="px-4 py-2 text-right font-medium">{formatNumber(item.current_price)}</td>
                <td className="px-4 py-2 text-right hidden md:table-cell">{formatNumber(item.market_value)}</td>
                <td className="px-4 py-2 text-right">
                  <span className={cn("font-bold", item.unrealized_pnl >= 0 ? "text-up" : "text-down")}>
                    {formatNumber(item.unrealized_pnl)}
                  </span>
                  <span className={cn("block text-xs font-bold", item.unrealized_pnl_percent >= 0 ? "text-up" : "text-down")}>
                    {formatPercent(item.unrealized_pnl_percent)}
                  </span>
                </td>
                <td className="px-4 py-2 text-right hidden lg:table-cell">{formatPercent(item.weight)}</td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="inline-flex items-center rounded-md p-1.5 text-muted-foreground hover:bg-destructive hover:text-destructive-foreground"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
            ))}
            {portfolio.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                  No holdings yet. Add your first holding above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Risk Analysis */}
      {summary?.sector_allocation && Object.keys(summary.sector_allocation).length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            Sector Allocation
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(summary.sector_allocation).map(([sector, weight]: [string, any]) => (
              <div key={sector} className="rounded-md bg-muted p-3">
                <p className="text-xs text-muted-foreground">{sector}</p>
                <p className="text-lg font-bold">{formatPercent(Number(weight))}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rebalance Suggestions */}
      {portfolio.length > 0 && summary && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
            Rebalance Suggestions
          </h2>
          <p className="text-sm text-muted-foreground">
            Based on your current allocation, consider reviewing positions with weight over 25% to reduce concentration risk.
            {portfolio.some((p: any) => p.weight > 25) && (
              <span className="block mt-2 text-up font-medium">
                Alert: You have positions exceeding 25% portfolio weight.
              </span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}
