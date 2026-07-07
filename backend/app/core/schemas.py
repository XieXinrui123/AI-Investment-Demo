from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

# ========== Auth Schemas ==========
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    risk_level: str = "balanced"
    investor_type: Optional[str] = None
    membership: str = "free"
    is_admin: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    risk_level: Optional[str] = None
    investor_type: Optional[str] = None
    investment_experience: Optional[str] = None
    max_drawdown_tolerance: Optional[float] = None
    investment_horizon: Optional[str] = None

# ========== Market Schemas ==========
class IndexDataOut(BaseModel):
    index_code: str
    index_name: str
    close: float
    change_pct: float
    amount: Optional[float] = None
    market: str

class SectorDataOut(BaseModel):
    sector_name: str
    change_pct: float
    amount: Optional[float] = None
    net_inflow: Optional[float] = None
    leading_stocks: Optional[list] = None

class MarketOverviewOut(BaseModel):
    date: str
    indices: List[IndexDataOut]
    sectors_up: List[SectorDataOut]
    sectors_down: List[SectorDataOut]
    sentiment_score: float
    up_count: int
    down_count: int
    limit_up_count: int
    limit_down_count: int
    total_amount: float

# ========== Watchlist Schemas ==========
class WatchlistCreate(BaseModel):
    ticker: str
    note: Optional[str] = None
    target_price: Optional[float] = None
    alert_price: Optional[float] = None

class WatchlistOut(BaseModel):
    id: int
    ticker: str
    name: Optional[str] = None
    note: Optional[str] = None
    target_price: Optional[float] = None
    alert_price: Optional[float] = None
    current_price: Optional[float] = None
    change_pct: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== Portfolio Schemas ==========
class PortfolioCreate(BaseModel):
    ticker: str
    name: Optional[str] = None
    quantity: float
    avg_cost: float
    buy_date: Optional[date] = None
    thesis: Optional[str] = None
    target_weight: Optional[float] = None
    stop_condition: Optional[str] = None

class PortfolioOut(BaseModel):
    id: int
    ticker: str
    name: Optional[str] = None
    quantity: float
    avg_cost: float
    buy_date: Optional[date] = None
    thesis: Optional[str] = None
    target_weight: Optional[float] = None
    stop_condition: Optional[str] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    weight: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class PortfolioSummary(BaseModel):
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    cash_ratio: float
    stock_count: int
    winning_count: int
    losing_count: int

# ========== Journal Schemas ==========
class JournalCreate(BaseModel):
    date: date
    ticker: Optional[str] = None
    action: str
    price: Optional[float] = None
    quantity: Optional[float] = None
    weight: Optional[float] = None
    reason: Optional[str] = None
    thesis: Optional[str] = None
    risk: Optional[str] = None
    exit_condition: Optional[str] = None
    emotion: Optional[str] = None
    review: Optional[str] = None

class JournalOut(BaseModel):
    id: int
    user_id: int
    date: date
    ticker: Optional[str] = None
    action: str
    price: Optional[float] = None
    quantity: Optional[float] = None
    weight: Optional[float] = None
    reason: Optional[str] = None
    thesis: Optional[str] = None
    risk: Optional[str] = None
    exit_condition: Optional[str] = None
    emotion: Optional[str] = None
    review: Optional[str] = None
    ai_review: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== AI Assistant Schemas ==========
class AIQuestion(BaseModel):
    question: str
    context_type: Optional[str] = None
    related_tickers: Optional[List[str]] = None

class AIAnswer(BaseModel):
    answer: str
    conclusion: Optional[str] = None
    facts: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    watchpoints: Optional[List[str]] = None
    related_tickers: Optional[List[str]] = None

# ========== Asset Allocation Schemas ==========
class AssetAllocationCreate(BaseModel):
    asset_type: str
    asset_name: Optional[str] = None
    amount: float
    currency: str = "CNY"
    liquidity_level: Optional[str] = None
    risk_level: Optional[str] = None
    target_ratio: Optional[float] = None

class AssetAllocationOut(BaseModel):
    id: int
    asset_type: str
    asset_name: Optional[str] = None
    amount: float
    currency: str
    liquidity_level: Optional[str] = None
    risk_level: Optional[str] = None
    target_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    deviation: Optional[float] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ========== Daily Review Schemas ==========
class DailyReviewOut(BaseModel):
    id: int
    date: date
    market: str
    one_sentence_summary: Optional[str] = None
    market_summary: Optional[str] = None
    index_summary: Optional[str] = None
    sector_summary: Optional[str] = None
    topic_summary: Optional[str] = None
    fund_flow_summary: Optional[str] = None
    news_summary: Optional[str] = None
    risk_summary: Optional[str] = None
    tomorrow_watchlist: Optional[str] = None
    ai_generated: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== News Schemas ==========
class NewsOut(BaseModel):
    id: int
    title: str
    source: Optional[str] = None
    publish_time: Optional[datetime] = None
    content: Optional[str] = None
    url: Optional[str] = None
    related_tickers: Optional[list] = None
    sentiment: Optional[str] = None
    impact_level: Optional[str] = None
    ai_summary: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True

# ========== Announcement Schemas ==========
class AnnouncementOut(BaseModel):
    id: int
    ticker: Optional[str] = None
    title: Optional[str] = None
    publish_time: Optional[datetime] = None
    announcement_type: Optional[str] = None
    content: Optional[str] = None
    file_url: Optional[str] = None
    ai_summary: Optional[str] = None
    impact_direction: Optional[str] = None
    
    class Config:
        from_attributes = True

class AnnouncementAnalyzeRequest(BaseModel):
    content: str
    announcement_type: Optional[str] = None

class AnnouncementAnalyzeResponse(BaseModel):
    summary: str
    key_facts: List[str]
    positive_factors: List[str]
    negative_factors: List[str]
    short_term_impact: str
    long_term_impact: str
    portfolio_impact: str
    watchpoints: List[str]
    risk_warning: str
