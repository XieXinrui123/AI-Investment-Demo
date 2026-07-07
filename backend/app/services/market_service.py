import random
import logging
import time
import os
import re
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

logger = logging.getLogger(__name__)

# ============================================================
#  多源市场数据服务 - 免费数据源 + 超时控制 + 自动降级
# ============================================================
#  数据源优先级（A股指数）:
#  1. 新浪财经实时API - 免费，JSONP，无需key，速度快
#  2. AkShare (东方财富) - 免费，数据全但依赖较重，可选
#  3. 本地 mock 数据 - 永远可用
#
#  数据源优先级（美股/港股）:
#  1. Yahoo Finance chart API - 免费，无需key
#  2. yfinance - 免费，可选
#  2. 本地 mock 数据 - 永远可用
#
#  环境变量:
#  - USE_REAL_DATA=true/false (默认 true，网络超时时自动降级)
#  - NETWORK_TIMEOUT=3 (默认3秒，网络请求超时时间)
# ============================================================

class MarketService:
    """多源市场数据服务 - 免费数据源 + 强制超时 + 自动降级"""
    
    USE_REAL_DATA = os.getenv("USE_REAL_DATA", "true").lower() == "true"
    NETWORK_TIMEOUT = int(os.getenv("NETWORK_TIMEOUT", "3"))
    ENABLE_AKSHARE_BREADTH = os.getenv("ENABLE_AKSHARE_BREADTH", "false").lower() == "true"
    CACHE_TTL = 60
    
    _cache = {}
    _cache_time = {}
    
    A_INDEX_CODES = {
        "000001": "上证指数", "399001": "深证成指",
        "399006": "创业板指", "000688": "科创50", "000300": "沪深300",
    }
    
    SINA_CODES = {
        "000001": "sh000001", "399001": "sz399001",
        "399006": "sz399006", "000688": "sh000688", "000300": "sh000300",
    }

    REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn",
    }
    
    MOCK_INDICES = {
        "A": [
            {"code": "000001", "name": "上证指数", "close": 3385.42, "change_pct": 0.82},
            {"code": "399001", "name": "深证成指", "close": 10892.15, "change_pct": 0.35},
            {"code": "399006", "name": "创业板指", "close": 2188.63, "change_pct": -0.21},
            {"code": "000688", "name": "科创50", "close": 1025.88, "change_pct": 1.45},
            {"code": "000300", "name": "沪深300", "close": 3952.10, "change_pct": 0.56},
        ],
        "HK": [
            {"code": "HSI", "name": "恒生指数", "close": 19520.34, "change_pct": 1.12},
        ],
        "US": [
            {"code": "SPX", "name": "标普500", "close": 5825.12, "change_pct": 0.32},
            {"code": "IXIC", "name": "纳斯达克", "close": 18550.45, "change_pct": -0.36},
        ],
    }
    
    SECTORS = [
        {"name": "半导体", "change_pct": 3.20, "net_inflow": 45.2},
        {"name": "机器人", "change_pct": 2.80, "net_inflow": 32.1},
        {"name": "AI应用", "change_pct": 2.45, "net_inflow": 28.6},
        {"name": "创新药", "change_pct": 1.85, "net_inflow": 15.3},
        {"name": "低空经济", "change_pct": 1.62, "net_inflow": 12.8},
        {"name": "白酒", "change_pct": -1.70, "net_inflow": -28.5},
        {"name": "房地产", "change_pct": -1.45, "net_inflow": -22.1},
        {"name": "医药商业", "change_pct": -1.20, "net_inflow": -15.6},
        {"name": "银行", "change_pct": -0.85, "net_inflow": -10.2},
        {"name": "煤炭", "change_pct": -0.62, "net_inflow": -8.4},
    ]
    
    HOT_TOPICS = [
        {"name": "AI应用", "heat": 95, "change_pct": 3.5, "catalyst": "OpenAI新品发布", "sustainability": "中"},
        {"name": "半导体国产替代", "heat": 88, "change_pct": 4.2, "catalyst": "大基金三期落地", "sustainability": "高"},
        {"name": "低空经济", "heat": 82, "change_pct": 2.8, "catalyst": "政策试点扩容", "sustainability": "中"},
        {"name": "机器人", "heat": 78, "change_pct": 3.1, "catalyst": "特斯拉Optimus进展", "sustainability": "中"},
        {"name": "创新药", "heat": 72, "change_pct": 1.9, "catalyst": "BD出海加速", "sustainability": "高"},
    ]
    
    NEWS = [
        {"title": "央行宣布降准0.5个百分点,释放长期流动性约1万亿元", "source": "财联社", "category": "macro", "impact": "high", "sentiment": "positive"},
        {"title": "半导体设备国产化率突破40%,大基金三期重点布局", "source": "证券时报", "category": "industry", "impact": "high", "sentiment": "positive"},
        {"title": "腾讯一季度游戏收入同比增长12%,海外业务持续扩张", "source": "第一财经", "category": "company", "impact": "medium", "sentiment": "positive"},
    ]
    
    # ========== 核心: 强制超时包装器 ==========
    
    def _fetch_with_timeout(self, func, *args, timeout=None):
        """用线程池执行函数，强制超时（不等待后台线程完成）"""
        if timeout is None:
            timeout = self.NETWORK_TIMEOUT
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(func, *args)
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            logger.warning(f"请求超时 ({timeout}s): {func.__name__}")
            return None
        except Exception as e:
            logger.warning(f"请求失败: {func.__name__} - {type(e).__name__}")
            return None
        finally:
            executor.shutdown(wait=False)  # 关键: 不等待后台线程
    
    # ========== 缓存 ==========
    
    def _get_cache(self, key: str) -> Any:
        now = time.time()
        if key in self._cache and key in self._cache_time:
            if now - self._cache_time[key] < self.CACHE_TTL:
                return self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_time[key] = time.time()

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value in (None, ""):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _normalize_a_share_for_sina(self, ticker: str) -> Optional[str]:
        raw = ticker.upper().strip()
        code = raw.split(".")[0]
        if not (len(code) == 6 and code.isdigit()):
            return None

        if raw.endswith(".SS") or code.startswith(("5", "6", "9")):
            return f"sh{code}"
        return f"sz{code}"

    def _normalize_yahoo_ticker(self, ticker: str) -> str:
        raw = ticker.upper().strip()
        if raw.endswith(".HK"):
            code = raw.split(".")[0]
            if code.isdigit() and len(code) > 4:
                return f"{int(code):04d}.HK"
            return raw
        if raw.endswith(".SS") or raw.endswith(".SZ") or raw.endswith(".HK"):
            return raw

        code = raw.split(".")[0]
        if len(code) == 6 and code.isdigit():
            suffix = ".SS" if code.startswith(("5", "6", "9")) else ".SZ"
            return f"{code}{suffix}"
        return raw
    
    # ========== 数据源1: AkShare ==========
    
    def _source_akshare_indices(self) -> Optional[List[Dict]]:
        try:
            import akshare as ak
            df = ak.stock_zh_index_spot_em()
            indices = []
            for code, name in self.A_INDEX_CODES.items():
                row = df[df['代码'] == code]
                if not row.empty:
                    indices.append({
                        "code": code, "name": name,
                        "close": float(row['最新价'].values[0]),
                        "change_pct": float(row['涨跌幅'].values[0]),
                    })
                else:
                    indices.append({"code": code, "name": name, "close": 0, "change_pct": 0})
            return indices
        except Exception as e:
            logger.debug(f"AkShare 失败: {e}")
            return None
    
    def _source_akshare_movers(self, category="gainers", limit=10) -> Optional[List[Dict]]:
        try:
            import akshare as ak
            import pandas as pd
            df = ak.stock_zh_a_spot_em()
            df = df[df['名称'].notna()]
            if category == "gainers":
                df = df.nlargest(limit, '涨跌幅')
            elif category == "losers":
                df = df.nsmallest(limit, '涨跌幅')
            results = []
            for _, row in df.iterrows():
                code = str(row['代码'])
                suffix = ".SS" if code.startswith('6') else ".SZ"
                results.append({
                    "ticker": f"{code}{suffix}",
                    "name": str(row['名称']),
                    "price": float(row['最新价']) if pd.notna(row['最新价']) else 0,
                    "change_pct": float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                })
            return results
        except Exception as e:
            logger.debug(f"AkShare 排行失败: {e}")
            return None
    
    # ========== 数据源2: 新浪财经 (备用，JSONP，无需key) ==========
    
    def _source_sina_indices(self) -> Optional[List[Dict]]:
        try:
            import requests
            codes = ",".join(self.SINA_CODES.values())
            url = f"https://hq.sinajs.cn/list={codes}"
            resp = requests.get(url, headers=self.REQUEST_HEADERS, timeout=3)
            if resp.status_code != 200:
                return None
            resp.encoding = "gbk"
            
            text = resp.text
            indices = []
            # 完整指数格式: name,open,prev_close,current,high,low,...
            for code, sina_code in self.SINA_CODES.items():
                pattern = rf'var hq_str_{sina_code}="([^"]*)"'
                match = re.search(pattern, text)
                if match:
                    parts = match.group(1).split(',')
                    if len(parts) >= 4:
                        prev_close = self._safe_float(parts[2])
                        raw_price = self._safe_float(parts[3])
                        price = raw_price if raw_price > 0 else prev_close
                        change = price - prev_close if prev_close else 0
                        change_pct = (change / prev_close * 100) if prev_close else 0
                        indices.append({
                            "code": code,
                            "name": parts[0],
                            "close": round(price, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "prev_close": round(prev_close, 2),
                            "volume": int(self._safe_float(parts[8])) if len(parts) > 8 else 0,
                        })
                    else:
                        indices.append({"code": code, "name": self.A_INDEX_CODES.get(code, code), "close": 0, "change_pct": 0})
                else:
                    indices.append({"code": code, "name": self.A_INDEX_CODES.get(code, code), "close": 0, "change_pct": 0})
            return indices
        except Exception as e:
            logger.debug(f"新浪 失败: {e}")
            return None

    def _source_sina_stock_spot(self, ticker: str) -> Optional[Dict]:
        """A股实时行情（新浪免费接口，无需 key）。"""
        sina_code = self._normalize_a_share_for_sina(ticker)
        if not sina_code:
            return None

        try:
            import requests
            url = f"https://hq.sinajs.cn/list={sina_code}"
            resp = requests.get(url, headers=self.REQUEST_HEADERS, timeout=3)
            if resp.status_code != 200:
                return None
            resp.encoding = "gbk"

            match = re.search(rf'var hq_str_{sina_code}="([^"]*)"', resp.text)
            if not match:
                return None

            parts = match.group(1).split(",")
            if len(parts) < 32 or not parts[0]:
                return None

            code = ticker.upper().split(".")[0]
            suffix = ".SS" if sina_code.startswith("sh") else ".SZ"
            raw_price = self._safe_float(parts[3])
            prev_close = self._safe_float(parts[2])
            open_price = self._safe_float(parts[1])
            high = self._safe_float(parts[4])
            low = self._safe_float(parts[5])
            volume = self._safe_float(parts[8])
            amount = self._safe_float(parts[9])
            price = raw_price if raw_price > 0 else prev_close
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

            return {
                "ticker": f"{code}{suffix}",
                "name": parts[0],
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "prev_close": round(prev_close, 2),
                "volume": int(volume),
                "amount": round(amount / 1e8, 2) if amount else 0,
                "trade_time": f"{parts[30]} {parts[31]}" if parts[30] and parts[31] else None,
            }
        except Exception as e:
            logger.debug(f"新浪个股失败 {ticker}: {e}")
            return None
    
    # ========== 数据源3: Yahoo Finance (美股/港股/A股备用) ==========

    def _source_yahoo_chart(self, ticker: str) -> Optional[Dict]:
        try:
            import requests
            yahoo_ticker = self._normalize_yahoo_ticker(ticker)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}"
            params = {"range": "5d", "interval": "1d"}
            resp = requests.get(url, params=params, headers={"User-Agent": self.REQUEST_HEADERS["User-Agent"]}, timeout=5)
            if resp.status_code != 200:
                return None

            payload = resp.json()
            result = (payload.get("chart", {}).get("result") or [None])[0]
            if not result:
                return None

            meta = result.get("meta", {})
            quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
            closes = [c for c in quote.get("close", []) if c is not None]
            if not closes and not meta.get("regularMarketPrice"):
                return None

            price = self._safe_float(meta.get("regularMarketPrice"), self._safe_float(closes[-1] if closes else 0))
            prev_close = self._safe_float(meta.get("chartPreviousClose"))
            if not prev_close and len(closes) >= 2:
                prev_close = self._safe_float(closes[-2])
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            market_cap = meta.get("marketCap")

            return {
                "ticker": meta.get("symbol", yahoo_ticker),
                "name": meta.get("longName") or meta.get("shortName") or meta.get("symbol", yahoo_ticker),
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "currency": meta.get("currency"),
                "market_cap": round(market_cap / 1e8, 2) if market_cap else None,
            }
        except Exception as e:
            logger.debug(f"Yahoo Finance 失败 {ticker}: {e}")
            return None

    # ========== 数据源4: yfinance (可选备用) ==========
    
    def _source_yfinance(self, ticker: str) -> Optional[Dict]:
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1d")
            if hist.empty:
                return None
            latest = hist.iloc[-1]
            prev_close = info.get('previousClose', latest['Close'])
            change_pct = ((latest['Close'] - prev_close) / prev_close * 100) if prev_close else 0
            return {
                "ticker": ticker,
                "name": info.get('shortName', ticker),
                "price": round(latest['Close'], 2),
                "change_pct": round(change_pct, 2),
                "pe": info.get('trailingPE'),
                "market_cap": info.get('marketCap', 0) / 1e8 if info.get('marketCap') else None,
            }
        except Exception as e:
            logger.debug(f"yfinance 失败 {ticker}: {e}")
            return None
    
    # ========== 多源获取: A股指数 (AkShare -> 新浪 -> mock) ==========
    
    def _get_a_indices(self) -> List[Dict]:
        """获取A股指数，多源冗余，自动降级"""
        cache_key = "a_indices"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        if not self.USE_REAL_DATA:
            return self.MOCK_INDICES["A"].copy()
        
        # 源1: 新浪财经 (带超时)
        result = self._fetch_with_timeout(self._source_sina_indices)
        if result:
            self._set_cache(cache_key, result)
            return result
        
        # 源2: AkShare (带超时)
        result = self._fetch_with_timeout(self._source_akshare_indices)
        if result:
            self._set_cache(cache_key, result)
            return result
        
        # 兜底: mock
        logger.info("所有网络源失败，使用 mock 数据")
        return self.MOCK_INDICES["A"].copy()
    
    # ========== 多源获取: A股涨跌排行 ==========
    
    def _get_a_movers(self, category="gainers", limit=10) -> List[Dict]:
        cache_key = f"a_movers_{category}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        if not self.USE_REAL_DATA:
            return self._get_mock_movers(category)
        
        result = self._fetch_with_timeout(self._source_akshare_movers, category, limit)
        if result:
            self._set_cache(cache_key, result)
            return result
        
        return self._get_mock_movers(category)
    
    # ========== 多源获取: 个股详情 ==========
    
    def _get_stock_detail(self, ticker: str) -> Dict:
        cache_key = f"stock_{ticker}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        if not self.USE_REAL_DATA:
            return self._get_mock_stock(ticker)
        
        result = None
        data_source = "mock"
        
        # A股: 新浪免费接口 -> AkShare可选备用 -> Yahoo备用
        if ticker.endswith('.SS') or ticker.endswith('.SZ') or (len(ticker.split('.')[0]) == 6 and ticker.split('.')[0].isdigit()):
            result = self._fetch_with_timeout(self._source_sina_stock_spot, ticker)
            if result:
                data_source = "sina"
            if not result:
                result = self._fetch_with_timeout(self._source_akshare_stock_spot, ticker)
                if result:
                    data_source = "akshare"
            if not result:
                result = self._fetch_with_timeout(self._source_yahoo_chart, ticker)
                if result:
                    data_source = "yahoo"
        
        # 美股/港股: Yahoo直连 -> yfinance可选备用
        if not result and ('.' not in ticker or ticker.endswith('.HK')):
            result = self._fetch_with_timeout(self._source_yahoo_chart, ticker)
            if result:
                data_source = "yahoo"
        
        if not result and ('.' not in ticker or ticker.endswith('.HK')):
            result = self._fetch_with_timeout(self._source_yfinance, ticker)
            if result:
                data_source = "yfinance"
        
        if result:
            result["news_count"] = random.randint(0, 8)
            result["announcement_count"] = random.randint(0, 3)
            result["data_source"] = data_source
            self._set_cache(cache_key, result)
            return result
        
        return self._get_mock_stock(ticker)

    def _source_akshare_stock_spot(self, ticker: str) -> Optional[Dict]:
        """AkShare 可选备用源；未安装 akshare 时返回 None。"""
        try:
            import akshare as ak
            import pandas as pd

            code = ticker.upper().split(".")[0]
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"].astype(str) == code]
            if row.empty:
                return None
            item = row.iloc[0]
            suffix = ".SS" if code.startswith(("5", "6", "9")) else ".SZ"
            return {
                "ticker": f"{code}{suffix}",
                "name": str(item["名称"]),
                "price": float(item["最新价"]) if pd.notna(item["最新价"]) else 0,
                "change_pct": float(item["涨跌幅"]) if pd.notna(item["涨跌幅"]) else 0,
                "pe": float(item["市盈率-动态"]) if "市盈率-动态" in item and pd.notna(item["市盈率-动态"]) else None,
                "market_cap": float(item["总市值"]) / 1e8 if "总市值" in item and pd.notna(item["总市值"]) else None,
            }
        except Exception as e:
            logger.debug(f"AkShare 个股失败 {ticker}: {e}")
            return None
    
    # ========== mock 辅助方法 ==========
    
    def _get_mock_movers(self, category="gainers") -> List[Dict]:
        stocks = [
            {"ticker": "00700.HK", "name": "腾讯控股", "price": 485.20, "change_pct": 1.21},
            {"ticker": "600519.SS", "name": "贵州茅台", "price": 1528.50, "change_pct": -1.05},
            {"ticker": "NVDA", "name": "英伟达", "price": 138.25, "change_pct": 2.40},
            {"ticker": "002475.SZ", "name": "立讯精密", "price": 42.85, "change_pct": 3.15},
            {"ticker": "300750.SZ", "name": "宁德时代", "price": 228.60, "change_pct": -0.85},
        ]
        if category == "gainers":
            stocks.sort(key=lambda x: x["change_pct"], reverse=True)
        elif category == "losers":
            stocks.sort(key=lambda x: x["change_pct"])
        return stocks[:10]
    
    def _get_mock_stock(self, ticker: str) -> Dict:
        return {
            "ticker": ticker, "name": ticker,
            "price": round(random.uniform(10, 500), 2),
            "change_pct": round(random.uniform(-5, 5), 2),
            "pe": round(random.uniform(10, 60), 1),
            "market_cap": random.randint(500, 50000),
            "news_count": random.randint(0, 5),
            "announcement_count": random.randint(0, 2),
            "data_source": "mock",
        }
    
    # ========== 公开接口 ==========
    
    async def get_market_overview(self, market: str = "A") -> Dict[str, Any]:
        """获取市场概览 - 多源冗余，超时自动降级"""
        data_source = "mock"
        indices = self.MOCK_INDICES.get(market, self.MOCK_INDICES["A"]).copy()
        up_count, down_count = 0, 0
        
        if market == "A":
            real_indices = self._get_a_indices()
            has_real_data = real_indices != self.MOCK_INDICES["A"]
            if has_real_data:
                indices = real_indices
                data_source = "sina_or_akshare"
            
            if self.USE_REAL_DATA and self.ENABLE_AKSHARE_BREADTH:
                # 尝试获取涨跌家数 (AkShare)
                count_result = self._fetch_with_timeout(self._source_akshare_movers, "gainers", 5000)
                if count_result:
                    up_count = len([s for s in count_result if s.get("change_pct", 0) > 0])
                    down_count = len([s for s in count_result if s.get("change_pct", 0) < 0])
                    data_source = "akshare"  # 只有count_result成功才是真正的akshare
                else:
                    up_count = random.randint(2800, 4200)
                    down_count = random.randint(800, 2200)
                    # data_source 保持 mock（如果indices已经是mock的话）
            else:
                up_count = random.randint(2800, 4200)
                down_count = random.randint(800, 2200)
        else:
            up_count = random.randint(1000, 3000)
            down_count = random.randint(500, 1500)
        
        sectors = sorted(self.SECTORS, key=lambda x: x["change_pct"], reverse=True)
        sentiment = 50 + (up_count - down_count) / 100
        sentiment = max(0, min(100, sentiment))
        
        return {
            "date": date.today().isoformat(),
            "market": market,
            "indices": indices,
            "sectors_up": sectors[:5],
            "sectors_down": sectors[-5:],
            "sentiment_score": round(sentiment, 1),
            "up_count": up_count,
            "down_count": down_count,
            "limit_up_count": random.randint(40, 120),
            "limit_down_count": random.randint(2, 15),
            "total_amount": round(random.uniform(8500, 13500), 2),
            "hot_topics": self.HOT_TOPICS[:4],
            "data_source": data_source,
        }
    
    async def get_indices(self, market: str = "A") -> List[Dict]:
        if market == "A":
            return self._get_a_indices()
        return self.MOCK_INDICES.get(market, self.MOCK_INDICES["A"]).copy()
    
    async def get_sectors(self, market: str = "A", sort_by: str = "change_pct") -> List[Dict]:
        sectors = self.SECTORS.copy()
        if sort_by == "change_pct":
            sectors.sort(key=lambda x: x["change_pct"], reverse=True)
        return sectors
    
    async def get_hot_topics(self, market: str = "A") -> List[Dict]:
        return self.HOT_TOPICS
    
    async def get_stock_movers(self, market: str = "A", category: str = "gainers") -> List[Dict]:
        if market == "A":
            return self._get_a_movers(category)
        return self._get_mock_movers(category)
    
    async def get_fund_flow(self, market: str = "A") -> Dict:
        return {
            "main_inflow": round(random.uniform(-150, 200), 2),
            "northbound_inflow": round(random.uniform(-80, 60), 2),
            "southbound_inflow": round(random.uniform(10, 80), 2),
            "margin_balance": round(random.uniform(15000, 18500), 2),
            "top_sectors_inflow": self.SECTORS[:3],
            "top_sectors_outflow": self.SECTORS[-3:],
        }
    
    async def get_news(self, category: Optional[str] = None, impact: Optional[str] = None, limit: int = 20) -> List[Dict]:
        news = self.NEWS.copy()
        if category:
            news = [n for n in news if n["category"] == category]
        if impact:
            news = [n for n in news if n["impact"] == impact]
        return news[:limit]
    
    async def get_stock_detail(self, ticker: str) -> Dict:
        return self._get_stock_detail(ticker)
    
    async def get_daily_review(self, review_date: date) -> Optional[Dict]:
        return {
            "date": review_date.isoformat(),
            "one_sentence_summary": "今日A股市场呈现震荡格局，科技成长板块活跃，短期关注成交量变化。",
            "market_summary": "市场整体分化，科技方向较强。",
            "sector_summary": "领涨:半导体、机器人；领跌:白酒、房地产。",
            "fund_flow_summary": "主力资金净流入科技方向。",
            "risk_summary": "成交量未放大，需警惕回调风险。",
            "tomorrow_watchlist": ["关注成交额变化", "北向资金方向", "科技板块持续性"],
        }
