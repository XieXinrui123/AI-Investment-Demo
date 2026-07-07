"""
Database Seed Script - 填充SQLite数据库的示例数据

使用方法:
    cd backend
    python -c "from app.data.seed_data import seed_all; seed_all()"

或在启动时自动运行（已在main.py中通过create_all自动创建表结构，但需手动运行seed）
"""

import random
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.database import SessionLocal, engine
from app.models.models import (
    User,
    Stock,
    DailyMarketData,
    News,
    DailyReview,
    Watchlist,
    Portfolio,
    InvestmentJournal,
    AssetAllocation,
    IndexData,
    SectorData,
)


# ============================================================================
# Sample Data Definitions
# ============================================================================

SAMPLE_STOCKS = [
    # A-share 主板
    {"ticker": "600519.SS", "name": "贵州茅台", "name_en": "Kweichow Moutai", "market": "A", "exchange": "SSE", "industry": "食品饮料", "sector": "白酒", "currency": "CNY", "pe_ttm": 25.2, "pb": 7.8, "dividend_yield": 1.8, "market_cap": 1920000000000},
    {"ticker": "000001.SZ", "name": "平安银行", "name_en": "Ping An Bank", "market": "A", "exchange": "SZSE", "industry": "银行", "sector": "股份制银行", "currency": "CNY", "pe_ttm": 5.1, "pb": 0.52, "dividend_yield": 4.2, "market_cap": 220000000000},
    {"ticker": "600036.SS", "name": "招商银行", "name_en": "China Merchants Bank", "market": "A", "exchange": "SSE", "industry": "银行", "sector": "股份制银行", "currency": "CNY", "pe_ttm": 5.8, "pb": 0.88, "dividend_yield": 5.1, "market_cap": 890000000000},
    {"ticker": "601318.SS", "name": "中国平安", "name_en": "Ping An Insurance", "market": "A", "exchange": "SSE", "industry": "保险", "sector": "综合金融", "currency": "CNY", "pe_ttm": 8.5, "pb": 0.92, "dividend_yield": 3.8, "market_cap": 850000000000},
    {"ticker": "600276.SS", "name": "恒瑞医药", "name_en": "Hengrui Medicine", "market": "A", "exchange": "SSE", "industry": "医药生物", "sector": "创新药", "currency": "CNY", "pe_ttm": 55.3, "pb": 8.2, "dividend_yield": 0.3, "market_cap": 307000000000},
    {"ticker": "000858.SZ", "name": "五粮液", "name_en": "Wuliangye", "market": "A", "exchange": "SZSE", "industry": "食品饮料", "sector": "白酒", "currency": "CNY", "pe_ttm": 18.5, "pb": 4.2, "dividend_yield": 2.5, "market_cap": 580000000000},
    {"ticker": "002594.SZ", "name": "比亚迪", "name_en": "BYD", "market": "A", "exchange": "SZSE", "industry": "汽车", "sector": "新能源汽车", "currency": "CNY", "pe_ttm": 22.1, "pb": 4.8, "dividend_yield": 0.5, "market_cap": 720000000000},
    {"ticker": "601888.SS", "name": "中国中免", "name_en": "China Tourism Group", "market": "A", "exchange": "SSE", "industry": "商贸零售", "sector": "免税", "currency": "CNY", "pe_ttm": 28.6, "pb": 3.5, "dividend_yield": 1.2, "market_cap": 185000000000},

    # A-share 创业板/科创板
    {"ticker": "300750.SZ", "name": "宁德时代", "name_en": "CATL", "market": "A", "exchange": "SZSE", "industry": "电力设备", "sector": "动力电池", "currency": "CNY", "pe_ttm": 18.3, "pb": 4.5, "dividend_yield": 0.8, "market_cap": 1005000000000},
    {"ticker": "300760.SZ", "name": "迈瑞医疗", "name_en": "Mindray", "market": "A", "exchange": "SZSE", "industry": "医药生物", "sector": "医疗器械", "currency": "CNY", "pe_ttm": 32.5, "pb": 9.1, "dividend_yield": 1.0, "market_cap": 350000000000},
    {"ticker": "688981.SS", "name": "中芯国际", "name_en": "SMIC", "market": "A", "exchange": "SSE", "industry": "电子", "sector": "半导体", "currency": "CNY", "pe_ttm": 85.2, "pb": 3.2, "dividend_yield": 0.0, "market_cap": 420000000000},
    {"ticker": "688111.SS", "name": "金山办公", "name_en": "Kingsoft Office", "market": "A", "exchange": "SSE", "industry": "计算机", "sector": "软件", "currency": "CNY", "pe_ttm": 68.5, "pb": 6.8, "dividend_yield": 0.3, "market_cap": 120000000000},
    {"ticker": "002475.SZ", "name": "立讯精密", "name_en": "Luxshare", "market": "A", "exchange": "SZSE", "industry": "电子", "sector": "消费电子", "currency": "CNY", "pe_ttm": 22.1, "pb": 4.2, "dividend_yield": 0.6, "market_cap": 305000000000},

    # HK
    {"ticker": "00700.HK", "name": "腾讯控股", "name_en": "Tencent", "market": "HK", "exchange": "HKEX", "industry": "互联网", "sector": "平台经济", "currency": "HKD", "pe_ttm": 18.5, "pb": 3.8, "dividend_yield": 1.2, "market_cap": 4600000000000},
    {"ticker": "09988.HK", "name": "阿里巴巴-W", "name_en": "Alibaba", "market": "HK", "exchange": "HKEX", "industry": "互联网", "sector": "电商", "currency": "HKD", "pe_ttm": 15.2, "pb": 1.6, "dividend_yield": 1.5, "market_cap": 1650000000000},
    {"ticker": "03690.HK", "name": "美团-W", "name_en": "Meituan", "market": "HK", "exchange": "HKEX", "industry": "互联网", "sector": "本地生活", "currency": "HKD", "pe_ttm": 28.6, "pb": 4.2, "dividend_yield": 0.0, "market_cap": 680000000000},
    {"ticker": "02331.HK", "name": "李宁", "name_en": "Li Ning", "market": "HK", "exchange": "HKEX", "industry": "纺织服饰", "sector": "运动品牌", "currency": "HKD", "pe_ttm": 18.2, "pb": 2.8, "dividend_yield": 2.1, "market_cap": 55000000000},
    {"ticker": "01810.HK", "name": "小米集团-W", "name_en": "Xiaomi", "market": "HK", "exchange": "HKEX", "industry": "电子", "sector": "智能手机", "currency": "HKD", "pe_ttm": 25.8, "pb": 3.5, "dividend_yield": 0.0, "market_cap": 720000000000},

    # US
    {"ticker": "AAPL", "name": "苹果公司", "name_en": "Apple Inc.", "market": "US", "exchange": "NASDAQ", "industry": "科技", "sector": "消费电子", "currency": "USD", "pe_ttm": 32.5, "pb": 48.2, "dividend_yield": 0.5, "market_cap": 3500000000000},
    {"ticker": "NVDA", "name": "英伟达", "name_en": "NVIDIA", "market": "US", "exchange": "NASDAQ", "industry": "科技", "sector": "半导体", "currency": "USD", "pe_ttm": 42.8, "pb": 55.6, "dividend_yield": 0.03, "market_cap": 3380000000000},
    {"ticker": "MSFT", "name": "微软", "name_en": "Microsoft", "market": "US", "exchange": "NASDAQ", "industry": "科技", "sector": "软件", "currency": "USD", "pe_ttm": 35.2, "pb": 12.8, "dividend_yield": 0.7, "market_cap": 3100000000000},
    {"ticker": "BABA", "name": "阿里巴巴", "name_en": "Alibaba Group", "market": "US", "exchange": "NYSE", "industry": "互联网", "sector": "电商", "currency": "USD", "pe_ttm": 15.2, "pb": 1.6, "dividend_yield": 1.5, "market_cap": 218000000000},
    {"ticker": "PDD", "name": "拼多多", "name_en": "PDD Holdings", "market": "US", "exchange": "NASDAQ", "industry": "互联网", "sector": "电商", "currency": "USD", "pe_ttm": 12.8, "pb": 4.5, "dividend_yield": 0.0, "market_cap": 142000000000},
    {"ticker": "TSLA", "name": "特斯拉", "name_en": "Tesla", "market": "US", "exchange": "NASDAQ", "industry": "汽车", "sector": "新能源汽车", "currency": "USD", "pe_ttm": 65.2, "pb": 12.5, "dividend_yield": 0.0, "market_cap": 800000000000},
]

