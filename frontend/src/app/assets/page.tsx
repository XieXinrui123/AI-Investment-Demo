"use client";

import React, { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { getAssetAllocations, addAllocation } from "@/lib/api";
import { cn, formatNumber, formatPercent } from "@/lib/utils";
import {
  Loader2,
  Plus,
  Bot,
  PieChart as PieChartIcon,
  Target,
  AlertTriangle,
} from "lucide-react";

const COLORS = ["#ef4444", "#22c55e", "#3b82f6", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];

export default function AssetsPage() {
  const [allocations, setAllocations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [formData, setFormData] = useState({
    category: "",
    current_percent: "",
    target_percent: "",
    amount: "",
  });

  const fetchAllocations = async () => {
    try {
      const data = await getAssetAllocations();
      setAllocations(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllocations();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      await addAllocation({
        category: formData.category.trim(),
        current_percent: Number(formData.current_percent) || 0,
        target_percent: Number(formData.target_percent) || 0,
        amount: Number(formData.amount) || 0,
      });
      setFormData({ category: "", current_percent: "", target_percent: "", amount: "" });
      setShowForm(false);
      await fetchAllocations();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleAIAnalysis = async () => {
    setAiLoading(true);
    setAiAnalysis(null);
    try {
      await new Promise((r) => setTimeout(r, 1500));
      const totalCurrent = allocations.reduce((sum, a) => sum + a.current_percent, 0);
      const totalTarget = allocations.reduce((sum, a) => sum + a.target_percent, 0);
      const deviations = allocations
        .filter((a) => Math.abs(a.current_percent - a.target_percent) > 5)
        .map((a) => `${a.category}: ${formatPercent(a.current_percent - a.target_percent)}`);

      setAiAnalysis(
        `Asset Allocation Analysis:\n\n` +
        `Total Current Allocation: ${formatPercent(totalCurrent)}\n` +
        `Total Target Allocation: ${formatPercent(totalTarget)}\n\n` +
        `Significant Deviations (>5%):\n${deviations.length > 0 ? deviations.join("\n") : "None - allocation is well balanced."}\n\n` +
        `Suggestion: Consider rebalancing towards target weights to maintain your desired risk profile.`
      );
    } catch (err: any) {
      setAiAnalysis(`Error: ${err.message}`);
    } finally {
      setAiLoading(false);
    }
  };

  const chartData = allocations.map((a, idx) => ({
    name: a.category,
    value: a.current_percent,
    color: COLORS[idx % COLORS.length],
  }));

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
        <h1 className="text-2xl font-bold">Asset Allocation</h1>
        <div className="flex gap-2">
          <button
            onClick={handleAIAnalysis}
            disabled={aiLoading || allocations.length === 0}
            className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground hover:bg-accent/80 disabled:opacity-50"
          >
            {aiLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
            AI Analysis
          </button>
          <button
            onClick={() => setShowForm((p) => !p)}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Add
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {/* AI Analysis Result */}
      {aiAnalysis && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            AI Allocation Analysis
          </h3>
          <p className="text-sm whitespace-pre-wrap text-foreground">{aiAnalysis}</p>
          <button
            onClick={() => setAiAnalysis(null)}
            className="mt-3 text-xs text-muted-foreground hover:text-foreground underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <form onSubmit={handleAdd} className="rounded-lg border border-border bg-card p-4 space-y-3">
          <h3 className="text-sm font-semibold">Add Allocation</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <input
              type="text"
              placeholder="Category (e.g. Stocks)"
              value={formData.category}
              onChange={(e) => setFormData((p) => ({ ...p, category: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              required
            />
            <input
              type="number"
              step="0.1"
              placeholder="Current %"
              value={formData.current_percent}
              onChange={(e) => setFormData((p) => ({ ...p, current_percent: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              required
            />
            <input
              type="number"
              step="0.1"
              placeholder="Target %"
              value={formData.target_percent}
              onChange={(e) => setFormData((p) => ({ ...p, target_percent: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Amount"
              value={formData.amount}
              onChange={(e) => setFormData((p) => ({ ...p, amount: e.target.value }))}
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <PieChartIcon className="h-4 w-4 text-muted-foreground" />
            Current Allocation
          </h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => formatPercent(value)}
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "0.5rem",
                    fontSize: "0.75rem",
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[300px] items-center justify-center text-muted-foreground text-sm">
              No allocation data. Add items to see the chart.
            </div>
          )}
        </div>

        {/* Target vs Current Comparison */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
            <Target className="h-4 w-4 text-muted-foreground" />
            Target vs Current
          </h2>
          <div className="space-y-3">
            {allocations.map((item) => {
              const diff = item.current_percent - item.target_percent;
              return (
                <div key={item.id} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{item.category}</span>
                    <span className="text-muted-foreground">
                      {formatPercent(item.current_percent)} / {formatPercent(item.target_percent)}
                    </span>
                  </div>
                  <div className="relative h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="absolute top-0 left-0 h-full rounded-full bg-primary"
                      style={{ width: `${Math.min(item.current_percent, 100)}%` }}
                    />
                    <div
                      className="absolute top-0 h-full w-0.5 bg-foreground/50"
                      style={{ left: `${Math.min(item.target_percent, 100)}%` }}
                    />
                  </div>
                  {Math.abs(diff) > 5 && (
                    <p className={cn("text-xs", diff > 0 ? "text-up" : "text-down")}>
                      {diff > 0 ? "Overweight" : "Underweight"} by {formatPercent(Math.abs(diff))}
                    </p>
                  )}
                </div>
              );
            })}
            {allocations.length === 0 && (
              <p className="text-center text-muted-foreground py-8 text-sm">No allocation data available.</p>
            )}
          </div>
        </div>
      </div>

      {/* Allocation Table */}
      {allocations.length > 0 && (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Category</th>
                <th className="px-4 py-2 text-right font-medium">Current %</th>
                <th className="px-4 py-2 text-right font-medium">Target %</th>
                <th className="px-4 py-2 text-right font-medium">Diff</th>
                <th className="px-4 py-2 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {allocations.map((item) => {
                const diff = item.current_percent - item.target_percent;
                return (
                  <tr key={item.id} className="border-t border-border hover:bg-muted/50">
                    <td className="px-4 py-2 font-medium">{item.category}</td>
                    <td className="px-4 py-2 text-right">{formatPercent(item.current_percent)}</td>
                    <td className="px-4 py-2 text-right text-muted-foreground">{formatPercent(item.target_percent)}</td>
                    <td className={cn("px-4 py-2 text-right font-bold", diff > 0 ? "text-up" : diff < 0 ? "text-down" : "text-neutral")}>
                      {diff > 0 ? "+" : ""}{formatPercent(diff)}
                    </td>
                    <td className="px-4 py-2 text-right">{formatNumber(item.amount)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
