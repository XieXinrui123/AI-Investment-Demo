from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from app.models.database import get_db
from app.models.models import User
from app.core.security import get_current_user, get_current_user_optional, get_current_active_user
from app.services.ai_service import AIService
from app.services.market_service import MarketService

router = APIRouter()
market_service = MarketService()
ai_service = AIService()

@router.get("/")
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取首页 Dashboard 数据"""
    today = date.today()
    
    # Market overview
    market_overview = await market_service.get_market_overview("A")
    
    # AI daily review
    daily_review = await market_service.get_daily_review(today)
    
    # User's watchlist summary (if logged in)
    watchlist_summary = None
    if current_user and current_user.id:
        from app.models.models import Watchlist
        watchlist_items = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).limit(5).all()
        watchlist_list = []
        for item in watchlist_items:
            stock_data = await market_service.get_stock_detail(item.ticker)
            watchlist_list.append({
                "ticker": item.ticker,
                "name": stock_data.get("name", item.ticker),
                "price": stock_data.get("price"),
                "change_pct": stock_data.get("change_pct"),
                "news_count": stock_data.get("news_count", 0),
            })
        # Find top gainer and loser
        top_gainer = None
        top_loser = None
        if watchlist_list:
            sorted_by_change = sorted(watchlist_list, key=lambda x: x.get("change_pct", 0) or 0, reverse=True)
            top_gainer = sorted_by_change[0] if sorted_by_change[0].get("change_pct", 0) > 0 else None
            top_loser = sorted_by_change[-1] if sorted_by_change[-1].get("change_pct", 0) < 0 else None
        watchlist_summary = {
            "total_items": len(watchlist_items),
            "top_gainer": top_gainer,
            "top_loser": top_loser,
            "items": watchlist_list,
        }
    
    # User's portfolio summary (if logged in)
    portfolio_summary = None
    if current_user and current_user.id:
        from app.models.models import Portfolio
        from app.services.portfolio_service import PortfolioService
        portfolio_items = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
        if portfolio_items:
            ps = PortfolioService()
            portfolio_summary = await ps.get_summary(portfolio_items)
            if portfolio_summary:
                portfolio_summary = {
                    "total_value": portfolio_summary.get("total_value", 0),
                    "total_pnl": portfolio_summary.get("total_pnl", 0),
                    "risk_level": portfolio_summary.get("risk_level", "medium"),
                }
    
    return {
        "date": today.isoformat(),
        "market_status": "closed",
        "market_overview": market_overview,
        "ai_summary": daily_review.get("one_sentence_summary") if daily_review else None,
        "sentiment": market_overview.get("sentiment_score", 50),
        "watchlist_summary": watchlist_summary,
        "portfolio_summary": portfolio_summary,
        "tomorrow_watchlist": daily_review.get("tomorrow_watchlist") if daily_review else None,
    }
