from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey, Date, BigInteger, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    avatar_url = Column(String(500))
    phone = Column(String(20))
    
    risk_level = Column(String(20), default="balanced")
    investor_type = Column(String(50))
    investment_experience = Column(String(20))
    max_drawdown_tolerance = Column(Float)
    investment_horizon = Column(String(20))
    
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    membership = Column(String(20), default="free")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    journals = relationship("InvestmentJournal", back_populates="user", cascade="all, delete-orphan")
    asset_allocations = relationship("AssetAllocation", back_populates="user", cascade="all, delete-orphan")
    ai_chat_logs = relationship("AIChatLog", back_populates="user", cascade="all, delete-orphan")

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    name_en = Column(String(100))
    market = Column(String(10), nullable=False)
    exchange = Column(String(20))
    industry = Column(String(50))
    sector = Column(String(50))
    currency = Column(String(5), default="CNY")
    status = Column(String(10), default="active")
    pe_ttm = Column(Float)
    pb = Column(Float)
    dividend_yield = Column(Float)
    market_cap = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DailyMarketData(Base):
    __tablename__ = "daily_market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    prev_close = Column(Numeric(12, 4))
    change = Column(Numeric(12, 4))
    change_pct = Column(Numeric(8, 4))
    volume = Column(BigInteger)
    amount = Column(Numeric(18, 4))
    turnover_rate = Column(Numeric(8, 4))
    
    __table_args__ = (UniqueConstraint('ticker', 'date', name='uix_daily_market'),)

class IndexData(Base):
    __tablename__ = "index_data"
    
    id = Column(Integer, primary_key=True, index=True)
    index_code = Column(String(20), index=True, nullable=False)
    index_name = Column(String(50))
    date = Column(Date, index=True, nullable=False)
    close = Column(Numeric(12, 4))
    change_pct = Column(Numeric(8, 4))
    amount = Column(Numeric(18, 4))
    market = Column(String(10))

class SectorData(Base):
    __tablename__ = "sector_data"
    
    id = Column(Integer, primary_key=True, index=True)
    sector_name = Column(String(50), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    change_pct = Column(Numeric(8, 4))
    amount = Column(Numeric(18, 4))
    net_inflow = Column(Numeric(18, 4))
    leading_stocks = Column(JSON)

class News(Base):
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    source = Column(String(100))
    publish_time = Column(DateTime)
    content = Column(Text)
    url = Column(String(1000))
    related_tickers = Column(JSON)
    related_sectors = Column(JSON)
    sentiment = Column(String(10))
    impact_level = Column(String(10))
    ai_summary = Column(Text)
    category = Column(String(20))

class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True)
    title = Column(String(500))
    publish_time = Column(DateTime)
    announcement_type = Column(String(50))
    content = Column(Text)
    file_url = Column(String(1000))
    ai_summary = Column(Text)
    impact_direction = Column(String(10))

class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    note = Column(Text)
    target_price = Column(Numeric(12, 4))
    alert_price = Column(Numeric(12, 4))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="watchlists")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    name = Column(String(100))
    quantity = Column(Numeric(18, 4))
    avg_cost = Column(Numeric(12, 4))
    buy_date = Column(Date)
    thesis = Column(Text)
    target_weight = Column(Numeric(5, 4))
    stop_condition = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="portfolios")

class InvestmentJournal(Base):
    __tablename__ = "investment_journals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    ticker = Column(String(20))
    action = Column(String(20), nullable=False)
    price = Column(Numeric(12, 4))
    quantity = Column(Numeric(18, 4))
    weight = Column(Numeric(5, 4))
    reason = Column(Text)
    thesis = Column(Text)
    risk = Column(Text)
    exit_condition = Column(Text)
    emotion = Column(String(20))
    review = Column(Text)
    ai_review = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="journals")

class DailyReview(Base):
    __tablename__ = "daily_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    market = Column(String(10), default="A")
    one_sentence_summary = Column(Text)
    market_summary = Column(Text)
    index_summary = Column(Text)
    sector_summary = Column(Text)
    topic_summary = Column(Text)
    fund_flow_summary = Column(Text)
    news_summary = Column(Text)
    risk_summary = Column(Text)
    tomorrow_watchlist = Column(Text)
    ai_generated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AssetAllocation(Base):
    __tablename__ = "asset_allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    asset_type = Column(String(30), nullable=False)
    asset_name = Column(String(100))
    amount = Column(Numeric(18, 4))
    currency = Column(String(5), default="CNY")
    liquidity_level = Column(String(10))
    risk_level = Column(String(10))
    target_ratio = Column(Numeric(5, 4))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="asset_allocations")

class AIChatLog(Base):
    __tablename__ = "ai_chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    context_type = Column(String(20))
    related_tickers = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="ai_chat_logs")
