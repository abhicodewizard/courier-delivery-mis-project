-- =====================================================================
-- 03_business_queries.sql  |  Delivery performance analysis
-- Each block starts with "-- Q<number>: title" (the runner script relies on this).
-- Works in MySQL 8+ and SQLite 3.25+.
-- Definitions: On-Time % = on-time deliveries / delivered shipments
--              RTO %     = RTO / (Delivered + RTO)   (In Transit is excluded)
-- =====================================================================

-- Q1: Overall KPIs
-- Business question: How is the network performing overall?
-- Concepts: conditional aggregation (CASE WHEN inside SUM), AVG ignores NULL
SELECT
    COUNT(*)                                                          AS total_shipments,
    SUM(CASE WHEN status = 'Delivered'  THEN 1 ELSE 0 END)            AS delivered,
    SUM(CASE WHEN status = 'RTO'        THEN 1 ELSE 0 END)            AS rto,
    SUM(CASE WHEN status = 'In Transit' THEN 1 ELSE 0 END)            AS in_transit,
    SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END)           AS on_time,
    ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END), 2) AS on_time_pct,
    ROUND(AVG(transit_days), 2)                                       AS avg_transit_days,
    ROUND(100.0 * SUM(CASE WHEN status = 'RTO' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN status IN ('Delivered', 'RTO') THEN 1 ELSE 0 END), 2) AS rto_pct,
    ROUND(SUM(freight_amount), 0)                                     AS total_freight_revenue
FROM v_shipment_sla;

-- Q2: Shipment status breakdown
-- Business question: What share of shipments is delivered, returned or still moving?
-- Concepts: GROUP BY, scalar subquery for the total
SELECT
    status,
    COUNT(*) AS shipments,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM shipments), 2) AS share_pct
FROM shipments
GROUP BY status
ORDER BY shipments DESC;

-- Q3: Service-type performance against SLA
-- Business question: Do we keep the promise we make for each service?
-- Concepts: view, WHERE before GROUP BY, conditional AVG
SELECT
    service_type,
    sla_days,
    COUNT(*)                                                                   AS delivered,
    ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct,
    ROUND(AVG(transit_days), 2)                                                AS avg_transit_days,
    ROUND(AVG(CASE WHEN sla_status = 'Late' THEN delay_days END), 2)           AS avg_delay_days_when_late
FROM v_shipment_sla
WHERE status = 'Delivered'
GROUP BY service_type, sla_days
ORDER BY on_time_pct;

-- Q4: Destination branch ranking by on-time %
-- Business question: Which branches deliver best and worst?
-- Concepts: CTE, RANK() window function
WITH branch_stats AS (
    SELECT
        dest_city,
        dest_zone,
        COUNT(*) AS delivered,
        ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct,
        ROUND(AVG(transit_days), 2) AS avg_transit_days
    FROM v_shipment_full
    WHERE status = 'Delivered'
    GROUP BY dest_city, dest_zone
)
SELECT
    dest_city, dest_zone, delivered, on_time_pct, avg_transit_days,
    RANK() OVER (ORDER BY on_time_pct DESC) AS performance_rank
FROM branch_stats
ORDER BY performance_rank;

-- Q5: Best and worst branch inside each zone
-- Business question: Who is the weakest branch within each zone?
-- Concepts: RANK() with PARTITION BY (rank restarts for every zone)
WITH branch_stats AS (
    SELECT
        dest_zone,
        dest_city,
        COUNT(*) AS delivered,
        ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct
    FROM v_shipment_full
    WHERE status = 'Delivered'
    GROUP BY dest_zone, dest_city
)
SELECT
    dest_zone, dest_city, delivered, on_time_pct,
    RANK() OVER (PARTITION BY dest_zone ORDER BY on_time_pct DESC) AS rank_in_zone
FROM branch_stats
ORDER BY dest_zone, rank_in_zone;

-- Q6: Branches below the company average on-time %
-- Business question: Which branches need an action plan?
-- Concepts: HAVING with a scalar subquery
SELECT
    dest_city,
    COUNT(*) AS delivered,
    ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct
FROM v_shipment_full
WHERE status = 'Delivered'
GROUP BY dest_city
HAVING 100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*) <
       (SELECT 100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*)
        FROM v_shipment_sla WHERE status = 'Delivered')
ORDER BY on_time_pct;

-- Q7: Zone-to-zone lane performance
-- Business question: Which long-distance lanes (origin zone to destination zone) are weakest?
-- Concepts: GROUP BY two columns, HAVING to ignore tiny lanes
SELECT
    origin_zone,
    dest_zone,
    COUNT(*) AS delivered,
    ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct,
    ROUND(AVG(transit_days), 2) AS avg_transit_days
FROM v_shipment_full
WHERE status = 'Delivered'
GROUP BY origin_zone, dest_zone
HAVING COUNT(*) >= 100
ORDER BY on_time_pct;

