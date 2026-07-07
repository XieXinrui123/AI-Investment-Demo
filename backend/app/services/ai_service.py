import os
import json
import httpx
from typing import List, Optional, Dict, Any
from datetime import date

from app.core.config import get_settings

settings = get_settings()

class AIService:
    """AI服务层 - 集成ai-berkshire的投研框架"""
    
    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.api_key = settings.OPENAI_API_KEY if self.provider == "openai" else settings.DEEPSEEK_API_KEY
        self.model = settings.AI_MODEL
    
    async def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """调用大语言模型"""
        if not self.api_key:
            # 模拟AI回复（当没有API key时）
            return self._mock_response(system_prompt, user_prompt)
        
        try:
            if self.provider == "openai":
                return await self._call_openai(system_prompt, user_prompt, temperature)
            else:
                return await self._call_deepseek(system_prompt, user_prompt, temperature)
        except Exception as e:
            print(f"AI API error: {e}")
            return self._mock_response(system_prompt, user_prompt)
    
    async def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 4000,
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _call_deepseek(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 4000,
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _mock_response(self, system_prompt: str, user_prompt: str) -> str:
        """模拟AI回复（无API key时）"""
        # 根据prompt类型返回不同的模拟回复
        if "每日市场复盘" in user_prompt or "market review" in system_prompt.lower():
            return """今日A股市场呈现分化格局。上证指数小幅收涨，科技成长方向表现较强，半导体、机器人、AI应用板块领涨；地产、消费和医药板块承压。成交额较前一交易日有所萎缩，说明增量资金仍然有限。短期市场仍需观察成交额能否持续放大，以及领涨板块是否具备持续性。

**风险提示**：当前市场成交量未能有效放大，部分科技成长股短期涨幅较高，需警惕回调风险。"""
        
        elif "个股" in user_prompt or "stock" in system_prompt.lower():
            return """该股今日上涨1.21%，主要受板块整体反弹带动。公司暂无重大公告，市场关注点集中在业务恢复进展。当前估值处于近三年中低分位，适合作为长期观察标的，但短期仍需关注市场流动性和行业走势。

**风险提示**：短期涨幅后可能面临技术性回调，需关注后续成交量变化。"""
        
        elif "Checklist" in system_prompt or "checklist" in user_prompt.lower():
            return json.dumps({
                "company": "腾讯控股",
                "passed": False,
                "score": 4.0,
                "scores": {
                    "capability": 4,
                    "business": 5,
                    "moat": 4,
                    "management": 4,
                    "valuation": 4,
                },
                "conclusion": "灰色地带",
                "reason": "商业模式优秀，管理层值得信赖，但估值安全边际一般，建议等待更好的买入时机。"
            })
        
        elif "公告" in user_prompt or "announcement" in system_prompt.lower():
            return """**公告类型**: 大股东减持

**一句话摘要**: 公司大股东拟减持不超过2%股份

**关键事实**: 
- 减持比例不超过总股本的2%
- 减持方式为集中竞价和大宗交易
- 减持期限为6个月

**利好因素**: 
- 减持比例相对有限
- 公司基本面未发生变化

**利空因素**: 
- 短期可能压制市场情绪
- 在股价已有较大涨幅的情况下，减持信号偏负面

**风险提示**: 需关注减持节奏和市场承接能力
"""
        
        return """根据当前数据，该标的处于观察区间。建议持续关注基本面变化和估值水平，不急于做出投资决策。"""
    
    # ==================== AI Berkshire Skills Integration ====================
    
    async def generate_daily_review(self, market: str = "A") -> Dict[str, Any]:
        """生成每日市场复盘 - 对应PRD 8.2"""
        system_prompt = """你是一名专业股票市场复盘分析师。请根据以下数据生成每日市场复盘。

要求：
- 不给出确定性买卖建议
- 不使用"必涨""一定"等表达
- 明确区分事实、推测和风险
- 语言专业、简洁、适合个人投资者阅读"""
        
        from app.services.market_service import MarketService
        market_service = MarketService()
        overview = await market_service.get_market_overview(market)
        
        user_prompt = f"""请生成{market}股市场每日复盘：
指数表现：{json.dumps(overview['indices'], ensure_ascii=False)}
上涨家数：{overview['up_count']}，下跌家数：{overview['down_count']}
涨停数：{overview['limit_up_count']}，跌停数：{overview['limit_down_count']}
成交额：{overview['total_amount']}亿元
领涨板块：{json.dumps(overview['sectors_up'], ensure_ascii=False)}
领跌板块：{json.dumps(overview['sectors_down'], ensure_ascii=False)}
热门题材：{json.dumps(overview['hot_topics'], ensure_ascii=False)}

请输出：
1. 今日市场一句话总结
2. 市场整体表现
3. 指数表现解读
4. 领涨板块原因
5. 领跌板块原因
6. 风险提示
7. 明日关注点"""
        
        response = await self._call_llm(system_prompt, user_prompt)
        return {
            "date": date.today().isoformat(),
            "market": market,
            "ai_generated": True,
            "content": response,
            "one_sentence_summary": self._extract_first_line(response),
        }
    
    async def generate_stock_review(self, ticker: str) -> Dict[str, Any]:
        """生成个股复盘 - 对应PRD 9.5"""
        system_prompt = """你是一名股票研究助理。请根据股票行情、公告、新闻数据，生成该股票的每日复盘。

要求：
- 不直接推荐买入或卖出
- 使用审慎语言
- 给出观察框架
- 明确事实来源和推测部分"""
        
        from app.services.market_service import MarketService
        market_service = MarketService()
        stock_data = await market_service.get_stock_detail(ticker)
        
        user_prompt = f"""请生成{ticker}({stock_data.get('name', '')})的每日复盘：
当前价格：{stock_data.get('price', 'N/A')}
涨跌幅：{stock_data.get('change_pct', 'N/A')}%
PE(TTM)：{stock_data.get('pe', 'N/A')}
市值：{stock_data.get('market_cap', 'N/A')}亿

请输出：
1. 今日涨跌情况
2. 可能原因
3. 基本面是否发生变化
4. 估值是否处于高位
5. 后续需要观察的指标
6. 风险提示"""
        
        response = await self._call_llm(system_prompt, user_prompt)
        return {
            "ticker": ticker,
            "date": date.today().isoformat(),
            "content": response,
        }
    
    async def analyze_announcement(self, content: str, announcement_type: Optional[str] = None) -> Dict[str, Any]:
        """公告/财报解读 - 对应PRD 13"""
        system_prompt = """你是一名上市公司公告分析师。请阅读以下公告内容，并输出结构化解读。

要求：
- 保持客观
- 不夸大影响
- 不做确定性股价预测
- 明确区分事实和判断"""
        
        user_prompt = f"""请解读以下公告：
公告类型：{announcement_type or '未知'}

公告内容：
{content[:8000]}

请输出：
1. 公告类型
2. 一句话摘要
3. 关键事实
4. 潜在利好
5. 潜在利空
6. 对短期市场情绪的影响
7. 对长期基本面的影响
8. 需要继续观察的事项
9. 风险提示"""
        
        response = await self._call_llm(system_prompt, user_prompt)
        return self._parse_announcement_analysis(response)
    
    async def chat(self, question: str, context_type: Optional[str] = None, 
                   related_tickers: Optional[List[str]] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """AI投研助手问答 - 对应PRD 12"""
        system_prompt = """你是一名专业的AI投研助手。请根据用户的问题，提供结构化的投资分析。

回答必须使用固定结构：
1. 结论
2. 事实依据
3. 可能原因
4. 风险提示
5. 后续观察点

限制：
- 不得使用"必涨""一定会跌""马上买入""稳赚"等表达
- 应使用"可能""需要观察""从当前数据看""仍存在风险""不构成投资建议"""
        
        user_prompt = f"""用户问题：{question}
上下文类型：{context_type or '一般'}
相关标的：{', '.join(related_tickers) if related_tickers else '无'}

请提供专业、审慎的回答。"""
        
        response = await self._call_llm(system_prompt, user_prompt)
        return {
            "answer": response,
            "conclusion": self._extract_conclusion(response),
            "facts": self._extract_facts(response),
            "risks": self._extract_risks(response),
            "watchpoints": self._extract_watchpoints(response),
            "related_tickers": related_tickers or [],
        }
    
    async def review_portfolio(self, items: List) -> Dict[str, Any]:
        """持仓组合AI复盘"""
        if not items:
            return {"message": "暂无持仓数据", "suggestions": []}
        
        system_prompt = """你是一名组合风险分析师。请根据用户持仓数据，分析当前组合风险。

要求：
- 不提供具体买卖指令
- 只提供风险识别和观察建议
- 用审慎、专业语言表达"""
        
        portfolio_text = "\n".join([
            f"{item.ticker}: 数量{item.quantity}, 成本{item.avg_cost}" 
            for item in items
        ])
        
        user_prompt = f"""请分析以下持仓组合的风险：

{portfolio_text}

请输出：
1. 当前组合结构
2. 集中度风险
3. 主要风险来源
4. 风险控制建议"""
        
        response = await self._call_llm(system_prompt, user_prompt)
        return {"analysis": response, "suggestions": []}
    
    async def review_behavior(self, journals: List, current_journal=None) -> str:
        """投资行为AI复盘"""
        system_prompt = """你是一名投资行为复盘教练。请根据用户投资日志，分析其投资行为模式。

要求：
- 关注行为和纪律
- 不评价用户能力
- 不给出确定性投资建议"""
        
        journal_text = "\n".join([
            f"日期: {j.date}, 标的: {j.ticker or 'N/A'}, 操作: {j.action}, 理由: {j.reason or 'N/A'}"
            for j in journals[:20]
        ])
        
        user_prompt = f"""请分析以下投资行为：

{journal_text}

请输出：
1. 交易概况
2. 盈利/亏损交易共性
3. 是否存在追涨杀跌
4. 是否存在频繁交易
5. 下月需要改进的行为"""
        
        return await self._call_llm(system_prompt, user_prompt)
    
    async def analyze_asset_allocation(self, allocations: List, risk_level: str = "balanced") -> Dict[str, Any]:
        """资产配置AI分析"""
        system_prompt = """你是一名资产配置顾问。请根据用户的资产配置情况，提供分析建议。

要求：
- 不提供具体产品推荐
- 关注大类资产配置合理性
- 用审慎、专业语言表达"""
        
        alloc_text = "\n".join([
            f"{a.asset_type}: {float(a.amount) if a.amount else 0} {a.currency}"
            for a in allocations
        ])
        
        user_prompt = f"""风险偏好：{risk_level}

资产配置：
{alloc_text}

请分析：
1. 当前资产结构特点
2. 主要风险
3. 流动性是否充足
4. 是否需要再平衡"""
        
        response = await self._call_llm(system_prompt, user_prompt)
        return {"analysis": response}
    
    async def investment_checklist(self, ticker: str) -> Dict[str, Any]:
        """巴菲特六关Checklist - 对应ai-berkshire investment-checklist skill"""
        system_prompt = """你是巴菲特价值投资分析师。请对以下标的执行六关Checklist分析。

六关：
1. 我能理解这门生意吗（能力圈）
2. 这是一门好生意吗（经济特征）
3. 护城河够不够深（竞争优势）
4. 管理层是否值得信任（人的因素）
5. 价格是否足够便宜（安全边际）
6. 仓位与决策纪律（防止情绪失控）

评分标准（1-5星）：
最后输出：是否通过Checklist、综合评分、核心结论"""
        
        user_prompt = f"""请对{ticker}执行巴菲特六关Checklist分析。

要求：
- 宁可错过，不可做错
- 诚实面对能力圈
- 安全边际是生命线"""
        
        response = await self._call_llm(system_prompt, user_prompt)
        return {
            "ticker": ticker,
            "checklist_result": response,
        }
    
    # ==================== File Processing ====================
    
    async def extract_pdf_text(self, file_path: str) -> str:
        """提取PDF文本"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            return f"PDF解析失败: {str(e)}"
    
    async def extract_docx_text(self, file_path: str) -> str:
        """提取DOCX文本"""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            return f"DOCX解析失败: {str(e)}"
    
    # ==================== Helper Methods ====================
    
    def _extract_first_line(self, text: str) -> str:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        return lines[0] if lines else ""
    
    def _extract_conclusion(self, text: str) -> str:
        # Simple extraction - in production, use structured output
        if "结论" in text:
            idx = text.find("结论")
            end = text.find("\n", idx + 10)
            return text[idx:end] if end > idx else text[idx:idx+200]
        return ""
    
    def _extract_facts(self, text: str) -> List[str]:
        facts = []
        for line in text.split('\n'):
            if any(k in line for k in ["事实", "数据", "收入", "利润", "PE", "市值"]):
                facts.append(line.strip())
        return facts[:5]
    
    def _extract_risks(self, text: str) -> List[str]:
        risks = []
        for line in text.split('\n'):
            if any(k in line for k in ["风险", "警惕", "注意", "不确定性"]):
                risks.append(line.strip())
        return risks[:5]
    
    def _extract_watchpoints(self, text: str) -> List[str]:
        points = []
        for line in text.split('\n'):
            if any(k in line for k in ["观察", "关注", "跟踪", "后续"]):
                points.append(line.strip())
        return points[:5]
    
    def _parse_announcement_analysis(self, text: str) -> Dict[str, Any]:
        """解析公告分析文本为结构化数据"""
        return {
            "summary": self._extract_first_line(text),
            "key_facts": self._extract_facts(text),
            "positive_factors": self._extract_items_after_keyword(text, "利好"),
            "negative_factors": self._extract_items_after_keyword(text, "利空"),
            "short_term_impact": "短期影响需观察市场情绪",
            "long_term_impact": "长期影响取决于基本面变化",
            "portfolio_impact": "建议结合持仓逻辑判断",
            "watchpoints": self._extract_watchpoints(text),
            "risk_warning": "本分析不构成投资建议",
        }
    
    def _extract_items_after_keyword(self, text: str, keyword: str) -> List[str]:
        items = []
        lines = text.split('\n')
        capturing = False
        for line in lines:
            if keyword in line and not capturing:
                capturing = True
            elif capturing:
                if line.strip().startswith('-') or line.strip().startswith('•'):
                    items.append(line.strip().lstrip('-• '))
                elif not line.strip() or any(k in line for k in ["影响", "结论", "风险"]):
                    break
        return items[:5]
