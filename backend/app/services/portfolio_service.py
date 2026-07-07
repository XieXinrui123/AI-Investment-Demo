from typing import List, Dict, Any
from app.models.models import Portfolio

class PortfolioService:
    """持仓组合服务"""
    
    async def enrich_portfolio(self, items: List[Portfolio]) -> List[Dict]:
        """丰富持仓数据（加入实时价格和盈亏计算）"""
        from app.services.market_service import MarketService
        market_service = MarketService()
        
        result = []
        total_value = 0
        
        for item in items:
            stock_data = await market_service.get_stock_detail(item.ticker)
            current_price = stock_data.get("price", 0)
            quantity = float(item.quantity) if item.quantity else 0
            avg_cost = float(item.avg_cost) if item.avg_cost else 0
            
            market_value = current_price * quantity
            total_value += market_value
            
            pnl = (current_price - avg_cost) * quantity
            pnl_pct = ((current_price / avg_cost) - 1) * 100 if avg_cost > 0 else 0
            
            result.append({
                "id": item.id,
                "ticker": item.ticker,
                "name": stock_data.get("name", item.name or item.ticker),
                "quantity": quantity,
                "avg_cost": avg_cost,
                "buy_date": item.buy_date,
                "thesis": item.thesis,
                "target_weight": float(item.target_weight) if item.target_weight else None,
                "stop_condition": item.stop_condition,
                "current_price": current_price,
                "market_value": round(market_value, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "created_at": item.created_at,
            })
        
        # 计算权重
        for item in result:
            item["weight"] = round(item["market_value"] / total_value, 4) if total_value > 0 else 0
        
        return result
    
    async def get_summary(self, items: List[Portfolio]) -> Dict:
        """获取持仓汇总"""
        enriched = await self.enrich_portfolio(items)
        
        total_value = sum(item["market_value"] for item in enriched)
        total_cost = sum(item["avg_cost"] * item["quantity"] for item in enriched)
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        winning = [item for item in enriched if item["pnl"] > 0]
        losing = [item for item in enriched if item["pnl"] < 0]
        
        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "stock_count": len(enriched),
            "winning_count": len(winning),
            "losing_count": len(losing),
            "winning_value": round(sum(w["market_value"] for w in winning), 2),
            "losing_value": round(sum(l["market_value"] for l in losing), 2),
        }
    
    async def get_risk_analysis(self, items: List[Portfolio]) -> Dict:
        """持仓风险分析"""
        enriched = await self.enrich_portfolio(items)
        
        if not enriched:
            return {"message": "无持仓数据", "risk_level": "low"}
        
        # 集中度分析
        max_weight = max(item["weight"] for item in enriched) if enriched else 0
        top3_weight = sum(sorted([item["weight"] for item in enriched], reverse=True)[:3])
        
        # 简单风险判断
        risk_factors = []
        if max_weight > 0.30:
            risk_factors.append(f"单一持仓占比{max_weight*100:.1f}%，集中度偏高")
        if top3_weight > 0.70:
            risk_factors.append(f"前三大持仓占比{top3_weight*100:.1f}%，组合不够分散")
        
        risk_level = "high" if len(risk_factors) >= 2 else ("medium" if risk_factors else "low")
        
        return {
            "max_concentration": round(max_weight, 4),
            "top3_concentration": round(top3_weight, 4),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "suggestion": "建议关注仓位分散和行业平衡" if risk_factors else "组合风险处于合理水平",
        }
    
    async def get_rebalance_suggestions(self, items: List[Portfolio]) -> List[Dict]:
        """再平衡建议"""
        enriched = await self.enrich_portfolio(items)
        suggestions = []
        
        for item in enriched:
            if item.get("target_weight") and item["weight"]:
                deviation = item["weight"] - item["target_weight"]
                if abs(deviation) > 0.05:  # 偏离超过5%
                    action = "减仓" if deviation > 0 else "加仓"
                    suggestions.append({
                        "ticker": item["ticker"],
                        "name": item["name"],
                        "current_weight": item["weight"],
                        "target_weight": item["target_weight"],
                        "deviation": round(deviation, 4),
                        "suggested_action": action,
                    })
        
        return suggestions
