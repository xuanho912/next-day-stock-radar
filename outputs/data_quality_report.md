# Data Quality Report

- score: `58`
- latest_data_date: `2026-06-16`
- expected_latest_trading_date: `2026-06-16`
- data_freshness_status: `partial_fallback`
- stale_warning: `True`
- candidate_count: `39`

## Provider Status

- yahoo: `{'available': True, 'total_symbols': 61, 'fallback_count': 1, 'fallback_symbols': ['SAVA'], 'sources': ['fallback-yahoo-error', 'yahoo-chart']}`
- finnhub: `{'configured': True, 'available': False, 'source': 'finnhub', 'optional_data_status': {'quote': 'available', 'ohlcv_candle_fallback': 'available', 'company_news': 'available', 'market_news': 'available', 'earnings_calendar': 'available', 'economic_calendar': 'missing', 'sentiment': 'available'}, 'error_count': 81}`
- fred: `{'configured': True, 'available': True, 'source': 'fred-api', 'error_count': 0}`