SAMPLE_NEWS = [
    {"title": "央行宣布降准0.5个百分点，释放长期流动性约1万亿元", "source": "财联社", "category": "macro", "impact_level": "high", "sentiment": "positive", "related_tickers": ["000001.SZ", "600036.SS"], "related_sectors": ["银行"]},
    {"title": "半导体设备国产化率突破40%，大基金三期重点布局", "source": "证券时报", "category": "industry", "impact_level": "high", "sentiment": "positive", "related_tickers": ["688981.SS"], "related_sectors": ["半导体"]},
    {"title": "腾讯一季度游戏收入同比增长12%，海外业务持续扩张", "source": "第一财经", "category": "company", "impact_level": "medium", "sentiment": "positive", "related_tickers": ["00700.HK"], "related_sectors": ["互联网"]},
    {"title": "美国PMI数据低于预期，市场对降息预期升温", "source": "华尔街日报", "category": "macro", "impact_level": "medium", "sentiment": "neutral", "related_tickers": ["AAPL", "NVDA"], "related_sectors": ["科技"]},
    {"title": "白酒行业库存压力仍存，头部酒企控量稳价", "source": "界面新闻", "category": "industry", "impact_level": "medium", "sentiment": "negative", "related_tickers": ["600519.SS", "000858.SZ"], "related_sectors": ["白酒"]},
    {"title": "宁德时代发布新一代麒麟电池，能量密度提升15%", "source": "36氪", "category": "company", "impact_level": "medium", "sentiment": "positive", "related_tickers": ["300750.SZ"], "related_sectors": ["动力电池"]},
    {"title": "香港恒生指数突破20000点关口，科技股领涨", "source": "彭博社", "category": "market", "impact_level": "medium", "sentiment": "positive", "related_tickers": ["00700.HK", "09988.HK"], "related_sectors": ["互联网"]},
    {"title": "英伟达新一代AI芯片需求超预期，订单排期至2026年", "source": "路透社", "category": "company", "impact_level": "high", "sentiment": "positive", "related_tickers": ["NVDA"], "related_sectors": ["半导体"]},
    {"title": "医药集采政策趋缓，创新药板块迎来估值修复", "source": "医药经济报", "category": "policy", "impact_level": "medium", "sentiment": "positive", "related_tickers": ["600276.SS", "300760.SZ"], "related_sectors": ["创新药", "医疗器械"]},
    {"title": "美联储维持利率不变，鲍威尔表态偏鹰", "source": "CNBC", "category": "macro", "impact_level": "high", "sentiment": "negative", "related_tickers": ["AAPL", "MSFT", "TSLA"], "related_sectors": ["科技"]},
    {"title": "比亚迪5月销量同比增长25%，海外出口创新高", "source": "汽车之家", "category": "company", "impact_level": "medium", "sentiment": "positive", "related_tickers": ["002594.SZ"], "related_sectors": ["新能源汽车"]},
    {"title": "美团外卖业务利润率持续改善，到店业务复苏", "source": "晚点LatePost", "category": "company", "impact_level": "medium", "sentiment": "positive", "related_tickers": ["03690.HK"], "related_sectors": ["本地生活"]},
    {"title": "中芯国际Q1产能利用率提升至85%，成熟制程订单饱满", "source": "集微网", "category": "company", "impact_level": "medium", "sentiment": "positive", "related_tickers": ["688981.SS"], "related_sectors": ["半导体"]},
    {"title": "李宁发布夏季新品，国潮系列销量超预期", "source": "时尚商业Daily", "category": "company", "impact_level": "low", "sentiment": "positive", "related_tickers": ["02331.HK"], "related_sectors": ["运动品牌"]},
    {"title": "金山办公AI功能月活突破千万，付费转化率提升", "source": "Tech星球", "category": "company", "impact_level": "medium", "sentiment": "positive", "related_tickers": ["688111.SS"], "related_sectors": ["软件"]},
]

