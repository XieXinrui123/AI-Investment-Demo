"""
AI Berkshire Skills - 投研框架核心技能模块

整合 ai-berkshire 研究框架的五大核心技能：
1. InvestmentTeamSkill - 四视角分析（段永平/商业、巴菲特/财务、芒格/竞争、李录/风险）
2. PortfolioReviewSkill - 持仓组合健康检查
3. NewsPulseSkill - 新闻舆情与价格归因
4. InvestmentChecklistSkill - 巴菲特六关Checklist
5. EarningsReviewSkill - 财报深度解读
"""

import json
import re
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date, datetime

from app.services.ai_service import AIService
from app.utils.financial_rigor import (
    verify_market_cap,
    verify_valuation,
    cross_validate,
    three_scenario_valuation,
)


# ============================================================================
# Base Skill
# ============================================================================

class BaseSkill:
    """所有AI技能的基类"""

    def __init__(self, ai_service: Optional[AIService] = None):
        self.ai = ai_service or AIService()

    def _safe_json_parse(self, text: str) -> Dict[str, Any]:
        """安全解析JSON，失败时返回包含原始文本的字典"""
        # 尝试提取JSON代码块
        code_block = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if code_block:
            text = code_block.group(1)
        else:
            # 尝试提取花括号包裹的内容
            brace_match = re.search(r"\{.*\}", text, re.DOTALL)
            if brace_match:
                text = brace_match.group(0)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text, "parse_error": True}

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """从Markdown文本中提取带标题的章节"""
        sections = {}
        current_key = "overview"
        current_lines = []

        for line in text.splitlines():
            header_match = re.match(r"^(#{1,3})\s*(.+)", line)
            if header_match:
                if current_lines:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = header_match.group(2).strip().strip("*")
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections[current_key] = "\n".join(current_lines).strip()

        return sections


# ============================================================================
# 1. InvestmentTeamSkill - 四视角投研分析
# ============================================================================

