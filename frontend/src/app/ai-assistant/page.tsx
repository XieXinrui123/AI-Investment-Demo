"use client";

import React, { useState } from "react";
import AIChat from "@/components/AIChat";
import { cn } from "@/lib/utils";
import { Bot, MessageCircle, TrendingUp, Wallet, PieChart, BarChart3 } from "lucide-react";

const quickQuestions = [
  { label: "今天市场怎么样？", icon: TrendingUp },
  { label: "我的持仓有风险吗？", icon: Wallet },
  { label: "推荐关注哪些板块？", icon: BarChart3 },
  { label: "资产如何再平衡？", icon: PieChart },
];

const contexts = [
  { id: "market", label: "Market", icon: TrendingUp },
  { id: "stock", label: "Stock", icon: BarChart3 },
  { id: "portfolio", label: "Portfolio", icon: Wallet },
  { id: "asset", label: "Asset", icon: PieChart },
];

export default function AIAssistantPage() {
  const [contextType, setContextType] = useState<string>("market");
  const [messages, setMessages] = useState<any[]>([]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Bot className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold">AI Assistant</h1>
      </div>

      {/* Context Selector */}
      <div className="flex flex-wrap gap-2">
        {contexts.map((ctx) => {
          const Icon = ctx.icon;
          return (
            <button
              key={ctx.id}
              onClick={() => setContextType(ctx.id)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors",
                contextType === ctx.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {ctx.label}
            </button>
          );
        })}
      </div>

      {/* Quick Questions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {quickQuestions.map((q) => {
          const Icon = q.icon;
          return (
            <button
              key={q.label}
              onClick={() => {
                setMessages((prev) => [
                  ...prev,
                  { role: "user", content: q.label, timestamp: new Date().toISOString() },
                ]);
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-3 text-sm font-medium text-foreground hover:bg-accent hover:text-accent-foreground transition-colors text-left"
            >
              <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="truncate">{q.label}</span>
            </button>
          );
        })}
      </div>

      {/* Chat Interface */}
      <AIChat
        initialMessages={messages}
        contextType={contextType}
        className="min-h-[500px]"
      />
    </div>
  );
}