DAILY_REVIEW_TEMPLATES = [
    {
        "market": "A",
        "one_sentence_summary": "今日A股市场呈现缩量震荡格局，科技成长板块相对活跃，机器人、半导体方向领涨；地产、消费表现偏弱。短期仍需观察成交额能否持续放大。",
        "market_summary": "今日市场整体呈现分化格局。上证指数小幅上涨0.3%，创业板指微跌0.2%。科技成长方向表现较强，半导体、机器人、AI应用板块领涨，而地产、消费、医药板块承压。",
        "index_summary": "上证指数收报3385点，涨0.3%；深证成指涨0.1%；创业板指跌0.2%；科创50涨1.2%。市场整体呈现沪强深弱格局。",
        "sector_summary": "领涨板块：半导体(+3.2%)、机器人(+2.8%)、AI应用(+2.5%)；领跌板块：白酒(-1.7%)、房地产(-1.5%)、医药商业(-1.2%)。",
        "topic_summary": "今日市场热点集中在AI应用和半导体国产替代，低空经济概念持续活跃。黄金板块受地缘避险情绪推动小幅上涨。",
        "fund_flow_summary": "主力资金净流入科技成长方向，半导体板块净流入45.2亿元。北向资金净流出32亿元，外资对人民币资产仍偏谨慎。",
        "news_summary": "央行降准释放流动性利好、半导体国产化政策、腾讯业绩超预期等利好科技板块；白酒库存压力、地产销售疲软等拖累相关板块。",
        "risk_summary": "当前市场成交量未能有效放大，增量资金有限。部分科技成长股短期涨幅较高，需警惕回调风险。",
        "tomorrow_watchlist": "关注成交额变化、北向资金方向、科技板块持续性、重点公司公告",
    },
    {
        "market": "HK",
        "one_sentence_summary": "港股今日大幅反弹，恒生科技指数涨超2%，腾讯、美团等科网股领涨。南向资金持续流入，市场信心有所恢复。",
        "market_summary": "港股今日强劲反弹，恒生指数涨1.5%，恒生科技指数涨2.1%。科技板块全面上涨，互联网、半导体、新能源汽车表现突出。",
        "index_summary": "恒生指数收报19850点，涨1.5%；恒生科技指数涨2.1%；国企指数涨1.3%。",
        "sector_summary": "领涨：互联网科技(+2.5%)、半导体(+3.1%)、新能源汽车(+1.8%)；领跌：地产(-0.5%)、公用事业(-0.3%)。",
        "topic_summary": "科网股反弹是今日主线，市场期待港股通扩容和美联储降息预期。",
        "fund_flow_summary": "南向资金净流入85亿港元，连续5日净流入。外资通过港股通持续加仓科技和医疗板块。",
        "news_summary": "腾讯业绩超预期、阿里回购进展、美联储降息预期升温等利好港股。",
        "risk_summary": "港股仍受中美关系、美联储政策、地缘政治等外部因素影响，波动性较大。",
        "tomorrow_watchlist": "关注美联储议息会议、南向资金流向、科网股业绩发布",
    },
    {
        "market": "US",
        "one_sentence_summary": "美股三大指数涨跌互现，科技股分化明显。英伟达创新高，苹果小幅回调。市场等待美联储利率决议。",
        "market_summary": "标普500微涨0.1%，纳斯达克跌0.2%，道琼斯涨0.3%。芯片股表现强劲，大型科技股分化。",
        "index_summary": "标普500收报5830点，纳指收报18550点，道指收报42350点。",
        "sector_summary": "领涨：半导体(+2.8%)、能源(+1.2%)；领跌：生物科技(-1.5%)、消费品(-0.8%)。",
        "topic_summary": "AI芯片需求持续旺盛，英伟达订单排期至2026年。市场聚焦下周美联储利率决议。",
        "fund_flow_summary": "机构投资者增持科技股，ETF资金净流入约50亿美元。",
        "news_summary": "英伟达订单超预期、PMI数据低于预期、美联储官员鹰派发言等。",
        "risk_summary": "高估值科技股面临回调压力，地缘风险仍需关注。",
        "tomorrow_watchlist": "关注美联储利率决议、非农就业数据、科技股财报",
    },
]

