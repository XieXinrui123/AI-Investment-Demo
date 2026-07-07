from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.database import get_db
from app.models.models import User, Portfolio
from app.core.security import get_current_user_optional
from app.core.schemas import PortfolioCreate, PortfolioOut, PortfolioSummary
from app.services.market_service import MarketService
from app.services.portfolio_service import PortfolioService

router = APIRouter()
market_service = MarketService()
portfolio_service = PortfolioService()

@router.get("/", response_model=List[PortfolioOut])
async def get_portfolio(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取持仓列表"""
    if not current_user:
        return []
    items = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    return await portfolio_service.enrich_portfolio(items)

@router.get("/summary")
async def get_portfolio_summary(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取持仓汇总"""
    if not current_user:
        return {}
    items = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    return await portfolio_service.get_summary(items)

@router.post("/", response_model=PortfolioOut)
async def add_portfolio(
    item: PortfolioCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """添加持仓"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    db_item = Portfolio(
        user_id=current_user.id,
        ticker=item.ticker,
        name=item.name,
        quantity=item.quantity,
        avg_cost=item.avg_cost,
        buy_date=item.buy_date,
        thesis=item.thesis,
        target_weight=item.target_weight,
        stop_condition=item.stop_condition,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    enriched = await portfolio_service.enrich_portfolio([db_item])
    return enriched[0] if enriched else db_item

@router.put("/{portfolio_id}", response_model=PortfolioOut)
async def update_portfolio(
    portfolio_id: int,
    item: PortfolioCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """更新持仓"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    db_item = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    
    for field, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    
    enriched = await portfolio_service.enrich_portfolio([db_item])
    return enriched[0] if enriched else db_item

@router.delete("/{portfolio_id}")
async def remove_portfolio(
    portfolio_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """删除持仓"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    item = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    db.delete(item)
    db.commit()
    return {"message": "Removed from portfolio"}

@router.get("/risk-analysis")
async def get_risk_analysis(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取持仓风险分析"""
    if not current_user:
        return {}
    items = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    return await portfolio_service.get_risk_analysis(items)

@router.get("/rebalance")
async def get_rebalance_suggestions(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取再平衡建议"""
    if not current_user:
        return []
    items = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    return await portfolio_service.get_rebalance_suggestions(items)
