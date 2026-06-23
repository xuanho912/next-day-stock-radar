# 数据质量报告

- score: `66`
- latest_data_date: `2026-06-23`
- expected_latest_trading_date: `2026-06-23`
- data_freshness_status: `partial_fallback`
- stale_warning: `True`
- candidate_count: `39`

## 数据源状态

- yahoo: `{'available': True, 'total_symbols': 61, 'fallback_count': 1, 'fallback_symbols': ['SAVA'], 'sources': ['fallback-yahoo-error', 'yahoo-chart']}`
- finnhub: `{'configured': True, 'available': True, 'core_available': True, 'availability_status': 'partial', 'source': 'finnhub', 'optional_data_status': {'quote': 'available', 'ohlcv_candle_fallback': 'missing', 'company_news': 'available', 'market_news': 'available', 'earnings_calendar': 'available', 'economic_calendar': 'missing', 'sentiment': 'missing'}, 'error_count': 81}`
- fred: `{'configured': True, 'available': True, 'source': 'fred-api', 'error_count': 0}`
