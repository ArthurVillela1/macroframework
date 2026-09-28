USE macro;
GO

DECLARE @cols NVARCHAR(MAX), @sql NVARCHAR(MAX);

-- Build the column list from the series in the table: [AVG_HOURLY_EARNINGS], [BREAKEVEN_10Y], ...
SELECT @cols = STRING_AGG(CAST(QUOTENAME(series_id) AS NVARCHAR(MAX)), ', ')
               WITHIN GROUP (ORDER BY series_id)
FROM (SELECT DISTINCT series_id FROM dbo.observations) s;

SET @sql = N'
CREATE OR ALTER VIEW dbo.observations_wide AS
SELECT obs_date, ' + @cols + N'
FROM (
    SELECT obs_date, series_id, value
    FROM dbo.observations
) src
PIVOT (
    MAX(value) FOR series_id IN (' + @cols + N')
) p;';

EXEC sp_executesql @sql;

SELECT *
FROM dbo.observations_wide
ORDER BY obs_date DESC;