# Personal Finance and Investment Research Roadmap

This roadmap is based on the current local personal deployment and competitor research. The product should stay local-first, private, and focused on helping one person make better financial planning and investment decisions.

## Competitor Patterns

### Personal finance dashboard

Empower emphasizes a whole-financial-life dashboard across budgeting, planning, retirement decisions, net worth, spending, cash flow, portfolio balance, retirement savings, and emergency fund.

Useful product lesson: the home page should not be only a market dashboard. It should answer: "Am I financially on track?"

### Four-bucket planning

Qieman and Youzhiyouxing both frame investing around life goals and mental accounts rather than only product selection. Qieman uses a "four buckets" model: liquid money, stable money, long-term investment, and insurance protection. Youzhiyouxing emphasizes family CFO-style net worth, liabilities, goals, and real investment return tracking.

Useful product lesson: asset allocation should be organized by purpose, horizon, and risk, not only by ticker or market.

### Portfolio accounting

Sharesight and Tonghuashun Investment Ledger focus on performance, tax/reporting, multi-account aggregation, dividends, cash, property/unlisted assets, and profit/loss calendars.

Useful product lesson: the portfolio module should support transaction-level accounting, cash flows, dividends, deposits/withdrawals, and true money-weighted/time-weighted returns.

### Portfolio X-Ray and exposure

Morningstar X-Ray breaks down portfolios by asset allocation, sector, geography, investment style, top holdings, overlap, and risk exposure.

Useful product lesson: the app should explain hidden concentration and overlap, not only show visible holdings.

### Backtest and strategy lab

Portfolio Visualizer focuses on backtesting, Monte Carlo simulation, tactical asset allocation, optimization, risk metrics, and drawdown/survival analysis.

Useful product lesson: investment strategy planning should include scenario tests before money is committed.

### Social/idea tracking

Xueqiu provides watchlists, portfolios, market discussion, hot stocks, fund tools, and portfolio-based idea tracking. Xueqiu combinations make a basket of holdings easy to follow and rebalance.

Useful product lesson: for a personal local app, copy the workflow but not the social network: create personal "strategy baskets" and watch their drift, risk, and thesis changes.

## Recommended Product Shape

### 1. Personal CFO Dashboard

Goal: replace the current market-first dashboard with a personal finance cockpit.

Add:

- Net worth snapshot: investable assets, cash, liabilities, total net worth
- Four-bucket allocation: liquid, stable, long-term, protection
- Monthly cash flow: income, expense, investable surplus
- Emergency fund coverage: current liquid assets / monthly expense
- Goal progress: house, retirement, education, travel, reserve
- Alerts: concentration, drawdown, missing backup, stale prices

### 2. Real Portfolio Ledger

Goal: make returns accurate enough for real personal decision-making.

Add:

- Transaction table: buy, sell, dividend, deposit, withdrawal, fee, tax
- Cost basis tracking
- Realized and unrealized P/L
- Money-weighted return (IRR)
- Time-weighted return
- Dividend income calendar
- Profit/loss calendar by day and month

### 3. Asset Allocation and Rebalancing

Goal: turn holdings into an actionable plan.

Add:

- Target allocation by bucket, market, asset class, sector, currency
- Drift calculation
- Rebalance suggestions
- "New money first" rebalance mode
- Risk budget: max single stock, max sector, max currency, max equity exposure
- One-page allocation policy statement

### 4. Portfolio X-Ray

Goal: expose hidden risks.

Add:

- Sector exposure
- Geography exposure
- Currency exposure
- Top 10 holdings concentration
- Single-stock and ETF/fund overlap
- Style exposure: growth/value, large/small, cyclical/defensive
- Drawdown and volatility estimate

### 5. Strategy Lab

Goal: support investment strategy planning before execution.

Add:

- Strategy baskets: value, dividend, AI, index, overseas, cash-plus
- Backtest using local historical prices where available
- Scenario tests: bull, bear, sideways, rate cut, RMB depreciation
- Monte Carlo for long-term goals
- Rebalance frequency comparison
- Thesis template and exit checklist

### 6. Research Workflow

Goal: convert market noise into a repeatable research system.

Add:

- Company research page: business, moat, valuation, risks, catalysts
- Watchlist scoring: quality, valuation, momentum, risk, conviction
- News/event timeline per ticker
- AI daily brief only for watchlist and holdings
- Thesis drift detection: "what changed since I bought?"
- Decision journal tied to trades

### 7. Local Data Reliability

Goal: make the local app trustworthy.

Add:

- Data source status indicator
- Last updated time for every quote
- Market session awareness: pre-open, trading, lunch break, closed
- Fallback labels: live, previous close, mock
- Manual price override for private assets
- Backup reminder if database was not backed up in 7 days

## Implementation Priority

### Phase 1: Trust and bookkeeping

1. Fix quote states and source labels across all market tables.
2. Add transaction ledger and cash flow fields.
3. Add backup freshness warning.
4. Add Personal CFO dashboard.

### Phase 2: Planning

1. Add four-bucket asset allocation.
2. Add target allocation and drift.
3. Add rebalancing suggestions.
4. Add emergency fund and goal progress.

### Phase 3: Research

1. Add strategy baskets.
2. Add ticker research pages.
3. Add thesis and exit checklist.
4. Add watchlist scoring.

### Phase 4: Analytics

1. Add X-Ray exposure analysis.
2. Add return metrics: IRR, TWR, max drawdown.
3. Add basic backtesting.
4. Add Monte Carlo goal simulation.

## Near-Term UI Changes

- Rename dashboard sections from generic English labels to personal workflow language.
- Add "Data Source" and "Last Updated" badges in market tables.
- Split market view into "行情观察" and "我的组合影响".
- Add an "资产规划" first-level page focused on four-bucket planning.
- Add an "投资策略" page for baskets, thesis, and rebalance plans.