# ============================================================================
# Seed Functions
# ============================================================================

def seed_stocks(db: Session) -> None:
    """Seed stocks table"""
    existing = {s.ticker for s in db.query(Stock.ticker).all()}
    added = 0
    for data in SAMPLE_STOCKS:
        if data["ticker"] in existing:
            continue
        stock = Stock(**data)
        db.add(stock)
        added += 1
    db.commit()
    print(f"[seed] Stocks: added {added}, skipped {len(SAMPLE_STOCKS) - added}")


def seed_daily_market_data(db: Session, days: int = 30) -> None:
    """Seed 30 days of daily market data for each stock"""
    existing_pairs = set(
        db.query(DailyMarketData.ticker, DailyMarketData.date).all()
    )

    added = 0
    end_date = date.today()

    # Base prices for each ticker
    base_prices = {
        "600519.SS": 1500, "000001.SZ": 11.5, "600036.SS": 35.2, "601318.SS": 48.5,
        "600276.SS": 48.0, "000858.SZ": 145, "002594.SZ": 258, "601888.SS": 72,
        "300750.SZ": 228, "300760.SZ": 285, "688981.SS": 52, "688111.SS": 285,
        "002475.SZ": 42, "00700.HK": 485, "09988.HK": 88, "03690.HK": 125,
        "02331.HK": 18.5, "01810.HK": 18.8, "AAPL": 185, "NVDA": 138,
        "MSFT": 420, "BABA": 88, "PDD": 108, "TSLA": 245,
    }

    for stock_data in SAMPLE_STOCKS:
        ticker = stock_data["ticker"]
        base = base_prices.get(ticker, 100)
        current_price = base

        for i in range(days):
            d = end_date - timedelta(days=i)
            if (ticker, d) in existing_pairs:
                continue

            # Random walk price simulation
            change_pct = random.uniform(-3.5, 3.5)
            open_price = current_price * (1 + random.uniform(-0.8, 0.8) / 100)
            close_price = current_price * (1 + change_pct / 100)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 1.5) / 100)
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 1.5) / 100)
            volume = int(random.uniform(500000, 50000000))
            amount = Decimal(str(close_price * volume))

            daily = DailyMarketData(
                ticker=ticker,
                date=d,
                open=Decimal(str(round(open_price, 4))),
                high=Decimal(str(round(high_price, 4))),
                low=Decimal(str(round(low_price, 4))),
                close=Decimal(str(round(close_price, 4))),
                prev_close=Decimal(str(round(current_price, 4))),
                change=Decimal(str(round(close_price - current_price, 4))),
                change_pct=Decimal(str(round(change_pct, 4))),
                volume=volume,
                amount=amount,
                turnover_rate=Decimal(str(round(random.uniform(0.5, 8.0), 4))),
            )
            db.add(daily)
            added += 1
            current_price = close_price

    db.commit()
    print(f"[seed] DailyMarketData: added {added} records")


