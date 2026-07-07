from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.models.database import get_db
from app.models.models import User
from app.core.security import get_current_user_optional
from app.core.schemas import MarketOverviewOut, DailyReviewOut, NewsOut
from app.services.market_service import MarketService

router = APIRouter()
market_service = MarketService()

@router.get("/overview")
async def get_market_overview(
    market: str = "A",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取市场概览数据"""
    return await market_service.get_market_overview(market)

@router.get("/indices")
async def get_indices(
    market: str = "A",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取指数行情"""
    return await market_service.get_indices(market)

@router.get("/sectors")
async def get_sectors(
    market: str = "A",
    sort_by: str = "change_pct",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取行业板块数据"""
    return await market_service.get_sectors(market, sort_by)

@router.get("/hot-topics")
async def get_hot_topics(
    market: str = "A",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取热门题材"""
    return await market_service.get_hot_topics(market)

@router.get("/stock-movers")
async def get_stock_movers(
    market: str = "A",
    category: str = "gainers",  # gainers, losers, volume, turnover
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取个股异动"""
    return await market_service.get_stock_movers(market, category)

@router.get("/fund-flow")
async def get_fund_flow(
    market: str = "A",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取资金流向"""
    return await market_service.get_fund_flow(market)

@router.get("/news")
async def get_news(
    category: Optional[str] = None,
    impact: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取新闻"""
    return await market_service.get_news(category, impact, limit)

@router.get("/stock/{ticker}")
async def get_stock_detail(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取个股详情"""
    return await market_service.get_stock_detail(ticker)