-- Q8: Top 10 busiest city lanes
-- Business question: Where is our volume and how do those lanes perform?
-- Concepts: JOINing the same table (branches) twice with aliases ob / db
SELECT
    ob.city AS origin_city,
    db.city AS dest_city,
    COUNT(*) AS shipments,
    SUM(CASE WHEN s.status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
    ROUND(100.0 * SUM(CASE WHEN s.status = 'Delivered' AND s.transit_days <= l.sla_days THEN 1 ELSE 0 END)
          / SUM(CASE WHEN s.status = 'Delivered' THEN 1 ELSE 0 END), 2) AS on_time_pct,
    ROUND(AVG(s.transit_days), 2) AS avg_transit_days
FROM shipments s
JOIN branches       ob ON s.origin_branch_id = ob.branch_id
JOIN branches       db ON s.dest_branch_id   = db.branch_id
JOIN service_levels l  ON s.service_type     = l.service_type
GROUP BY ob.city, db.city
ORDER BY shipments DESC
LIMIT 10;

-- Q9: Monthly trend
-- Business question: How do volume and on-time % change month by month?
-- Concepts: GROUP BY a period column, conditional aggregation
SELECT
    booking_month,
    COUNT(*) AS shipments,
    SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
    ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END), 2) AS on_time_pct,
    ROUND(AVG(transit_days), 2) AS avg_transit_days
FROM v_shipment_sla
GROUP BY booking_month
ORDER BY booking_month;

-- Q10: Month-over-month change in shipment volume
-- Business question: How fast is volume growing or falling from one month to the next?
-- Concepts: CTE, LAG() window function (looks at the previous row)
WITH monthly AS (
    SELECT booking_month, COUNT(*) AS shipments
    FROM shipments
    GROUP BY booking_month
)
SELECT
    booking_month,
    shipments,
    LAG(shipments) OVER (ORDER BY booking_month) AS previous_month,
    ROUND(100.0 * (shipments - LAG(shipments) OVER (ORDER BY booking_month))
          / LAG(shipments) OVER (ORDER BY booking_month), 1) AS mom_change_pct
FROM monthly
ORDER BY booking_month;

-- Q11: Cumulative freight revenue
-- Business question: How does revenue build up over time?
-- Concepts: running total with SUM() OVER (ORDER BY ...)
WITH monthly AS (
    SELECT booking_month, SUM(freight_amount) AS revenue
    FROM shipments
    GROUP BY booking_month
)
SELECT
    booking_month,
    ROUND(revenue, 0) AS revenue,
    ROUND(SUM(revenue) OVER (ORDER BY booking_month), 0) AS cumulative_revenue
FROM monthly
ORDER BY booking_month;

-- Q12: Seasonality by calendar month (both years combined)
-- Business question: Which calendar months are busiest and hardest on delivery performance?
-- Concepts: GROUP BY month number, conditional aggregation
SELECT
    booking_month_no,
    COUNT(*) AS shipments,
    ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END), 2) AS on_time_pct
FROM v_shipment_sla
GROUP BY booking_month_no
ORDER BY booking_month_no;

-- Q13: Reasons behind late deliveries
-- Business question: What causes SLA breaches?
-- Concepts: WHERE, GROUP BY, window over aggregate for share of total
SELECT
    delay_return_reason AS reason,
    COUNT(*)                        AS late_shipments,
    ROUND(AVG(delay_days), 2)       AS avg_delay_days,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM v_shipment_sla
WHERE sla_status = 'Late'
GROUP BY delay_return_reason
ORDER BY late_shipments DESC;

-- Q14: RTO (returned shipments) by payment mode
-- Business question: Does Cash on Delivery increase returns?
-- Concepts: CASE WHEN, HAVING
SELECT
    payment_mode,
    COUNT(*) AS closed_shipments,
    SUM(CASE WHEN status = 'RTO' THEN 1 ELSE 0 END) AS rto,
    ROUND(100.0 * SUM(CASE WHEN status = 'RTO' THEN 1 ELSE 0 END) / COUNT(*), 2) AS rto_pct
FROM shipments
WHERE status IN ('Delivered', 'RTO')
GROUP BY payment_mode
HAVING COUNT(*) > 0
ORDER BY rto_pct DESC;

-- Q15: Why shipments are returned
-- Business question: What are the RTO reasons and how many are COD?
-- Concepts: WHERE, GROUP BY, conditional SUM
SELECT
    delay_return_reason AS rto_reason,
    COUNT(*) AS rto_shipments,
    SUM(CASE WHEN payment_mode = 'COD' THEN 1 ELSE 0 END) AS cod_shipments,
    ROUND(100.0 * SUM(CASE WHEN payment_mode = 'COD' THEN 1 ELSE 0 END) / COUNT(*), 1) AS cod_share_pct
FROM shipments
WHERE status = 'RTO'
GROUP BY delay_return_reason
ORDER BY rto_shipments DESC;