def seed_news(db: Session) -> None:
    """Seed news items"""
    existing_titles = {n.title for n in db.query(News.title).all()}
    added = 0
    for data in SAMPLE_NEWS:
        if data["title"] in existing_titles:
            continue
        news = News(
            title=data["title"],
            source=data["source"],
            category=data["category"],
            impact_level=data["impact_level"],
            sentiment=data["sentiment"],
            related_tickers=data["related_tickers"],
            related_sectors=data["related_sectors"],
            publish_time=datetime.now() - timedelta(hours=random.randint(1, 72)),
            content=data["title"] + "\n\n（此为示例新闻内容，实际系统会抓取完整新闻正文。）",
            url="https://example.com/news/" + str(random.randint(10000, 99999)),
        )
        db.add(news)
        added += 1
    db.commit()
    print(f"[seed] News: added {added}, skipped {len(SAMPLE_NEWS) - added}")


def seed_daily_reviews(db: Session, days: int = 30) -> None:
    """Seed daily reviews"""
    existing_dates = {(r.date, r.market) for r in db.query(DailyReview.date, DailyReview.market).all()}
    added = 0
    end_date = date.today()

    for i in range(days):
        d = end_date - timedelta(days=i)
        for template in DAILY_REVIEW_TEMPLATES:
            market = template["market"]
            if (d, market) in existing_dates:
                continue

            # Slightly vary the content by day
            day_offset = i % 3
            summary = template["one_sentence_summary"]
            if day_offset == 1:
                summary = summary.replace("缩量震荡", "放量上涨")
            elif day_offset == 2:
                summary = summary.replace("缩量震荡", "震荡调整")

            review = DailyReview(
                date=d,
                market=market,
                one_sentence_summary=summary,
                market_summary=template["market_summary"],
                index_summary=template["index_summary"],
                sector_summary=template["sector_summary"],
                topic_summary=template["topic_summary"],
                fund_flow_summary=template["fund_flow_summary"],
                news_summary=template["news_summary"],
                risk_summary=template["risk_summary"],
                tomorrow_watchlist=template["tomorrow_watchlist"],
                ai_generated=True,
            )
            db.add(review)
            added += 1

    db.commit()
    print(f"[seed] DailyReview: added {added} records")


