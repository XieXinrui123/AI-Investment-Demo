"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  PieChart as PieChartRecharts,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { getAssetAllocations, addAllocation, deleteAllocation } from "@/lib/api";
import { cn, formatNumber, formatPercent } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import {
  AlertTriangle,
  Banknote,
  Briefcase,
  CalendarClock,
  Landmark,
  Loader2,
  PieChart as PieChartIcon,
  Plus,
  ShieldCheck,
  Target,
  Trash2,
  TrendingUp,
  Wallet,
} from "lucide-react";

const BUCKETS = [
  {
    id: "liquid",
    label: "流动钱",
    description: "现金、活期、货币基金，应对 6-12 个月支出",
    icon: Wallet,
    color: "#0ea5e9",
  },
  {
    id: "stable",
    label: "稳健钱",
    description: "债券、固收、低波动资产，承接 1-3 年目标",
    icon: Landmark,
    color: "#22c55e",
  },
  {
    id: "growth",
    label: "长期钱",
    description: "股票、指数、权益基金，服务 5 年以上增值",
    icon: TrendingUp,
    color: "#f59e0b",
  },
  {
    id: "protection",
    label: "保障钱",
    description: "保险、备用保障、风险缓冲，不追求收益",
    icon: ShieldCheck,
    color: "#8b5cf6",
  },
];

const CURRENCY_LABEL: Record<string, string> = {
  CNY: "人民币",
  USD: "美元",
  HKD: "港币",
};

function classifyBucket(assetType: string) {
  const type = assetType.toLowerCase();
  if (["liquid", "cash", "money_market"].includes(type)) return "liquid";
  if (["stable", "bond", "fixed_income"].includes(type)) return "stable";
  if (["protection", "insurance"].includes(type)) return "protection";
  return "growth";
}

function bucketMeta(bucketId: string) {
  return BUCKETS.find((bucket) => bucket.id === bucketId) || BUCKETS[2];
}

function riskLabel(level: string) {
  if (level === "low") return "低风险";
  if (level === "high") return "高风险";
  return "中风险";
}

function liquidityLabel(level: string) {
  if (level === "high") return "高流动";
  if (level === "low") return "低流动";
  return "中流动";
}

type Allocation = {
  id: string;
  asset_type: string;
  asset_name: string;
  amount: number;
  currency: string;
  liquidity_level: string;
  risk_level: string;
  current_percent: number;
  target_percent: number;
};

