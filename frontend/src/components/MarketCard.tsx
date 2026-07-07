"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn, formatNumber, formatPercent } from "@/lib/utils";

interface MarketCardProps {
  title: string;
  subtitle?: string;
  price: number;
  change: number;
  changePercent: number;
  extra?: { label: string; value: string }[];
  className?: string;
}

export default function MarketCard({
  title,
  subtitle,
  price,
  change,
  changePercent,
  extra,
  className,
}: MarketCardProps) {
  const isUp = change > 0;
  const isDown = change < 0;
  const colorClass = isUp ? "text-up" : isDown ? "text-down" : "text-neutral";
  const bgClass = isUp
    ? "bg-red-50 dark:bg-red-950/20"
    : isDown
    ? "bg-green-50 dark:bg-green-950/20"
    : "bg-gray-50 dark:bg-gray-900/30";

  return (
    <div
      className={cn(
        "rounded-lg border border-border p-4 transition-shadow hover:shadow-md",
        bgClass,
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        <div className={cn("flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold", colorClass)}>
          {isUp ? (
            <TrendingUp className="h-3 w-3" />
          ) : isDown ? (
            <TrendingDown className="h-3 w-3" />
          ) : (
            <Minus className="h-3 w-3" />
          )}
          {formatPercent(changePercent)}
        </div>
      </div>
      <div className="mt-3">
        <p className="text-2xl font-bold text-foreground">{formatNumber(price, 2)}</p>
        <p className={cn("text-sm font-medium", colorClass)}>
          {isUp ? "+" : ""}
          {formatNumber(change, 2)}
        </p>
      </div>
      {extra && extra.length > 0 && (
        <div className="mt-3 grid grid-cols-2 gap-2 border-t border-border/50 pt-2">
          {extra.map((item) => (
            <div key={item.label}>
              <p className="text-[10px] text-muted-foreground uppercase">{item.label}</p>
              <p className="text-xs font-semibold text-foreground">{item.value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
