CREATE TABLE IF NOT EXISTS overdose_deaths (
  id                      SERIAL PRIMARY KEY,
  state_abbr              VARCHAR(2)   NOT NULL,
  state_name              VARCHAR(50)  NOT NULL,
  year                    INT          NOT NULL,
  month                   VARCHAR(20)  NOT NULL,
  period_end_date         DATE         NOT NULL,
  indicator               VARCHAR(100) NOT NULL,
  data_value              NUMERIC,
  predicted_value         NUMERIC,
  percent_complete        NUMERIC,
  loaded_at               TIMESTAMP    DEFAULT now(),
  UNIQUE (state_abbr, year, month, indicator)
);

CREATE INDEX IF NOT EXISTS idx_overdose_deaths_period ON overdose_deaths (period_end_date);
CREATE INDEX IF NOT EXISTS idx_overdose_deaths_indicator ON overdose_deaths (indicator);
