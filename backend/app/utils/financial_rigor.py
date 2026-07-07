"""
Financial Rigor - 财务数据验证与计算工具

提供精确的财务计算功能，使用 Decimal 确保精度。
对应 ai-berkshire 框架中的 financial_rigor.py 工具。
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
import statistics


# ============================================================================
# 1. Market Cap Verification
# ============================================================================

def verify_market_cap(
    price: Any,
    shares: Any,
    reported: Any,
    currency: str = "CNY",
    tolerance_pct: float = 5.0,
) -> Dict[str, Any]:
    """
    验证市值计算是否一致

    Args:
        price: 股价（元/股）
        shares: 总股本（亿股或股，需与reported单位一致）
        reported: 报告市值（亿元或元）
        currency: 货币代码
        tolerance_pct: 允许误差百分比

    Returns:
        {"verified": bool, "calculated": Decimal, "reported": Decimal, "discrepancy_pct": float, "notes": str}
    """
    try:
        d_price = Decimal(str(price))
        d_shares = Decimal(str(shares))
        d_reported = Decimal(str(reported))
    except Exception as e:
        return {
            "verified": False,
            "calculated": None,
            "reported": None,
            "discrepancy_pct": None,
            "notes": f"输入转换错误: {str(e)}",
            "currency": currency,
        }

    # 计算市值
    calculated = d_price * d_shares

    # 计算差异百分比
    if d_reported == 0:
        discrepancy_pct = Decimal("100") if calculated != 0 else Decimal("0")
    else:
        discrepancy_pct = abs((calculated - d_reported) / d_reported) * Decimal("100")

    verified = discrepancy_pct <= Decimal(str(tolerance_pct))

    return {
        "verified": bool(verified),
        "calculated": calculated.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        "reported": d_reported.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        "discrepancy_pct": float(discrepancy_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "tolerance_pct": tolerance_pct,
        "notes": (
            "市值计算一致" if verified
            else f"市值差异 {float(discrepancy_pct):.2f}%，请核查股本或股价单位"
        ),
        "currency": currency,
    }


# ============================================================================
# 2. Valuation Metrics Verification
# ============================================================================

def verify_valuation(
    price: Any,
    eps: Optional[Any] = None,
    bvps: Optional[Any] = None,
    fcf_per_share: Optional[Any] = None,
    dividend: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    验证估值指标计算

    Args:
        price: 股价
        eps: 每股收益（TTM）
        bvps: 每股净资产
        fcf_per_share: 每股自由现金流
        dividend: 每股股息

    Returns:
        {"pe": float|None, "pb": float|None, "p_fcf": float|None, "dividend_yield": float|None, "notes": str}
    """
    d_price = Decimal(str(price))
    result = {
        "price": float(d_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "pe": None,
        "pb": None,
        "p_fcf": None,
        "dividend_yield": None,
        "notes": [],
    }

    # PE
    if eps is not None:
        try:
            d_eps = Decimal(str(eps))
            if d_eps > 0:
                pe = d_price / d_eps
                result["pe"] = float(pe.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            elif d_eps < 0:
                result["notes"].append("EPS为负，PE无意义（亏损）")
            else:
                result["notes"].append("EPS为0，无法计算PE")
        except Exception as e:
            result["notes"].append(f"PE计算错误: {str(e)}")

    # PB
    if bvps is not None:
        try:
            d_bvps = Decimal(str(bvps))
            if d_bvps > 0:
                pb = d_price / d_bvps
                result["pb"] = float(pb.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            else:
                result["notes"].append("BVPS为0或负，PB无意义")
        except Exception as e:
            result["notes"].append(f"PB计算错误: {str(e)}")

    # P/FCF
    if fcf_per_share is not None:
        try:
            d_fcf = Decimal(str(fcf_per_share))
            if d_fcf > 0:
                p_fcf = d_price / d_fcf
                result["p_fcf"] = float(p_fcf.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            elif d_fcf < 0:
                result["notes"].append("FCF为负，P/FCF无意义")
        except Exception as e:
            result["notes"].append(f"P/FCF计算错误: {str(e)}")

    # Dividend Yield
    if dividend is not None:
        try:
            d_div = Decimal(str(dividend))
            if d_price > 0:
                div_yield = (d_div / d_price) * Decimal("100")
                result["dividend_yield"] = float(div_yield.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        except Exception as e:
            result["notes"].append(f"股息率计算错误: {str(e)}")

    result["notes"] = "; ".join(result["notes"]) if result["notes"] else "估值指标计算完成"
    return result


# ============================================================================
# 3. Cross-Validation
# ============================================================================

def cross_validate(
    field: str,
    values: List[Any],
    sources: Optional[List[str]] = None,
    tolerance_pct: float = 2.0,
) -> Dict[str, Any]:
    """
    交叉验证多个来源的数据一致性

    Args:
        field: 字段名称（如 "revenue", "eps"）
        values: 各来源的数值
        sources: 来源名称列表（可选）
        tolerance_pct: 允许差异百分比

    Returns:
        {"field": str, "consensus": Decimal|None, "range": (min, max), "cv": float, "verified": bool, "outliers": []}
    """
    if not values:
        return {
            "field": field,
            "consensus": None,
            "range": (None, None),
            "cv": None,
            "verified": False,
            "outliers": [],
            "notes": "无数据",
        }

    # 转换并过滤有效数值
    decimals = []
    valid_sources = []
    for i, v in enumerate(values):
        try:
            decimals.append(Decimal(str(v)))
            src = sources[i] if sources and i < len(sources) else f"source_{i}"
            valid_sources.append(src)
        except (ValueError, TypeError):
            continue

    if not decimals:
        return {
            "field": field,
            "consensus": None,
            "range": (None, None),
            "cv": None,
            "verified": False,
            "outliers": [],
            "notes": "无有效数值",
        }

    # 统计计算
    mean_val = sum(decimals) / len(decimals)
    min_val = min(decimals)
    max_val = max(decimals)

    # 变异系数 (CV)
    if len(decimals) > 1:
        try:
            std_val = Decimal(str(statistics.stdev([float(d) for d in decimals])))
            cv = (std_val / mean_val * Decimal("100")) if mean_val != 0 else Decimal("0")
        except statistics.StatisticsError:
            cv = Decimal("0")
    else:
        cv = Decimal("0")

    # 判断一致性
    if mean_val != 0:
        range_pct = abs((max_val - min_val) / mean_val) * Decimal("100")
    else:
        range_pct = Decimal("100") if max_val != min_val else Decimal("0")

    verified = range_pct <= Decimal(str(tolerance_pct))

    # 识别异常值（与均值差异超过容忍度的2倍）
    outliers = []
    outlier_threshold = Decimal(str(tolerance_pct * 2))
    for i, d in enumerate(decimals):
        if mean_val != 0:
            dev_pct = abs((d - mean_val) / mean_val) * Decimal("100")
        else:
            dev_pct = Decimal("100") if d != 0 else Decimal("0")

        if dev_pct > outlier_threshold:
            outliers.append({
                "source": valid_sources[i],
                "value": float(d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
                "deviation_pct": float(dev_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            })

    return {
        "field": field,
        "consensus": float(mean_val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        "range": (
            float(min_val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            float(max_val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        ),
        "cv": float(cv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "range_pct": float(range_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "tolerance_pct": tolerance_pct,
        "verified": bool(verified),
        "outliers": outliers,
        "source_count": len(decimals),
        "notes": (
            "数据一致" if verified and not outliers
            else f"数据存在差异，范围 {float(range_pct):.2f}%"
        ),
    }


# ============================================================================
# 4. Three-Scenario Valuation
# ============================================================================

def three_scenario_valuation(
    price: Any,
    eps: Any,
    shares: Any,
    growth_scenarios: Optional[Dict[str, Any]] = None,
    pe_scenarios: Optional[Dict[str, Any]] = None,
    years: int = 3,
    discount_rate: float = 0.10,
) -> Dict[str, Any]:
    """
    三情景估值模型

    基于未来盈利增长和PE假设，计算乐观/中性/悲观三种情景下的估值。

    Args:
        price: 当前股价
        eps: 当前每股收益
        shares: 总股本（亿股）
        growth_scenarios: {"bull": 0.20, "base": 0.10, "bear": 0.03} 年化增长率
        pe_scenarios: {"bull": 25, "base": 18, "bear": 12} 目标PE
        years: 预测年限
        discount_rate: 折现率

    Returns:
        三情景估值结果
    """
    # 默认值
    if growth_scenarios is None:
        growth_scenarios = {"bull": Decimal("0.20"), "base": Decimal("0.10"), "bear": Decimal("0.03")}
    if pe_scenarios is None:
        pe_scenarios = {"bull": Decimal("25"), "base": Decimal("18"), "bear": Decimal("12")}

    try:
        d_price = Decimal(str(price))
        d_eps = Decimal(str(eps))
        d_shares = Decimal(str(shares))
        d_years = Decimal(str(years))
        d_discount = Decimal(str(discount_rate))
    except Exception as e:
        return {
            "error": True,
            "message": f"参数转换错误: {str(e)}",
        }

    def calc_scenario(growth: Decimal, target_pe: Decimal) -> Dict[str, Any]:
        """计算单一情景"""
        # 未来EPS = 当前EPS * (1 + g)^n
        future_eps = d_eps * ((Decimal("1") + growth) ** int(years))

        # 目标价格 = 未来EPS * 目标PE
        target_price = future_eps * target_pe

        # 折现到当前 = 目标价格 / (1 + r)^n
        discount_factor = (Decimal("1") + d_discount) ** int(years)
        intrinsic_value = target_price / discount_factor

        # 上涨空间
        upside = ((intrinsic_value - d_price) / d_price * Decimal("100")) if d_price > 0 else Decimal("0")

        # 隐含市值
        implied_market_cap = intrinsic_value * d_shares

        return {
            "future_eps": float(future_eps.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            "target_price": float(target_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "intrinsic_value": float(intrinsic_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "upside_pct": float(upside.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "implied_market_cap": float(implied_market_cap.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        }

    # 转换场景参数
    g_bull = Decimal(str(growth_scenarios.get("bull", "0.20")))
    g_base = Decimal(str(growth_scenarios.get("base", "0.10")))
    g_bear = Decimal(str(growth_scenarios.get("bear", "0.03")))

    pe_bull = Decimal(str(pe_scenarios.get("bull", "25")))
    pe_base = Decimal(str(pe_scenarios.get("base", "18")))
    pe_bear = Decimal(str(pe_scenarios.get("bear", "12")))

    # 计算三情景
    bull = calc_scenario(g_bull, pe_bull)
    base = calc_scenario(g_base, pe_base)
    bear = calc_scenario(g_bear, pe_bear)

    # 综合判断
    current_price = float(d_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    avg_value = (bull["intrinsic_value"] + base["intrinsic_value"] + bear["intrinsic_value"]) / 3

    # 安全边际判断
    margin_of_safety = ((avg_value - current_price) / current_price * 100) if current_price > 0 else 0

    verdict = "expensive"
    if current_price <= bear["intrinsic_value"]:
        verdict = "deep_value"
    elif current_price <= base["intrinsic_value"]:
        verdict = "fair_to_cheap"
    elif current_price <= bull["intrinsic_value"]:
        verdict = "fair"

    return {
        "current_price": current_price,
        "current_eps": float(d_eps.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        "shares": float(d_shares.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        "forecast_years": years,
        "discount_rate": discount_rate,
        "bull": {
            "growth_rate": float(g_bull.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            "target_pe": float(pe_bull.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            **bull,
        },
        "base": {
            "growth_rate": float(g_base.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            "target_pe": float(pe_base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            **base,
        },
        "bear": {
            "growth_rate": float(g_bear.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            "target_pe": float(pe_bear.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            **bear,
        },
        "average_intrinsic_value": round(avg_value, 2),
        "margin_of_safety_pct": round(margin_of_safety, 2),
        "verdict": verdict,
        "notes": {
            "deep_value": "股价低于悲观情景估值，具备较深安全边际",
            "fair_to_cheap": "股价介于悲观和中性情景之间，具备一定安全边际",
            "fair": "股价介于中性和乐观情景之间，估值合理",
            "expensive": "股价高于乐观情景估值，可能偏贵",
        }.get(verdict, ""),
    }


# ============================================================================
# 5. Helper Functions
# ============================================================================

def normalize_unit(value: Any, unit: str = "yuan") -> Decimal:
    """
    统一单位到元

    Args:
        value: 原始数值
        unit: yuan / wan / yi / billion / million
    """
    d = Decimal(str(value))
    multipliers = {
        "yuan": Decimal("1"),
        "wan": Decimal("10000"),
        "yi": Decimal("100000000"),
        "million": Decimal("1000000"),
        "billion": Decimal("1000000000"),
    }
    return d * multipliers.get(unit, Decimal("1"))


def calculate_weighted_average(values: List[Any], weights: List[Any]) -> Decimal:
    """计算加权平均"""
    if not values or not weights or len(values) != len(weights):
        return Decimal("0")

    total_weight = sum(Decimal(str(w)) for w in weights)
    if total_weight == 0:
        return Decimal("0")

    weighted_sum = sum(Decimal(str(v)) * Decimal(str(w)) for v, w in zip(values, weights))
    return (weighted_sum / total_weight).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