export default function AssetsPage() {
  const { isAuthenticated } = useAuth();
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    bucket: "growth",
    asset_name: "",
    amount: "",
    target_percent: "",
    currency: "CNY",
    liquidity_level: "medium",
    risk_level: "medium",
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

  const summary = useMemo(() => {
    const total = allocations.reduce((sum, item) => sum + item.amount, 0);
    const targetTotal = allocations.reduce((sum, item) => sum + item.target_percent, 0);
    const bucketRows = BUCKETS.map((bucket) => {
      const items = allocations.filter((item) => classifyBucket(item.asset_type) === bucket.id);
      const amount = items.reduce((sum, item) => sum + item.amount, 0);
      const target = items.reduce((sum, item) => sum + item.target_percent, 0);
      const current = total > 0 ? (amount / total) * 100 : 0;
      const gapAmount = ((target - current) / 100) * total;
      return {
        ...bucket,
        amount,
        current,
        target,
        diff: current - target,
        gapAmount,
        count: items.length,
      };
    });
    const highRiskAmount = allocations
      .filter((item) => item.risk_level === "high")
      .reduce((sum, item) => sum + item.amount, 0);
    const liquidAmount = bucketRows.find((bucket) => bucket.id === "liquid")?.amount || 0;
    const largest = allocations.reduce<Allocation | null>(
      (max, item) => (!max || item.amount > max.amount ? item : max),
      null
    );
    return {
      total,
      targetTotal,
      bucketRows,
      highRiskPercent: total > 0 ? (highRiskAmount / total) * 100 : 0,
      liquidPercent: total > 0 ? (liquidAmount / total) * 100 : 0,
      largest,
      largestPercent: largest && total > 0 ? (largest.amount / total) * 100 : 0,
      alerts: bucketRows.filter((bucket) => Math.abs(bucket.diff) >= 5),
    };
  }, [allocations]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      await addAllocation({
        asset_type: formData.bucket,
        asset_name: formData.asset_name.trim(),
        amount: Number(formData.amount) || 0,
        target_percent: Number(formData.target_percent) || 0,
        currency: formData.currency,
        liquidity_level: formData.liquidity_level,
        risk_level: formData.risk_level,
      });
      setFormData({
        bucket: "growth",
        asset_name: "",
        amount: "",
        target_percent: "",
        currency: "CNY",
        liquidity_level: "medium",
        risk_level: "medium",
      });
      setShowForm(false);
      await fetchAllocations();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    setRemovingId(id);
    try {
      await deleteAllocation(id);
      await fetchAllocations();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRemovingId(null);
    }
  };

  const bucketChartData = summary.bucketRows
    .filter((bucket) => bucket.amount > 0)
    .map((bucket) => ({
      name: bucket.label,
      value: bucket.amount,
      color: bucket.color,
    }));

  const driftData = summary.bucketRows.map((bucket) => ({
    name: bucket.label,
    current: Number(bucket.current.toFixed(1)),
    target: Number(bucket.target.toFixed(1)),
  }));

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-center justify-center gap-4 py-20 text-center">
        <Briefcase className="h-10 w-10 text-muted-foreground" />
        <h1 className="text-2xl font-bold">个人资产配置规划</h1>
        <p className="text-sm text-muted-foreground">
          本地个人版需要登录后读取你的资产、目标比例和规划记录。
        </p>
        <Link
          href="/login"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          登录本地账号
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">个人资产配置规划</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            用四笔钱框架管理流动性、稳健资产、长期增值和风险保障。
          </p>
        </div>
        <button
          onClick={() => setShowForm((p) => !p)}
          className="inline-flex items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          新增资产
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">净资产</span>
            <Banknote className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="mt-2 text-2xl font-bold">¥{formatNumber(summary.total, 0)}</p>
          <p className="mt-1 text-xs text-muted-foreground">{allocations.length} 项资产</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">流动钱占比</span>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="mt-2 text-2xl font-bold">{formatPercent(summary.liquidPercent)}</p>
          <p className="mt-1 text-xs text-muted-foreground">建议覆盖 6-12 个月支出</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">高风险资产</span>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="mt-2 text-2xl font-bold">{formatPercent(summary.highRiskPercent)}</p>
          <p className="mt-1 text-xs text-muted-foreground">用于观察权益和高波动暴露</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">最大单项</span>
            <Target className="h-4 w-4 text-muted-foreground" />
          </div>
          <p className="mt-2 truncate text-lg font-bold">{summary.largest?.asset_name || "—"}</p>
          <p className="mt-1 text-xs text-muted-foreground">{formatPercent(summary.largestPercent)}</p>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleAdd} className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-3 text-sm font-semibold">新增资产到规划</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            <select
              value={formData.bucket}
              onChange={(e) => setFormData((p) => ({ ...p, bucket: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              {BUCKETS.map((bucket) => (
                <option key={bucket.id} value={bucket.id}>{bucket.label}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="资产名称，如 A股、货币基金、保险"
              value={formData.asset_name}
              onChange={(e) => setFormData((p) => ({ ...p, asset_name: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="金额"
              value={formData.amount}
              onChange={(e) => setFormData((p) => ({ ...p, amount: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            />
            <input
              type="number"
              step="0.1"
              placeholder="目标占比 %"
              value={formData.target_percent}
              onChange={(e) => setFormData((p) => ({ ...p, target_percent: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            />
            <select
              value={formData.currency}
              onChange={(e) => setFormData((p) => ({ ...p, currency: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="CNY">人民币</option>
              <option value="USD">美元</option>
              <option value="HKD">港币</option>
            </select>
            <select
              value={formData.liquidity_level}
              onChange={(e) => setFormData((p) => ({ ...p, liquidity_level: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="high">高流动</option>
              <option value="medium">中流动</option>
              <option value="low">低流动</option>
            </select>
            <select
              value={formData.risk_level}
              onChange={(e) => setFormData((p) => ({ ...p, risk_level: e.target.value }))}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="low">低风险</option>
              <option value="medium">中风险</option>
              <option value="high">高风险</option>
            </select>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={adding}
                className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                保存
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent"
              >
                取消
              </button>
            </div>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        {summary.bucketRows.map((bucket) => {
          const Icon = bucket.icon;
          return (
            <div key={bucket.id} className="rounded-lg border border-border bg-card p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md" style={{ backgroundColor: `${bucket.color}22`, color: bucket.color }}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <div>
                    <h2 className="text-sm font-semibold">{bucket.label}</h2>
                    <p className="text-xs text-muted-foreground">{bucket.count} 项</p>
                  </div>
                </div>
                <span className={cn("text-xs font-bold", bucket.diff > 5 ? "text-up" : bucket.diff < -5 ? "text-down" : "text-muted-foreground")}>
                  {bucket.diff > 0 ? "+" : ""}{formatPercent(bucket.diff)}
                </span>
              </div>
              <p className="mt-3 text-xl font-bold">¥{formatNumber(bucket.amount, 0)}</p>
              <div className="mt-3 h-2 rounded-full bg-muted">
                <div
                  className="h-2 rounded-full"
                  style={{ width: `${Math.min(bucket.current, 100)}%`, backgroundColor: bucket.color }}
                />
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                当前 {formatPercent(bucket.current)} / 目标 {formatPercent(bucket.target)}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">{bucket.description}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <PieChartIcon className="h-4 w-4 text-muted-foreground" />
            四笔钱分布
          </h2>
          {bucketChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChartRecharts>
                <Pie data={bucketChartData} cx="50%" cy="50%" innerRadius={62} outerRadius={104} paddingAngle={2} dataKey="value">
                  {bucketChartData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => `¥${formatNumber(value, 0)}`} />
              </PieChartRecharts>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[280px] items-center justify-center text-sm text-muted-foreground">
              暂无资产数据
            </div>
          )}
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <CalendarClock className="h-4 w-4 text-muted-foreground" />
            当前比例 vs 目标比例
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={driftData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" fontSize={12} />
              <YAxis fontSize={12} tickFormatter={(value) => `${value}%`} />
              <Tooltip formatter={(value: number) => formatPercent(value)} />
              <Bar dataKey="current" name="当前" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
              <Bar dataKey="target" name="目标" fill="#94a3b8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {summary.alerts.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <AlertTriangle className="h-4 w-4" />
            再平衡提醒
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
            {summary.alerts.map((bucket) => (
              <div key={bucket.id} className="rounded-md bg-background/70 p-3 text-sm">
                <span className="font-medium">{bucket.label}</span>
                <span className="ml-2 text-muted-foreground">
                  {bucket.diff > 0 ? "超配" : "低配"} {formatPercent(Math.abs(bucket.diff))}
                </span>
                <p className="mt-1 text-xs text-muted-foreground">
                  {bucket.gapAmount > 0
                    ? `后续新增资金优先补入约 ¥${formatNumber(Math.abs(bucket.gapAmount), 0)}`
                    : `可考虑减配或等待其他资产补齐约 ¥${formatNumber(Math.abs(bucket.gapAmount), 0)}`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="px-4 py-2 text-left font-medium">资产</th>
              <th className="px-4 py-2 text-left font-medium">四笔钱</th>
              <th className="px-4 py-2 text-right font-medium">金额</th>
              <th className="px-4 py-2 text-right font-medium">当前</th>
              <th className="px-4 py-2 text-right font-medium">目标</th>
              <th className="px-4 py-2 text-right font-medium">偏离</th>
              <th className="hidden px-4 py-2 text-right font-medium md:table-cell">属性</th>
              <th className="px-4 py-2 text-right font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {allocations.map((item) => {
              const bucket = bucketMeta(classifyBucket(item.asset_type));
              const diff = item.current_percent - item.target_percent;
              return (
                <tr key={item.id} className="border-t border-border hover:bg-muted/50">
                  <td className="px-4 py-2 font-medium">{item.asset_name}</td>
                  <td className="px-4 py-2">
                    <span className="rounded-full px-2 py-0.5 text-xs" style={{ backgroundColor: `${bucket.color}22`, color: bucket.color }}>
                      {bucket.label}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">¥{formatNumber(item.amount, 0)}</td>
                  <td className="px-4 py-2 text-right">{formatPercent(item.current_percent)}</td>
                  <td className="px-4 py-2 text-right text-muted-foreground">{formatPercent(item.target_percent)}</td>
                  <td className={cn("px-4 py-2 text-right font-bold", diff > 0 ? "text-up" : diff < 0 ? "text-down" : "text-neutral")}>
                    {diff > 0 ? "+" : ""}{formatPercent(diff)}
                  </td>
                  <td className="hidden px-4 py-2 text-right text-xs text-muted-foreground md:table-cell">
                    {CURRENCY_LABEL[item.currency] || item.currency} · {liquidityLabel(item.liquidity_level)} · {riskLabel(item.risk_level)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => handleDelete(item.id)}
                      disabled={removingId === item.id}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                      aria-label="Delete allocation"
                    >
                      {removingId === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                    </button>
                  </td>
                </tr>
              );
            })}
            {allocations.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-sm text-muted-foreground">
                  先新增现金、固收、权益或保障类资产，建立你的长期配置基线。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {Math.abs(summary.targetTotal - 100) > 1 && allocations.length > 0 && (
        <div className="rounded-md bg-muted p-3 text-sm text-muted-foreground">
          当前目标比例合计为 {formatPercent(summary.targetTotal)}，建议调整到 100%，这样再平衡建议会更准确。
        </div>
      )}
    </div>
  );
}
