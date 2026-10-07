-- =====================================================================
-- 02_views.sql  |  Reusable views (a VIEW is a saved SELECT; it stores no data)
-- =====================================================================

-- Adds the promised SLA days, the SLA result (On Time / Late / N/A) and delay days.
--   Late = delivered AFTER the promised number of days.
CREATE VIEW v_shipment_sla AS
SELECT
    s.*,
    l.sla_days,
    CASE
        WHEN s.status <> 'Delivered'        THEN 'N/A'
        WHEN s.transit_days <= l.sla_days   THEN 'On Time'
        ELSE 'Late'
    END AS sla_status,
    CASE
        WHEN s.status = 'Delivered' AND s.transit_days > l.sla_days
            THEN s.transit_days - l.sla_days
        ELSE 0
    END AS delay_days
FROM shipments s
JOIN service_levels l ON s.service_type = l.service_type;

-- Flat one-row-per-shipment table with origin and destination branch details.
-- The branches table is joined TWICE (once as origin ob, once as destination db).
CREATE VIEW v_shipment_full AS
SELECT
    v.*,
    ob.city  AS origin_city,  ob.state AS origin_state,  ob.zone AS origin_zone,
    db.city  AS dest_city,    db.state AS dest_state,    db.zone AS dest_zone
FROM v_shipment_sla v
JOIN branches ob ON v.origin_branch_id = ob.branch_id
JOIN branches db ON v.dest_branch_id   = db.branch_id;
