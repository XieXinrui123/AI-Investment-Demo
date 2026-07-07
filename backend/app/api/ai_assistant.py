from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.database import get_db
from app.models.models import User
from app.core.security import get_current_user_optional
from app.core.schemas import AIQuestion, AIAnswer, AnnouncementAnalyzeRequest, AnnouncementAnalyzeResponse
from app.services.ai_service import AIService
from app.services.market_service import MarketService

router = APIRouter()
ai_service = AIService()
market_service = MarketService()

@router.post("/chat", response_model=AIAnswer)
async def ai_chat(
    question: AIQuestion,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """AI投研助手问答"""
    answer = await ai_service.chat(
        question=question.question,
        context_type=question.context_type,
        related_tickers=question.related_tickers,
        user_id=current_user.id if current_user else None
    )
    return answer

@router.post("/analyze-announcement", response_model=AnnouncementAnalyzeResponse)
async def analyze_announcement(
    request: AnnouncementAnalyzeRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """公告/财报解读"""
    analysis = await ai_service.analyze_announcement(
        content=request.content,
        announcement_type=request.announcement_type
    )
    return analysis

@router.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """上传PDF进行解读"""
    import tempfile
    import os
    
    # Save uploaded file
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Extract text based on file type
        if suffix.lower() == ".pdf":
            text = await ai_service.extract_pdf_text(tmp_path)
        elif suffix.lower() in [".docx", ".doc"]:
            text = await ai_service.extract_docx_text(tmp_path)
        else:
            text = content.decode("utf-8", errors="ignore")
        
        analysis = await ai_service.analyze_announcement(content=text)
        return analysis
    finally:
        os.unlink(tmp_path)

@router.post("/portfolio-review")
async def portfolio_ai_review(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """AI持仓组合复盘"""
    if not current_user:
        return {"detail": "请先登录以使用此功能"}
    from app.models.models import Portfolio
    items = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    review = await ai_service.review_portfolio(items)
    return review

@router.post("/daily-market-review")
async def generate_daily_review(
    market: str = "A",
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """生成每日市场复盘"""
    review = await ai_service.generate_daily_review(market)
    return review

@router.post("/stock-review/{ticker}")
async def generate_stock_review(
    ticker: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """生成个股复盘"""
    review = await ai_service.generate_stock_review(ticker)
    return review

@router.post("/investment-checklist/{ticker}")
async def investment_checklist(
    ticker: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """巴菲特六关Checklist"""
    result = await ai_service.investment_checklist(ticker)
    return result
