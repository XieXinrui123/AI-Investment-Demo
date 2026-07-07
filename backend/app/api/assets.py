from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.database import get_db
from app.models.models import User, AssetAllocation
from app.core.security import get_current_user_optional
from app.core.schemas import AssetAllocationCreate, AssetAllocationOut

router = APIRouter()

@router.get("/", response_model=List[AssetAllocationOut])
async def get_allocations(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取资产配置"""
    if not current_user:
        return []
    items = db.query(AssetAllocation).filter(AssetAllocation.user_id == current_user.id).all()
    
    # Calculate ratios
    total = sum(float(item.amount) for item in items if item.amount) if items else 0
    result = []
    for item in items:
        current_ratio = (float(item.amount) / total) if total > 0 else 0
        deviation = (current_ratio - float(item.target_ratio)) if item.target_ratio else 0
        result.append({
            "id": item.id,
            "asset_type": item.asset_type,
            "asset_name": item.asset_name,
            "amount": float(item.amount) if item.amount else 0,
            "currency": item.currency,
            "liquidity_level": item.liquidity_level,
            "risk_level": item.risk_level,
            "target_ratio": float(item.target_ratio) if item.target_ratio else None,
            "current_ratio": round(current_ratio, 4),
            "deviation": round(deviation, 4),
            "updated_at": item.updated_at,
        })
    return result

@router.post("/", response_model=AssetAllocationOut)
async def add_allocation(
    item: AssetAllocationCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """添加资产配置"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    db_item = AssetAllocation(
        user_id=current_user.id,
        **item.model_dump()
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/{allocation_id}", response_model=AssetAllocationOut)
async def update_allocation(
    allocation_id: int,
    item: AssetAllocationCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """更新资产配置"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    db_item = db.query(AssetAllocation).filter(
        AssetAllocation.id == allocation_id,
        AssetAllocation.user_id == current_user.id
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Allocation not found")
    for field, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{allocation_id}")
async def delete_allocation(
    allocation_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """删除资产配置"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    item = db.query(AssetAllocation).filter(
        AssetAllocation.id == allocation_id,
        AssetAllocation.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Allocation not found")
    db.delete(item)
    db.commit()
    return {"message": "Allocation deleted"}

@router.get("/analysis")
async def get_allocation_analysis(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取资产配置分析"""
    if not current_user:
        return {}
    from app.services.ai_service import AIService
    ai_service = AIService()
    items = db.query(AssetAllocation).filter(AssetAllocation.user_id == current_user.id).all()
    analysis = await ai_service.analyze_asset_allocation(items, current_user.risk_level)
    return analysis
