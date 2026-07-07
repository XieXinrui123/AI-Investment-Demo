"use client";

import React, { useEffect, useState } from "react";
import { getJournals, createJournal, deleteJournal } from "@/lib/api";
import { cn, formatDate, formatNumber } from "@/lib/utils";
import {
  Loader2,
  Plus,
  Trash2,
  Bot,
  BookOpen,
  Filter,
} from "lucide-react";

const actions = ["buy", "sell", "hold", "watch", "review"] as const;

export default function JournalPage() {
  const [journals, setJournals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const [filterAction, setFilterAction] = useState<string>("all");
  const [aiReview, setAiReview] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split("T")[0],
    ticker: "",
    action: "buy",
    price: "",
    quantity: "",
    reason: "",
    thesis: "",
    risk_assessment: "",
    emotion: "",
  });

  const fetchJournals = async () => {
    try {
      const data = await getJournals();
      setJournals(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJournals();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      await createJournal({
        date: formData.date,
        ticker: formData.ticker.trim().toUpperCase(),
        action: formData.action,
        price: Number(formData.price) || 0,
        quantity: Number(formData.quantity) || 0,
        reason: formData.reason,
        thesis: formData.thesis,
        risk_assessment: formData.risk_assessment,
        emotion: formData.emotion,
      });
      setFormData({
        date: new Date().toISOString().split("T")[0],
        ticker: "",
        action: "buy",
        price: "",
        quantity: "",
        reason: "",
        thesis: "",
        risk_assessment: "",
        emotion: "",
      });
      setShowForm(false);
      await fetchJournals();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteJournal(id);
      await fetchJournals();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleAIReview = async () => {
    setAiLoading(true);
    setAiReview(null);
    try {
      // Simulate AI review based on journal entries
      await new Promise((r) => setTimeout(r, 1500));
      const buyCount = journals.filter((j) => j.action === "buy").length;
      const sellCount = journals.filter((j) => j.action === "sell").length;
      setAiReview(
        `Behavior Analysis Report:\n\n` +
        `Total Entries: ${journals.length}\n` +
        `Buy Actions: ${buyCount}\n` +
        `Sell Actions: ${sellCount}\n\n` +
        `Observation: Your trading frequency is ${journals.length > 20 ? "high" : "moderate"}. ` +
        `Consider reviewing entries with emotional tags to identify bias patterns. ` +
        `Maintaining a disciplined journal helps improve decision quality over time.`
      );
    } catch (err: any) {
      setAiReview(`Error: ${err.message}`);
    } finally {
      setAiLoading(false);
    }
  };

  const filteredJournals = filterAction === "all" ? journals : journals.filter((j) => j.action === filterAction);

  const actionColors: Record<string, string> = {
    buy: "bg-red-100 text-red-700 dark:bg-red-900/30",
    sell: "bg-green-100 text-green-700 dark:bg-green-900/30",
    hold: "bg-blue-100 text-blue-700 dark:bg-blue-900/30",
    watch: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30",
    review: "bg-purple-100 text-purple-700 dark:bg-purple-900/30",
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
        <h1 className="text-2xl font-bold">Investment Journal</h1>
        <div className="flex gap-2">
          <button
            onClick={handleAIReview}
            disabled={aiLoading || journals.length === 0}
            className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground hover:bg-accent/80 disabled:opacity-50"
          >
            {aiLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
            AI Review
          </button>
          <button
            onClick={() => setShowForm((p) => !p)}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Add Entry
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {/* AI Review Result */}
      {aiReview && (
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary" />
            AI Behavior Analysis
          </h3>
          <p className="text-sm whitespace-pre-wrap text-foreground">{aiReview}</p>
          <button
            onClick={() => setAiReview(null)}
            className="mt-3 text-xs text-muted-foreground hover:text-foreground underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <form onSubmit={handleAdd} className="rounded-lg border border-border bg-card p-4 space-y-3">
          <h3 className="text-sm font-semibold">New Journal Entry</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <input
              type="date"
              value={formData.date}
              onChange={(e) => setFormData((p) => ({ ...p, date: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              required
            />
            <input
              type="text"
              placeholder="Ticker"
              value={formData.ticker}
              onChange={(e) => setFormData((p) => ({ ...p, ticker: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              required
            />
            <select
              value={formData.action}
              onChange={(e) => setFormData((p) => ({ ...p, action: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {actions.map((a) => (
                <option key={a} value={a}>{a.toUpperCase()}</option>
              ))}
            </select>
            <input
              type="number"
              step="0.01"
              placeholder="Price"
              value={formData.price}
              onChange={(e) => setFormData((p) => ({ ...p, price: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <input
              type="number"
              placeholder="Quantity"
              value={formData.quantity}
              onChange={(e) => setFormData((p) => ({ ...p, quantity: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <input
              type="text"
              placeholder="Emotion"
              value={formData.emotion}
              onChange={(e) => setFormData((p) => ({ ...p, emotion: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <textarea
            placeholder="Reason for action"
            value={formData.reason}
            onChange={(e) => setFormData((p) => ({ ...p, reason: e.target.value }))}
            rows={2}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <textarea
            placeholder="Investment thesis"
            value={formData.thesis}
            onChange={(e) => setFormData((p) => ({ ...p, thesis: e.target.value }))}
            rows={2}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <textarea
            placeholder="Risk assessment"
            value={formData.risk_assessment}
            onChange={(e) => setFormData((p) => ({ ...p, risk_assessment: e.target.value }))}
            rows={2}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={adding}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Save Entry
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

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        >
          <option value="all">All Actions</option>
          {actions.map((a) => (
            <option key={a} value={a}>{a.toUpperCase()}</option>
          ))}
        </select>
      </div>

      {/* Journal Table */}
      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="px-4 py-2 text-left font-medium">Date</th>
              <th className="px-4 py-2 text-left font-medium">Ticker</th>
              <th className="px-4 py-2 text-left font-medium">Action</th>
              <th className="px-4 py-2 text-right font-medium hidden sm:table-cell">Price</th>
              <th className="px-4 py-2 text-right font-medium hidden sm:table-cell">Qty</th>
              <th className="px-4 py-2 text-left font-medium hidden lg:table-cell">Reason</th>
              <th className="px-4 py-2 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredJournals.map((entry) => (
              <tr key={entry.id} className="border-t border-border hover:bg-muted/50">
                <td className="px-4 py-2 text-muted-foreground">{formatDate(entry.date)}</td>
                <td className="px-4 py-2 font-semibold">{entry.ticker}</td>
                <td className="px-4 py-2">
                  <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold uppercase", actionColors[entry.action] || "bg-gray-100")}>
                    {entry.action}
                  </span>
                </td>
                <td className="px-4 py-2 text-right hidden sm:table-cell">{formatNumber(entry.price)}</td>
                <td className="px-4 py-2 text-right hidden sm:table-cell">{formatNumber(entry.quantity, 0)}</td>
                <td className="px-4 py-2 hidden lg:table-cell max-w-xs truncate">{entry.reason}</td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => handleDelete(entry.id)}
                    className="inline-flex items-center rounded-md p-1.5 text-muted-foreground hover:bg-destructive hover:text-destructive-foreground"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
            ))}
            {filteredJournals.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                  No journal entries found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
