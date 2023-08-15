-- Financial Dashboard Schema
-- All financial figures are in thousands USD (000s omitted)

CREATE TABLE IF NOT EXISTS companies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    ticker      VARCHAR(10)  UNIQUE,
    sector      VARCHAR(100),
    founded_year INTEGER
);

CREATE TABLE IF NOT EXISTS financial_metrics (
    id                  SERIAL PRIMARY KEY,
    company_id          INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    year                INTEGER NOT NULL,
    quarter             VARCHAR(2) NOT NULL CHECK (quarter IN ('Q1','Q2','Q3','Q4')),
    revenue             NUMERIC(15,2),
    cost_of_revenue     NUMERIC(15,2),
    gross_profit        NUMERIC(15,2),
    operating_expenses  NUMERIC(15,2),
    ebitda              NUMERIC(15,2),
    net_income          NUMERIC(15,2),
    user_count          BIGINT,
    employee_count      INTEGER,
    UNIQUE (company_id, year, quarter)
);

CREATE TABLE IF NOT EXISTS segments (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    year          INTEGER NOT NULL,
    quarter       VARCHAR(2) NOT NULL,
    segment_name  VARCHAR(100) NOT NULL,
    revenue       NUMERIC(15,2),
    growth_yoy    NUMERIC(6,2)
);

-- Convenience view: full P&L with derived margins
CREATE OR REPLACE VIEW pnl_summary AS
SELECT
    c.name                                                       AS company,
    fm.year,
    fm.quarter,
    fm.revenue,
    fm.gross_profit,
    ROUND(fm.gross_profit / NULLIF(fm.revenue, 0) * 100, 2)     AS gross_margin_pct,
    fm.operating_expenses,
    fm.ebitda,
    fm.net_income,
    ROUND(fm.net_income  / NULLIF(fm.revenue, 0) * 100, 2)      AS net_margin_pct,
    fm.user_count,
    fm.employee_count,
    ROUND(fm.revenue / NULLIF(fm.employee_count, 0), 2)         AS revenue_per_employee
FROM financial_metrics fm
JOIN companies c ON c.id = fm.company_id
ORDER BY fm.year, fm.quarter;

-- Quarter and year composite index for range queries
-- CREATE INDEX IF NOT EXISTS idx_fin_year_quarter ON financial_data(year, quarter);