class InvestmentTeamSkill(BaseSkill):
    """
    投资团队四视角分析
    - 段永平视角：商业本质、企业文化、做对的事情
    - 巴菲特视角：财务指标、ROE、自由现金流、安全边际
    - 芒格视角：竞争优势、护城河、逆向思维
    - 李录视角：风险识别、尾部风险、宏观环境
    """

    async def analyze(
        self,
        ticker: str,
        name: str = "",
        price: Optional[float] = None,
        pe_ttm: Optional[float] = None,
        pb: Optional[float] = None,
        roe: Optional[float] = None,
        market_cap: Optional[float] = None,
        industry: Optional[str] = None,
        business_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行四视角分析，返回结构化JSON结果
        """
        system_prompt = """你是AI伯克希尔投资研究团队，由四位顶尖投资人组成：

1. **段永平**（商业视角）：关注商业本质、企业文化、"做对的事情"、长期主义
2. **巴菲特**（财务视角）：关注ROE、自由现金流、毛利率、安全边际、估值
3. **芒格**（竞争视角）：关注护城河、竞争优势、能力圈、多元思维模型
4. **李录**（风险视角）：关注尾部风险、宏观环境、政策风险、黑天鹅

请对标的进行四视角分析，输出严格JSON格式：

{
  "ticker": "股票代码",
  "name": "公司名称",
  "overall_score": 0,
  "overall_conclusion": "总体结论（灰色地带/通过/不通过）",
  "perspectives": {
    "duan_yongping": {
      "score": 0,
      "business_quality": "商业本质评价",
      "culture": "企业文化评价",
      "long_term_outlook": "长期 outlook",
      "concerns": ["关注点1", "关注点2"],
      "verdict": "结论"
    },
    "buffett": {
      "score": 0,
      "roe_analysis": "ROE分析",
      "cash_flow": "现金流分析",
      "margin_safety": "安全边际评估",
      "valuation": "估值评价",
      "concerns": ["关注点1"],
      "verdict": "结论"
    },
    "munger": {
      "score": 0,
      "moat": "护城河分析",
      "competitive_position": "竞争地位",
      "capability_circle": "能力圈判断",
      "concerns": ["关注点1"],
      "verdict": "结论"
    },
    "li_lu": {
      "score": 0,
      "tail_risks": ["风险1", "风险2"],
      "macro_sensitivity": "宏观敏感度",
      "policy_risk": "政策风险",
      "margin_of_safety_risk": "安全边际风险",
      "verdict": "结论"
    }
  },
  "key_metrics": {
    "pe_ttm": 0,
    "pb": 0,
    "roe": 0,
    "market_cap": 0
  },
  "watchpoints": ["观察点1", "观察点2"],
  "risk_warning": "风险提示"
}

评分标准：1-5分，5分最优。总体结论：通过(>=4.0)、灰色地带(3.0-4.0)、不通过(<3.0)。"""

        user_prompt = f"""请对以下标的进行四视角深度分析：

**标的**：{ticker} {name}
**行业**：{industry or '未知'}
**当前价格**：{price or '未知'}
**PE(TTM)**：{pe_ttm or '未知'}
**PB**：{pb or '未知'}
**ROE**：{roe or '未知'}
**市值**：{market_cap or '未知'}亿

**业务概要**：
{business_summary or '请基于公开信息分析'}

要求：
- 每个视角给出1-5分评分和详细理由
- 明确指出能力圈边界（哪些能看懂，哪些看不懂）
- 不给出确定性买卖建议
- 明确区分事实和推测"""

        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.3)
        parsed = self._safe_json_parse(response)

        # 补充元数据
        if isinstance(parsed, dict) and not parsed.get("parse_error"):
            parsed["ticker"] = ticker
            parsed["analysis_date"] = date.today().isoformat()
            parsed["skill"] = "investment_team"

        return parsed

    async def quick_screen(self, ticker: str) -> Dict[str, Any]:
        """快速筛选：四视角精简版"""
        system_prompt = """你是AI投资筛选助手。请对标的进行快速四视角筛选，输出JSON：
{"passed": false, "scores": {"duan":0,"buffett":0,"munger":0,"li_lu":0}, 
 "bottleneck": "最弱环节", "verdict": "结论"}"""

        user_prompt = f"请对 {ticker} 进行快速四视角筛选，判断是否在能力圈内、是否有明显硬伤。"
        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.3)
        return self._safe_json_parse(response)


# ============================================================================
# 2. PortfolioReviewSkill - 持仓组合健康检查
# ============================================================================

class PortfolioReviewSkill(BaseSkill):
    """
    持仓组合健康检查
    - 集中度分析
    - 相关性检查
    - 机会成本分析
    - 组合再平衡建议
    """

    async def analyze(
        self,
        holdings: List[Dict[str, Any]],
        total_assets: Optional[float] = None,
        risk_tolerance: str = "balanced",
    ) -> Dict[str, Any]:
        """
        执行持仓组合健康检查

        holdings: [{"ticker": "", "name": "", "quantity": 0, "avg_cost": 0, "current_price": 0, "market_value": 0, "weight": 0, "sector": "", "thesis": ""}]
        """
        if not holdings:
            return {
                "status": "empty",
                "message": "暂无持仓数据",
                "risk_level": "low",
                "suggestions": [],
            }

        # 先进行定量计算
        quant = self._quantitative_analysis(holdings, total_assets)

        system_prompt = """你是AI投资组合分析师。请根据持仓数据进行组合健康检查。

输出严格JSON格式：
{
  "overall_health": "healthy/caution/danger",
  "health_score": 0,
  "concentration": {
    "max_single_weight": 0,
    "top3_weight": 0,
    "top5_weight": 0,
    "risk_level": "low/medium/high",
    "assessment": "集中度评价"
  },
  "sector_analysis": {
    "sector_breakdown": {"行业名": 0.35},
    "overexposed_sectors": ["行业名"],
    "missing_sectors": ["行业名"]
  },
  "correlation_concerns": ["相关性风险1"],
  "opportunity_cost": {
    "cash_drag": "现金拖累评估",
    "underperformers": ["ticker"],
    "replacement_candidates": "潜在替代思路"
  },
  "risk_assessment": {
    "level": "low/medium/high",
    "key_risks": ["风险1", "风险2"],
    "tail_risk_exposure": "尾部风险暴露"
  },
  "rebalance_suggestions": [
    {"ticker": "", "action": "reduce/add/hold", "reason": "", "suggested_weight": 0}
  ],
  "behavior_notes": ["行为纪律提示1"],
  "summary": "总体评价"
}

限制：
- 不给出具体买卖指令
- 不提供确定性预测
- 只提供风险识别和观察建议"""

        holdings_text = json.dumps(holdings, ensure_ascii=False, indent=2)
        user_prompt = f"""请分析以下持仓组合：

**总持仓价值**：{quant['total_value']:.2f} 万元
**现金/总资产比例**：{quant['cash_ratio']*100:.1f}%
**风险承受度**：{risk_tolerance}

**持仓明细**：
{holdings_text}

**定量指标**：
- 最大单一持仓占比：{quant['max_weight']*100:.1f}%
- 前三大持仓占比：{quant['top3_weight']*100:.1f}%
- 盈利持仓数：{quant['winning_count']}
- 亏损持仓数：{quant['losing_count']}
- 平均仓位盈亏：{quant['avg_pnl_pct']:.1f}%

请输出组合健康检查报告。"""

        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.3)
        parsed = self._safe_json_parse(response)

        if isinstance(parsed, dict) and not parsed.get("parse_error"):
            parsed["quantitative"] = quant
            parsed["analysis_date"] = date.today().isoformat()
            parsed["skill"] = "portfolio_review"
        else:
            # Fallback with quant data
            parsed = {
                "raw_response": response,
                "quantitative": quant,
                "analysis_date": date.today().isoformat(),
                "skill": "portfolio_review",
            }

        return parsed

    def _quantitative_analysis(self, holdings: List[Dict], total_assets: Optional[float]) -> Dict:
        """持仓定量分析"""
        total_value = sum(h.get("market_value", 0) for h in holdings)
        total_cost = sum(h.get("quantity", 0) * h.get("avg_cost", 0) for h in holdings)
        total_pnl = total_value - total_cost
        avg_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        weights = [h.get("weight", 0) for h in holdings if h.get("market_value", 0) > 0]
        sorted_weights = sorted(weights, reverse=True)

        max_weight = sorted_weights[0] if weights else 0
        top3_weight = sum(sorted_weights[:3]) if len(sorted_weights) >= 3 else sum(sorted_weights)

        winning = [h for h in holdings if h.get("pnl_pct", 0) > 0]
        losing = [h for h in holdings if h.get("pnl_pct", 0) < 0]

        cash_ratio = 0
        if total_assets and total_assets > total_value:
            cash_ratio = (total_assets - total_value) / total_assets

        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_pct": round(avg_pnl_pct, 2),
            "max_weight": round(max_weight, 4),
            "top3_weight": round(top3_weight, 4),
            "winning_count": len(winning),
            "losing_count": len(losing),
            "cash_ratio": round(cash_ratio, 4),
            "holding_count": len(holdings),
        }

    async def concentration_check(self, holdings: List[Dict]) -> Dict[str, Any]:
        """集中度快速检查"""
        quant = self._quantitative_analysis(holdings, None)

        risk_level = "low"
        if quant["max_weight"] > 0.40 or quant["top3_weight"] > 0.70:
            risk_level = "high"
        elif quant["max_weight"] > 0.25 or quant["top3_weight"] > 0.50:
            risk_level = "medium"

        return {
            "max_single_weight": quant["max_weight"],
            "top3_weight": quant["top3_weight"],
            "risk_level": risk_level,
            "assessment": (
                "单一持仓占比过高，建议分散" if risk_level == "high"
                else "集中度适中" if risk_level == "medium"
                else "集中度合理"
            ),
            "skill": "portfolio_review",
            "sub_skill": "concentration_check",
        }


# ============================================================================
# 3. NewsPulseSkill - 新闻舆情与价格归因
# ============================================================================

class NewsPulseSkill(BaseSkill):
    """
    新闻脉搏分析
    - 新闻情绪分析
    - 价格异动归因
    - 舆情热度追踪
    - 关联性分析
    """

    async def analyze(
        self,
        ticker: str,
        news_items: List[Dict[str, Any]],
        price_change_pct: Optional[float] = None,
        volume_ratio: Optional[float] = None,
        market_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行新闻舆情与价格归因分析

        news_items: [{"title": "", "source": "", "publish_time": "", "content": "", "sentiment": "positive/negative/neutral"}]
        """
        # 预处理：按时间排序、去重
        sorted_news = sorted(news_items, key=lambda x: x.get("publish_time", ""), reverse=True)

        system_prompt = """你是AI新闻舆情分析师。请根据新闻和股价数据，分析舆情对价格的影响。

输出严格JSON格式：
{
  "ticker": "",
  "news_sentiment": {
    "overall": "positive/negative/neutral/mixed",
    "score": 0,
    "positive_count": 0,
    "negative_count": 0,
    "neutral_count": 0
  },
  "price_attribution": {
    "primary_driver": "主要驱动因素",
    "news_contribution": "新闻贡献度(高/中/低)",
    "market_beta": "市场整体影响",
    "sector_effect": "板块效应",
    "idiosyncratic": "个股特有因素"
  },
  "key_narratives": [
    {"theme": "主题", "strength": "strong/moderate/weak", "direction": "positive/negative"}
  ],
  "risk_signals": [
    {"signal": "风险信号", "severity": "high/medium/low", "source": "来源"}
  ],
  "opportunity_signals": [
    {"signal": "机会信号", "strength": "high/medium/low", "source": "来源"}
  ],
  "information_asymmetry": "信息不对称评估",
  "recommendation": "舆情观察建议",
  "summary": "一句话总结"
}

注意：
- 明确区分"事实新闻"和"市场叙事"
- 不预测未来股价走势
- 指出信息来源的可信度差异"""

        news_text = json.dumps(sorted_news[:15], ensure_ascii=False, indent=2)  # 限制新闻数量
        user_prompt = f"""请分析 {ticker} 的新闻舆情与价格归因：

**价格变动**：{price_change_pct or '未知'}%
**量能比**：{volume_ratio or '未知'}（成交量/20日均量）
**市场环境**：{market_context or '未提供'}

**近期新闻**（按时间倒序）：
{news_text}

请输出舆情分析报告。"""

        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.3)
        parsed = self._safe_json_parse(response)

        if isinstance(parsed, dict) and not parsed.get("parse_error"):
            parsed["ticker"] = ticker
            parsed["news_count"] = len(sorted_news)
            parsed["analysis_date"] = date.today().isoformat()
            parsed["skill"] = "news_pulse"

        return parsed

    async def sentiment_batch(
        self, news_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量情感分析"""
        if not news_items:
            return []

        system_prompt = """你是新闻情感分析助手。对每条新闻给出情感标签和置信度。

情感标签：positive / negative / neutral / mixed
输出JSON数组格式：
[{"title": "标题", "sentiment": "positive", "confidence": 0.85, "key_phrase": "关键短语"}]"""

        news_text = json.dumps(news_items, ensure_ascii=False, indent=2)
        user_prompt = f"请对以下新闻进行情感分析：\n\n{news_text}"

        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.2)
        parsed = self._safe_json_parse(response)

        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict) and "raw_text" in parsed:
            # 尝试逐行解析
            return [{"title": n.get("title"), "sentiment": "unknown", "note": "batch_parse_failed"} for n in news_items]
        return []


# ============================================================================
# 4. InvestmentChecklistSkill - 巴菲特六关Checklist
# ============================================================================

class InvestmentChecklistSkill(BaseSkill):
    """
    巴菲特六关投资Checklist
    1. 我能理解这门生意吗（能力圈）
    2. 这是一门好生意吗（经济特征）
    3. 护城河够不够深（竞争优势）
    4. 管理层是否值得信任（人的因素）
    5. 价格是否足够便宜（安全边际）
    6. 仓位与决策纪律（防止情绪失控）
    """

    async def analyze(
        self,
        ticker: str,
        name: str = "",
        financial_data: Optional[Dict[str, Any]] = None,
        business_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行六关Checklist分析
        """
        system_prompt = """你是巴菲特价值投资Checklist分析师。请对标的严格执行六关检查。

六关：
1. **能力圈** - 我能否在5分钟内向一个12岁孩子解释清楚这门生意？
2. **生意质量** - 这门生意的经济特征是否优秀（高ROE、稳定现金流、低资本需求）？
3. **护城河** - 竞争优势是否清晰、可持续？
4. **管理层** - 管理层是否诚实、能干、为股东着想？
5. **安全边际** - 当前价格是否提供了足够的安全边际？
6. **决策纪律** - 我是否有足够的信息做出决定？情绪是否影响了判断？

输出严格JSON格式：
{
  "ticker": "",
  "name": "",
  "overall_passed": false,
  "overall_score": 0,
  "gate_results": {
    "capability": {
      "passed": false,
      "score": 0,
      "reasoning": "详细理由",
      "confidence": "high/medium/low",
      "notes": "备注"
    },
    "business_quality": { "passed": false, "score": 0, "reasoning": "", "confidence": "", "notes": "" },
    "moat": { "passed": false, "score": 0, "reasoning": "", "confidence": "", "notes": "" },
    "management": { "passed": false, "score": 0, "reasoning": "", "confidence": "", "notes": "" },
    "valuation": { "passed": false, "score": 0, "reasoning": "", "confidence": "", "notes": "" },
    "discipline": { "passed": false, "score": 0, "reasoning": "", "confidence": "", "notes": "" }
  },
  "bottleneck_gate": "最弱环节",
  "kill_factors": ["一票否决因素1"],
  "yellow_flags": ["黄色警告1"],
  "green_flags": ["绿色信号1"],
  "verdict": "综合结论",
  "next_steps": ["下一步行动1"],
  "risk_warning": "风险提示"
}

评分：每关1-5分，>=3分算通过。总体>=4分且没有kill factor才算"通过"。

原则：
- 宁可错过，不可做错
- 不懂的不碰
- 安全边际是生命线
- 诚实面对自己的能力圈"""

        fin_text = json.dumps(financial_data, ensure_ascii=False, indent=2) if financial_data else "未提供"
        user_prompt = f"""请对 {ticker} {name} 执行巴菲特六关Checklist：

**财务数据**：
{fin_text}

**业务描述**：
{business_description or '请基于公开信息分析'}

要求：
- 诚实面对能力圈边界，不懂就说不通过
- 每个关卡必须给出明确通过/不通过判断
- 识别任何一票否决的因素
- 不因为FOMO而放松标准"""

        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.2)
        parsed = self._safe_json_parse(response)

        if isinstance(parsed, dict) and not parsed.get("parse_error"):
            parsed["ticker"] = ticker
            parsed["name"] = name
            parsed["checklist_date"] = date.today().isoformat()
            parsed["skill"] = "investment_checklist"

        return parsed

    async def quick_check(self, ticker: str) -> Dict[str, Any]:
        """快速Checklist - 30秒版"""
        system_prompt = """你是快速投资筛选助手。对标的进行30秒六关快速检查。
输出JSON：
{"quick_pass": false, "red_flags": [""], "yellow_flags": [""], "verdict": ""}"""

        user_prompt = f"请对 {ticker} 进行30秒快速Checklist筛选。"
        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.2)
        return self._safe_json_parse(response)


