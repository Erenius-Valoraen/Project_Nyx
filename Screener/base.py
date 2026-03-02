from tradingview_screener import Query, col

screen = (Query()
 .select(
     'name',
     'description',
     'logoid',
     'update_mode',
     'type',
     'typespecs',
     'market_cap_basic',
     'fundamental_currency_code',
     'close',
     'pricescale',
     'minmov',
     'fractional',
     'minmove2',
     'currency',
     'change',
     'volume',
     'price_earnings_ttm',
     'earnings_per_share_diluted_ttm',
     'earnings_per_share_diluted_yoy_growth_ttm',
     'dividends_yield_current',
     'sector.tr',
     'sector',
     'market',
     'AnalystRating.tr',
     'AnalystRating',
     'relative_volume_10d_calc',
 )
 .where(
     col('is_primary') == True,
     col('typespecs').has('common'),
     col('type') == 'stock',
     col('close').between(2, 10000),
     col('change') > 0,
     col('active_symbol') == True,
 )
 .order_by('change', ascending=False, nulls_first=False)
 .limit(100)
 .set_markets('india')
 .set_property('symbols', {'query': {'types': ['stock', 'fund', 'dr']}})
 .set_property('preset', 'gainers'))

print(screen.get_scanner_data())