def seed_users_and_portfolios(db: Session) -> None:
    """Seed a demo user with sample portfolio and watchlist"""
    from app.core.security import get_password_hash

    # Check if demo user exists
    demo_user = db.query(User).filter(User.username == "demo").first()
    if not demo_user:
        demo_user = User(
            email="demo@ai-berkshire.com",
            username="demo",
            hashed_password=get_password_hash("demo123456"),
            full_name="Demo Investor",
            risk_level="balanced",
            investor_type="value_growth",
            investment_experience="intermediate",
            max_drawdown_tolerance=20.0,
            investment_horizon="medium",
            is_active=True,
            is_admin=False,
            membership="free",
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        print(f"[seed] Created demo user (id={demo_user.id})")
    else:
        print(f"[seed] Demo user already exists (id={demo_user.id})")

    # Seed watchlist
    watchlist_tickers = [
        ("600519.SS", "长期持有，目标价1800", 1800, 1400),
        ("00700.HK", "游戏出海+视频号", 520, 450),
        ("300750.SZ", "动力电池龙头", 280, 200),
        ("NVDA", "AI算力核心", 160, 120),
        ("002594.SZ", "新能源汽车龙头", 300, 220),
    ]
    existing_wl = {w.ticker for w in db.query(Watchlist).filter(Watchlist.user_id == demo_user.id).all()}
    added_wl = 0
    for ticker, note, target, alert in watchlist_tickers:
        if ticker in existing_wl:
            continue
        db.add(Watchlist(
            user_id=demo_user.id,
            ticker=ticker,
            note=note,
            target_price=Decimal(str(target)),
            alert_price=Decimal(str(alert)),
        ))
        added_wl += 1
    db.commit()
    print(f"[seed] Watchlist: added {added_wl}")

    # Seed portfolio
    portfolio_items = [
        ("600519.SS", "贵州茅台", 100, Decimal("1450"), date(2023, 5, 15), "白酒龙头，品牌护城河深厚", Decimal("0.25")),
        ("00700.HK", "腾讯控股", 500, Decimal("420"), date(2023, 8, 20), "平台经济+游戏出海+视频号", Decimal("0.20")),
        ("300750.SZ", "宁德时代", 200, Decimal("210"), date(2024, 1, 10), "动力电池全球龙头", Decimal("0.15")),
        ("600036.SS", "招商银行", 1000, Decimal("32"), date(2023, 3, 5), "零售银行标杆，高股息", Decimal("0.10")),
        ("002475.SZ", "立讯精密", 500, Decimal("38"), date(2024, 2, 18), "消费电子+汽车电子双轮驱动", Decimal("0.08")),
    ]
    existing_pf = {p.ticker for p in db.query(Portfolio).filter(Portfolio.user_id == demo_user.id).all()}
    added_pf = 0
    for ticker, name, qty, cost, buy_date, thesis, weight in portfolio_items:
        if ticker in existing_pf:
            continue
        db.add(Portfolio(
            user_id=demo_user.id,
            ticker=ticker,
            name=name,
            quantity=Decimal(str(qty)),
            avg_cost=cost,
            buy_date=buy_date,
            thesis=thesis,
            target_weight=weight,
            stop_condition="基本面恶化或估值过高",
        ))
        added_pf += 1
    db.commit()
    print(f"[seed] Portfolio: added {added_pf}")

    # Seed asset allocations
    alloc_items = [
        ("stock", "A股", 450000, "CNY", "medium", "medium", Decimal("0.45")),
        ("stock", "港股", 200000, "CNY", "medium", "medium", Decimal("0.20")),
        ("stock", "美股", 100000, "USD", "medium", "medium", Decimal("0.10")),
        ("cash", "货币基金", 150000, "CNY", "high", "low", Decimal("0.15")),
        ("bond", "债券基金", 100000, "CNY", "low", "low", Decimal("0.10")),
    ]
    existing_alloc = {a.asset_type for a in db.query(AssetAllocation).filter(AssetAllocation.user_id == demo_user.id).all()}
    added_alloc = 0
    for asset_type, name, amount, currency, liquidity, risk, target in alloc_items:
        if asset_type in existing_alloc:
            continue
        db.add(AssetAllocation(
            user_id=demo_user.id,
            asset_type=asset_type,
            asset_name=name,
            amount=Decimal(str(amount)),
            currency=currency,
            liquidity_level=liquidity,
            risk_level=risk,
            target_ratio=target,
        ))
        added_alloc += 1
    db.commit()
    print(f"[seed] AssetAllocation: added {added_alloc}")

    # Seed investment journals
    journal_items = [
        (date(2023, 5, 15), "600519.SS", "buy", Decimal("1450"), 100, Decimal("0.25"), "白酒龙头回调，长期配置", "品牌护城河", "业绩增速放缓或估值过高", "calm"),
        (date(2023, 8, 20), "00700.HK", "buy", Decimal("420"), 500, Decimal("0.20"), "游戏版号恢复，估值修复", "监管政策", "监管加码或游戏收入下滑", "optimistic"),
        (date(2024, 1, 10), "300750.SZ", "buy", Decimal("210"), 200, Decimal("0.15"), "动力电池需求持续增长", "技术迭代风险", "市场份额下滑", "cautious"),
        (date(2024, 3, 5), None, "review", None, None, None, "本月组合表现平稳，茅台贡献主要收益", None, None, "calm"),
        (date(2024, 6, 15), "002475.SZ", "buy", Decimal("38"), 500, Decimal("0.08"), "Vision Pro供应链+汽车电子", "客户集中度", "大客户订单流失", "calm"),
    ]
    existing_journals = db.query(InvestmentJournal).filter(InvestmentJournal.user_id == demo_user.id).count()
    if existing_journals == 0:
        for d, ticker, action, price, qty, weight, reason, thesis, exit_cond, emotion in journal_items:
            db.add(InvestmentJournal(
                user_id=demo_user.id,
                date=d,
                ticker=ticker,
                action=action,
                price=price,
                quantity=Decimal(str(qty)) if qty else None,
                weight=weight,
                reason=reason,
                thesis=thesis,
                exit_condition=exit_cond,
                emotion=emotion,
            ))
        db.commit()
        print(f"[seed] InvestmentJournal: added {len(journal_items)}")
    else:
        print(f"[seed] InvestmentJournal: skipped (already has {existing_journals} records)")


def seed_index_and_sector_data(db: Session, days: int = 30) -> None:
    """Seed index and sector data"""
    indices = [
        {"code": "000001", "name": "上证指数", "market": "A"},
        {"code": "399001", "name": "深证成指", "market": "A"},
        {"code": "399006", "name": "创业板指", "market": "A"},
        {"code": "HSI", "name": "恒生指数", "market": "HK"},
        {"code": "SPX", "name": "标普500", "market": "US"},
    ]
    sectors = [
        "半导体", "机器人", "AI应用", "创新药", "低空经济",
        "白酒", "房地产", "医药商业", "银行", "煤炭",
    ]

    existing_idx = set(db.query(IndexData.index_code, IndexData.date).all())
    existing_sec = set(db.query(SectorData.sector_name, SectorData.date).all())

    end_date = date.today()
    added_idx = 0
    added_sec = 0

    for i in range(days):
        d = end_date - timedelta(days=i)

        for idx in indices:
            if (idx["code"], d) in existing_idx:
                continue
            base_close = random.uniform(3000, 4000) if idx["market"] == "A" else (random.uniform(18000, 22000) if idx["market"] == "HK" else random.uniform(4500, 6000))
            change_pct = random.uniform(-1.5, 1.5)
            db.add(IndexData(
                index_code=idx["code"],
                index_name=idx["name"],
                date=d,
                close=Decimal(str(round(base_close * (1 + change_pct/100), 4))),
                change_pct=Decimal(str(round(change_pct, 4))),
                amount=Decimal(str(round(random.uniform(1000, 5000), 4))),
                market=idx["market"],
            ))
            added_idx += 1

        for sec in sectors:
            if (sec, d) in existing_sec:
                continue
            db.add(SectorData(
                sector_name=sec,
                date=d,
                change_pct=Decimal(str(round(random.uniform(-3, 4), 4))),
                amount=Decimal(str(round(random.uniform(100, 800), 4))),
                net_inflow=Decimal(str(round(random.uniform(-50, 60), 4))),
                leading_stocks=[random.choice(["600519.SS", "00700.HK", "300750.SZ", "688981.SS"])],
            ))
            added_sec += 1

    db.commit()
    print(f"[seed] IndexData: added {added_idx}, SectorData: added {added_sec}")


# ============================================================================
# Main Entry Point
# ============================================================================

def seed_all() -> None:
    """Run all seed operations"""
    print("=" * 50)
    print("AI Berkshire Database Seeder")
    print("=" * 50)

    db = SessionLocal()
    try:
        seed_stocks(db)
        seed_daily_market_data(db, days=30)
        seed_news(db)
        seed_daily_reviews(db, days=30)
        seed_index_and_sector_data(db, days=30)
        seed_users_and_portfolios(db)
        print("=" * 50)
        print("Seeding completed successfully!")
        print("=" * 50)
    except Exception as e:
        db.rollback()
        print(f"[seed] Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