# ============================================================================
# 5. EarningsReviewSkill - 财报深度解读
# ============================================================================

class EarningsReviewSkill(BaseSkill):
    """
    财报深度解读
    - 核心指标拆解
    - 同比环比分析
    - 业务分部分析
    - 前瞻指引解读
    - 会计质量检查
    """

    async def analyze(
        self,
        ticker: str,
        report_text: Optional[str] = None,
        report_type: str = "quarterly",  # quarterly / annual / interim
        period: Optional[str] = None,
        key_metrics: Optional[Dict[str, Any]] = None,
        previous_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行财报深度解读
        """
        system_prompt = """你是AI财报分析师。请深度解读上市公司财报，输出结构化分析。

输出严格JSON格式：
{
  "ticker": "",
  "period": "报告期",
  "report_type": "quarterly/annual",
  "executive_summary": {
    "one_sentence": "一句话总结",
    "beat_miss": "beat/miss/in-line",
    "key_highlight": "最亮点",
    "key_concern": "最大担忧"
  },
  "revenue_analysis": {
    "total_revenue_growth": "总收入增长分析",
    "segment_breakdown": {"分部名": "表现"},
    "quality_assessment": "收入质量评估"
  },
  "profitability": {
    "gross_margin_trend": "毛利率趋势",
    "operating_margin_trend": "营业利润率趋势",
    "net_margin_trend": "净利率趋势",
    "profit_quality": "利润质量"
  },
  "cash_flow": {
    "operating_cash_flow": "经营现金流",
    "free_cash_flow": "自由现金流",
    "capex_trend": "资本开支趋势",
    "cash_conversion": "现金转化能力"
  },
  "balance_sheet": {
    "debt_level": "债务水平",
    "cash_position": "现金状况",
    "working_capital": "营运资本",
    "asset_quality": "资产质量"
  },
  "accounting_quality": {
    "red_flags": ["会计红旗1"],
    "yellow_flags": ["会计黄旗1"],
    "notes": "会计质量备注"
  },
  "guidance_outlook": {
    "management_guidance": "管理层指引",
    "analyst_expectations": "分析师预期对比",
    "outlook_assessment": "前景评估"
  },
  "valuation_implication": {
    "pe_implication": "PE影响",
    "earnings_revision": "盈利修正方向",
    "fair_value_range": "合理估值区间"
  },
  "risks": ["风险1", "风险2"],
  "watchpoints": ["观察点1", "观察点2"],
  "conclusion": "总体结论"
}

原则：
- 关注收入确认政策变化
- 警惕应收账款、存货异常增长
- 区分经营现金流和净利润的差异
- 不给出确定性估值目标
- 明确区分事实和管理层预期
"""

        # 构建用户提示
        metrics_text = json.dumps(key_metrics, ensure_ascii=False, indent=2) if key_metrics else "未提供"
        prev_text = json.dumps(previous_metrics, ensure_ascii=False, indent=2) if previous_metrics else "未提供"
        report_excerpt = (report_text or "")[:6000]  # 限制长度

        user_prompt = f"""请深度解读 {ticker} 的{report_type}财报：

**报告期**：{period or '最新一期'}
**报告类型**：{"年报" if report_type == "annual" else "季报"}

**本期核心指标**：
{metrics_text}

**上期核心指标**：
{prev_text}

**财报原文摘要**：
{report_excerpt}

请输出深度财报分析报告。"""

        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.3)
        parsed = self._safe_json_parse(response)

        if isinstance(parsed, dict) and not parsed.get("parse_error"):
            parsed["ticker"] = ticker
            parsed["period"] = period
            parsed["report_type"] = report_type
            parsed["analysis_date"] = date.today().isoformat()
            parsed["skill"] = "earnings_review"

        return parsed

    async def compare_quarters(
        self,
        ticker: str,
        current: Dict[str, Any],
        previous: Dict[str, Any],
        year_ago: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """多季度对比分析"""
        system_prompt = """你是财报对比分析师。请对比多期财报数据，识别趋势和异常。
输出JSON：
{"trend_summary": "", "accelerating_metrics": [""], "decelerating_metrics": [""], 
 "red_flags": [""], "inflection_points": [""]}"""

        data = {"current": current, "previous": previous, "year_ago": year_ago}
        user_prompt = f"请对比 {ticker} 的多期财报：\n{json.dumps(data, ensure_ascii=False, indent=2)}"
        response = await self.ai._call_llm(system_prompt, user_prompt, temperature=0.3)
        return self._safe_json_parse(response)


# ============================================================================
# Convenience function for running all skills
# ============================================================================

async def run_full_research(
    ticker: str,
    ai_service: Optional[AIService] = None,
    financial_data: Optional[Dict] = None,
    news_items: Optional[List[Dict]] = None,
    holdings: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    对标的运行完整的AI Berkshire研究流程
    """
    team = InvestmentTeamSkill(ai_service)
    checklist = InvestmentChecklistSkill(ai_service)

    results = {
        "ticker": ticker,
        "research_date": date.today().isoformat(),
        "investment_team": None,
        "checklist": None,
        "news_pulse": None,
        "portfolio_review": None,
    }

    # 核心分析
    results["investment_team"] = await team.analyze(
        ticker=ticker,
        financial_data=financial_data,
        business_summary=financial_data.get("business_summary") if financial_data else None,
    )

    results["checklist"] = await checklist.analyze(
        ticker=ticker,
        financial_data=financial_data,
    )

    # 可选分析
    if news_items:
        news = NewsPulseSkill(ai_service)
        results["news_pulse"] = await news.analyze(ticker=ticker, news_items=news_items)

    if holdings:
        portfolio = PortfolioReviewSkill(ai_service)
        results["portfolio_review"] = await portfolio.analyze(holdings=holdings)

    # 综合结论
    overall_passed = False
    if (
        isinstance(results.get("checklist"), dict)
        and results["checklist"].get("overall_passed")
    ):
        overall_passed = True

    team_score = 0
    if (
        isinstance(results.get("investment_team"), dict)
        and "overall_score" in results["investment_team"]
    ):
        try:
            team_score = float(results["investment_team"]["overall_score"])
        except (ValueError, TypeError):
            team_score = 0

    results["synthesis"] = {
        "overall_passed": overall_passed,
        "investment_team_score": team_score,
        "recommendation": (
            "深入研究" if overall_passed and team_score >= 4.0
            else "灰色地带，继续观察" if team_score >= 3.0
            else "暂不考虑"
        ),
        "next_steps": [
            "阅读近3年年报和季报",
            "分析竞争对手情况",
            "跟踪管理层公开讲话",
            "等待更好的买入价格" if not overall_passed else "建立观察仓位",
        ],
    }

    return results
