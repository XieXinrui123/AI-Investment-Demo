from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models.database import get_db
from app.models.models import User, DailyReview, AIChatLog, News
from app.core.security import get_current_admin

router = APIRouter()

@router.get("/users")
async def admin_list_users(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """管理员：用户列表"""
    return db.query(User).offset(skip).limit(limit).all()

@router.get("/daily-reviews")
async def admin_list_reviews(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """管理员：每日复盘列表"""
    return db.query(DailyReview).order_by(DailyReview.date.desc()).offset(skip).limit(limit).all()

@router.get("/ai-logs")
async def admin_list_ai_logs(
    skip: int = 0, limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """管理员：AI问答日志"""
    return db.query(AIChatLog).order_by(AIChatLog.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/daily-review/generate")
async def admin_generate_review(
    market: str = "A",
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """管理员：手动触发每日复盘生成"""
    from app.services.ai_service import AIService
    ai_service = AIService()
    review = await ai_service.generate_daily_review(market)
    return review

@router.get("/stats")
async def admin_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """管理员：统计数据"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_reviews = db.query(DailyReview).count()
    total_ai_chats = db.query(AIChatLog).count()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_reviews": total_reviews,
        "total_ai_chats": total_ai_chats,
    }
