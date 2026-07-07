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


class PremarketFakeResponse:
    status_code = 200
    encoding = "gbk"
    text = (
        'var hq_str_sh600519="贵州茅台,0.000,1206.910,0.000,'
        '0.000,0.000,0.000,0.000,0,0.000,0,0.000,0,0.000,0,'
        '0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,'
        '0,0.000,0,0.000,2026-07-07,09:03:43,00";'
    )


class IndexPremarketFakeResponse:
    status_code = 200
    encoding = "gbk"
    text = (
        'var hq_str_sh000001="上证指数,0.0000,4041.2382,4041.1241,0.0000,0.0000,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-07-07,09:15:55,00,";\n'
        'var hq_str_sz399001="深证成指,0.000,15416.804,0.000,0.000,0.000,0.000,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,2026-07-07,09:15:57,00";\n'
        'var hq_str_sz399006="创业板指,0.000,3948.860,0.000,0.000,0.000,0.000,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,0,0.000,2026-07-07,09:15:12,00";\n'
        'var hq_str_sh000688="科创50,0.0000,1996.1029,1996.1029,0.0000,0.0000,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-07-07,09:15:55,00,";\n'
        'var hq_str_sh000300="沪深300,0.0000,4841.9980,4841.9634,0.0000,0.0000,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2026-07-07,09:15:55,00,";'
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


def test_sina_stock_spot_uses_previous_close_before_open(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return PremarketFakeResponse()

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    result = MarketService()._source_sina_stock_spot("600519.SS")

    assert result["price"] == 1206.91
    assert result["change_pct"] == 0


def test_sina_indices_use_full_codes_and_previous_close_before_open(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        assert "sz399001" in url
        assert "sz399006" in url
        return IndexPremarketFakeResponse()

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    indices = MarketService()._source_sina_indices()
    by_code = {item["code"]: item for item in indices}

    assert by_code["399001"]["close"] == 15416.8
    assert by_code["399001"]["change_pct"] == 0
    assert by_code["399006"]["close"] == 3948.86
    assert by_code["399006"]["change_pct"] == 0
    assert by_code["000688"]["close"] == 1996.1


def test_stock_detail_falls_back_without_raising(monkeypatch):
    service = MarketService()

    monkeypatch.setattr(service, "USE_REAL_DATA", True)
    monkeypatch.setattr(service, "_source_sina_stock_spot", lambda ticker: None)
    monkeypatch.setattr(service, "_source_akshare_stock_spot", lambda ticker: None)
    monkeypatch.setattr(service, "_source_yahoo_chart", lambda ticker: None)

    result = service._get_stock_detail("600519.SS")

    assert result["ticker"] == "600519.SS"
    assert result["data_source"] == "mock"