-- Q16: First-attempt delivery rate by branch
-- Business question: Where do we need more than one attempt?
-- Concepts: conditional aggregation, HAVING to keep branches with enough volume
SELECT
    dest_city,
    COUNT(*) AS delivered,
    ROUND(100.0 * SUM(CASE WHEN delivery_attempts = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS first_attempt_pct
FROM v_shipment_full
WHERE status = 'Delivered'
GROUP BY dest_city
HAVING COUNT(*) >= 100
ORDER BY first_attempt_pct;

-- Q17: Revenue by service type and customer type
-- Business question: Which segment brings the money?
-- Concepts: GROUP BY two columns, SUM, AVG
SELECT
    service_type,
    customer_type,
    COUNT(*) AS shipments,
    ROUND(SUM(freight_amount), 0) AS freight_revenue,
    ROUND(AVG(freight_amount), 2) AS avg_freight,
    ROUND(AVG(weight_kg), 2)      AS avg_weight_kg
FROM shipments
GROUP BY service_type, customer_type
ORDER BY freight_revenue DESC;

-- Q18: Performance by parcel weight band
-- Business question: Are heavy parcels delayed more often?
-- Concepts: CASE WHEN to create bands inside a derived table (subquery in FROM)
SELECT
    weight_band,
    COUNT(*) AS delivered,
    ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct,
    ROUND(AVG(freight_amount), 2) AS avg_freight
FROM (
    SELECT
        CASE
            WHEN weight_kg <= 1  THEN '1) Up to 1 kg'
            WHEN weight_kg <= 5  THEN '2) 1-5 kg'
            WHEN weight_kg <= 15 THEN '3) 5-15 kg'
            ELSE                      '4) Above 15 kg'
        END AS weight_band,
        sla_status, freight_amount
    FROM v_shipment_sla
    WHERE status = 'Delivered'
) AS banded
GROUP BY weight_band
ORDER BY weight_band;

-- Q19: Customer rating vs delivery outcome
-- Business question: Does a late delivery hurt customer satisfaction?
-- Concepts: IS NOT NULL (NULL = not rated), AVG, GROUP BY
SELECT
    sla_status,
    COUNT(customer_rating)         AS rated_shipments,
    ROUND(AVG(customer_rating), 2) AS avg_rating
FROM v_shipment_sla
WHERE customer_rating IS NOT NULL
GROUP BY sla_status
ORDER BY avg_rating DESC;

-- Q20: Late % by destination zone and service type (matrix)
-- Business question: Which zone and service combinations break the promise most?
-- Concepts: conditional aggregation used to turn rows into columns (pivot)
SELECT
    dest_zone,
    ROUND(100.0 * SUM(CASE WHEN service_type = 'Express'  AND sla_status = 'Late' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN service_type = 'Express'  THEN 1 ELSE 0 END), 1) AS express_late_pct,
    ROUND(100.0 * SUM(CASE WHEN service_type = 'Standard' AND sla_status = 'Late' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN service_type = 'Standard' THEN 1 ELSE 0 END), 1) AS standard_late_pct,
    ROUND(100.0 * SUM(CASE WHEN service_type = 'Economy'  AND sla_status = 'Late' THEN 1 ELSE 0 END)
          / SUM(CASE WHEN service_type = 'Economy'  THEN 1 ELSE 0 END), 1) AS economy_late_pct
FROM v_shipment_full
WHERE status = 'Delivered'
GROUP BY dest_zone
ORDER BY dest_zone;

-- Q21: Branches that send no shipments (LEFT JOIN)
-- Business question: Which branches only receive parcels and never originate any?
-- Concepts: LEFT JOIN keeps branches with zero matches (INNER JOIN would hide them)
SELECT
    b.branch_name,
    b.city,
    COUNT(s.awb_number) AS outbound_shipments
FROM branches b
LEFT JOIN shipments s ON s.origin_branch_id = b.branch_id
GROUP BY b.branch_id, b.branch_name, b.city
ORDER BY outbound_shipments, b.city;

-- Q22: Three months with the lowest on-time %
-- Business question: When did service quality drop the most?
-- Concepts: HAVING, ORDER BY, LIMIT
SELECT
    booking_month,
    COUNT(*) AS delivered,
    ROUND(100.0 * SUM(CASE WHEN sla_status = 'On Time' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct
FROM v_shipment_sla
WHERE status = 'Delivered'
GROUP BY booking_month
HAVING COUNT(*) >= 100
ORDER BY on_time_pct
LIMIT 3;

-- Q23: Main cause of lateness for each branch
-- Business question: What is the number one delay reason at every destination branch?
-- Concepts: ROW_NUMBER() with PARTITION BY inside a CTE, then keep row number 1
WITH reason_counts AS (
    SELECT
        dest_city,
        delay_return_reason AS reason,
        COUNT(*) AS late_shipments,
        ROW_NUMBER() OVER (PARTITION BY dest_city ORDER BY COUNT(*) DESC) AS rn
    FROM v_shipment_full
    WHERE sla_status = 'Late'
    GROUP BY dest_city, delay_return_reason
)
SELECT dest_city, reason AS top_delay_reason, late_shipments
FROM reason_counts
WHERE rn = 1
ORDER BY late_shipments DESC;
