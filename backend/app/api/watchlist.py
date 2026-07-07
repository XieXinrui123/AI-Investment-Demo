from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.database import get_db
from app.models.models import User, Watchlist
from app.core.security import get_current_user_optional
from app.core.schemas import WatchlistCreate, WatchlistOut
from app.services.market_service import MarketService

router = APIRouter()
market_service = MarketService()

@router.get("/", response_model=List[WatchlistOut])
async def get_watchlist(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取自选股列表"""
    if not current_user:
        return []
    items = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    result = []
    for item in items:
        # Enrich with market data
        stock_data = await market_service.get_stock_detail(item.ticker)
        result.append({
            "id": item.id,
            "ticker": item.ticker,
            "name": stock_data.get("name", item.ticker),
            "note": item.note,
            "target_price": float(item.target_price) if item.target_price else None,
            "alert_price": float(item.alert_price) if item.alert_price else None,
            "current_price": stock_data.get("price"),
            "change_pct": stock_data.get("change_pct"),
            "created_at": item.created_at,
        })
    return result

@router.post("/", response_model=WatchlistOut)
async def add_watchlist(
    item: WatchlistCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """添加自选股"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    # Check if already exists
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker == item.ticker
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stock already in watchlist")
    
    db_item = Watchlist(
        user_id=current_user.id,
        ticker=item.ticker,
        note=item.note,
        target_price=item.target_price,
        alert_price=item.alert_price,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    stock_data = await market_service.get_stock_detail(item.ticker)
    return {
        "id": db_item.id,
        "ticker": db_item.ticker,
        "name": stock_data.get("name", item.ticker),
        "note": db_item.note,
        "target_price": float(db_item.target_price) if db_item.target_price else None,
        "alert_price": float(db_item.alert_price) if db_item.alert_price else None,
        "current_price": stock_data.get("price"),
        "change_pct": stock_data.get("change_pct"),
        "created_at": db_item.created_at,
    }

@router.delete("/{watchlist_id}")
async def remove_watchlist(
    watchlist_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """删除自选股"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    item = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    db.delete(item)
    db.commit()
    return {"message": "Removed from watchlist"}
