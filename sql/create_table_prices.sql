CREATE EXTERNAL TABLE IF NOT EXISTS stox.prices (
    date DATE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    adj_close DOUBLE
)
PARTITIONED BY (
    ticker STRING,
    year INT,
    month INT,
    day INT
)
STORED AS TEXTFILE
LOCATION 's3://stox-curated-demo-1234/prices/'
TBLPROPERTIES (
    'skip.header.line.count' = '1',
    'serialization.format' = ',',
    'field.delim' = ','
);
