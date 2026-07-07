from app.services.market_service import MarketService


class FakeResponse:
    status_code = 200
    encoding = "gbk"
    text = (
        'var hq_str_sh600519="贵州茅台,1186.000,1194.450,1206.910,'
        '1215.000,1180.000,1206.900,1206.910,4097001,4913750668.000,'
        '1600,1206.900,3200,1206.890,1400,1206.880,200,1206.870,'
        '1100,1206.860,1734,1206.910,100,1206.920,200,1206.980,'
        '500,1206.990,2400,1207.000,2026-07-06,15:35:15,00";'
    )


def test_sina_stock_spot_parses_a_share(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        assert "sh600519" in url
        return FakeResponse()

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    result = MarketService()._source_sina_stock_spot("600519.SS")

    assert result["ticker"] == "600519.SS"
    assert result["name"] == "贵州茅台"
    assert result["price"] == 1206.91
    assert result["change_pct"] == 1.04
    assert result["data_source"] if "data_source" in result else True


def test_stock_detail_falls_back_without_raising(monkeypatch):
    service = MarketService()

    monkeypatch.setattr(service, "USE_REAL_DATA", True)
    monkeypatch.setattr(service, "_source_sina_stock_spot", lambda ticker: None)
    monkeypatch.setattr(service, "_source_akshare_stock_spot", lambda ticker: None)
    monkeypatch.setattr(service, "_source_yahoo_chart", lambda ticker: None)

    result = service._get_stock_detail("600519.SS")

    assert result["ticker"] == "600519.SS"
    assert result["data_source"] == "mock"
