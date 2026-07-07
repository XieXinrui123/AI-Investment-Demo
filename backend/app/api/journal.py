from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.models.database import get_db
from app.models.models import User, InvestmentJournal
from app.core.security import get_current_user_optional
from app.core.schemas import JournalCreate, JournalOut

router = APIRouter()

@router.get("/", response_model=List[JournalOut])
async def get_journals(
    ticker: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0, limit: int = 100,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取投资日志列表"""
    if not current_user:
        return []
    query = db.query(InvestmentJournal).filter(InvestmentJournal.user_id == current_user.id)
    if ticker:
        query = query.filter(InvestmentJournal.ticker == ticker)
    if action:
        query = query.filter(InvestmentJournal.action == action)
    if start_date:
        query = query.filter(InvestmentJournal.date >= start_date)
    if end_date:
        query = query.filter(InvestmentJournal.date <= end_date)
    return query.order_by(InvestmentJournal.date.desc()).offset(skip).limit(limit).all()

@router.post("/", response_model=JournalOut)
async def create_journal(
    journal: JournalCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """创建投资日志"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    db_journal = InvestmentJournal(
        user_id=current_user.id,
        **journal.model_dump()
    )
    db.add(db_journal)
    db.commit()
    db.refresh(db_journal)
    return db_journal

@router.get("/{journal_id}", response_model=JournalOut)
async def get_journal(
    journal_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取单条日志"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    journal = db.query(InvestmentJournal).filter(
        InvestmentJournal.id == journal_id,
        InvestmentJournal.user_id == current_user.id
    ).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    return journal

@router.put("/{journal_id}", response_model=JournalOut)
async def update_journal(
    journal_id: int,
    journal: JournalCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """更新日志"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    db_journal = db.query(InvestmentJournal).filter(
        InvestmentJournal.id == journal_id,
        InvestmentJournal.user_id == current_user.id
    ).first()
    if not db_journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    for field, value in journal.model_dump(exclude_unset=True).items():
        setattr(db_journal, field, value)
    db.commit()
    db.refresh(db_journal)
    return db_journal

@router.delete("/{journal_id}")
async def delete_journal(
    journal_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """删除日志"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    journal = db.query(InvestmentJournal).filter(
        InvestmentJournal.id == journal_id,
        InvestmentJournal.user_id == current_user.id
    ).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    db.delete(journal)
    db.commit()
    return {"message": "Journal deleted"}

@router.post("/{journal_id}/ai-review")
async def get_ai_review(
    journal_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取AI行为复盘"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    from app.services.ai_service import AIService
    ai_service = AIService()
    
    journal = db.query(InvestmentJournal).filter(
        InvestmentJournal.id == journal_id,
        InvestmentJournal.user_id == current_user.id
    ).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    
    # Get user's recent journals for context
    recent_journals = db.query(InvestmentJournal).filter(
        InvestmentJournal.user_id == current_user.id
    ).order_by(InvestmentJournal.date.desc()).limit(30).all()
    
    review = await ai_service.review_behavior(recent_journals, journal)
    journal.ai_review = review
    db.commit()
    return {"ai_review": review}
