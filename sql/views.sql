-- Daily returns per ticker
CREATE OR REPLACE VIEW stox.v_returns AS
SELECT 
    ticker,
    date,
    close,
    LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close,
    (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date)) / LAG(close) OVER (PARTITION BY ticker ORDER BY date) as daily_return
FROM stox.prices
WHERE LAG(close) OVER (PARTITION BY ticker ORDER BY date) IS NOT NULL;

-- Moving averages
CREATE OR REPLACE VIEW stox.v_sma AS
SELECT 
    ticker,
    date,
    close,
    AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as sma_7,
    AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as sma_20
FROM stox.prices;

-- 20-day rolling volatility
CREATE OR REPLACE VIEW stox.v_vol20 AS
SELECT 
    ticker,
    date,
    close,
    STDDEV(daily_return) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as vol_20
FROM stox.v_returns;

-- Drawdown analysis
CREATE OR REPLACE VIEW stox.v_drawdown AS
WITH running_peak AS (
    SELECT 
        ticker,
        date,
        close,
        MAX(close) OVER (PARTITION BY ticker ORDER BY date) as peak
    FROM stox.prices
)
SELECT 
    ticker,
    date,
    close,
    peak,
    (close - peak) / peak as drawdown,
    MIN((close - peak) / peak) OVER (PARTITION BY ticker ORDER BY date ROWS UNBOUNDED PRECEDING) as max_drawdown
FROM running_peak;

-- 60-day rolling correlation between tickers
CREATE OR REPLACE VIEW stox.v_corr AS
WITH returns_data AS (
    SELECT 
        ticker,
        date,
        daily_return
    FROM stox.v_returns
    WHERE daily_return IS NOT NULL
),
correlation_data AS (
    SELECT 
        a.ticker as ticker1,
        b.ticker as ticker2,
        a.date,
        a.daily_return as return1,
        b.daily_return as return2
    FROM returns_data a
    JOIN returns_data b ON a.date = b.date AND a.ticker < b.ticker
)
SELECT 
    ticker1,
    ticker2,
    date,
    CORR(return1, return2) OVER (
        PARTITION BY ticker1, ticker2 
        ORDER BY date 
        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
    ) as correlation_60d
FROM correlation_data
WHERE CORR(return1, return2) OVER (
    PARTITION BY ticker1, ticker2 
    ORDER BY date 
    ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
) IS NOT NULL;
