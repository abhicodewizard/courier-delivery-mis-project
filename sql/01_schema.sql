-- =====================================================================
-- 01_schema.sql  |  Courier Delivery Performance & MIS
-- Works in MySQL 8+ and SQLite 3.25+ (tested on SQLite).
-- Design: 3 related tables
--   branches (1) ---< shipments >--- (1) service_levels
--   shipments has TWO links to branches: origin_branch_id and dest_branch_id
-- =====================================================================

DROP VIEW  IF EXISTS v_shipment_full;
DROP VIEW  IF EXISTS v_shipment_sla;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS branches;
DROP TABLE IF EXISTS service_levels;

CREATE TABLE branches (
    branch_id    VARCHAR(5)   NOT NULL PRIMARY KEY,
    branch_name  VARCHAR(50)  NOT NULL,
    city         VARCHAR(50)  NOT NULL,
    state        VARCHAR(50)  NOT NULL,
    zone         VARCHAR(10)  NOT NULL
);

CREATE TABLE service_levels (
    service_type VARCHAR(15)  NOT NULL PRIMARY KEY,
    sla_days     INT          NOT NULL        -- promised delivery time in days
);

CREATE TABLE shipments (
    awb_number          VARCHAR(15)   NOT NULL PRIMARY KEY,   -- unique tracking number
    booking_date        DATE          NOT NULL,
    delivery_date       DATE          NULL,                   -- NULL until delivered
    booking_year        INT           NOT NULL,
    booking_quarter     VARCHAR(2)    NOT NULL,
    booking_month       VARCHAR(7)    NOT NULL,               -- YYYY-MM (sorts correctly)
    booking_month_no    INT           NOT NULL,               -- 1..12 (for seasonality)
    origin_branch_id    VARCHAR(5)    NOT NULL,
    dest_branch_id      VARCHAR(5)    NOT NULL,
    service_type        VARCHAR(15)   NOT NULL,
    weight_kg           DECIMAL(6,2)  NOT NULL,
    freight_amount      DECIMAL(10,2) NOT NULL,               -- INR
    payment_mode        VARCHAR(20)   NOT NULL,
    cod_amount          DECIMAL(10,2) NOT NULL,
    status              VARCHAR(15)   NOT NULL,               -- Delivered / RTO / In Transit
    delivery_attempts   INT           NOT NULL,
    delay_return_reason VARCHAR(30)   NOT NULL,               -- 'None' when there was no issue
    customer_type       VARCHAR(5)    NOT NULL,               -- B2C / B2B
    customer_rating     INT           NULL,                   -- NULL = customer did not rate
    transit_days        INT           NULL,                   -- NULL unless delivered
    FOREIGN KEY (origin_branch_id) REFERENCES branches (branch_id),
    FOREIGN KEY (dest_branch_id)   REFERENCES branches (branch_id),
    FOREIGN KEY (service_type)     REFERENCES service_levels (service_type)
);

CREATE INDEX idx_ship_origin  ON shipments (origin_branch_id);
CREATE INDEX idx_ship_dest    ON shipments (dest_branch_id);
CREATE INDEX idx_ship_month   ON shipments (booking_month);
CREATE INDEX idx_ship_status  ON shipments (status);
