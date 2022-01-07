-- Частоты встречаемости подписок по количеству продлений
SELECT continuations, COUNT(*) FROM (
    SELECT id, (SELECT COUNT(*) FROM succeeding_device_rents(id)) AS continuations FROM device_rent
) AS t GROUP BY continuations;

-- Топ-5 людей по количеству поставленных звезд
SELECT customer.first_name, customer.last_name, SUM(feedback.stars) AS total_stars
FROM feedback
JOIN device_rent ON feedback.device_rent_id = device_rent.id
JOIN customer ON device_rent.customer_id = customer.id
GROUP BY customer.id
ORDER BY total_stars DESC
LIMIT 5;

--- Телефон человека, нанесшего больше всего урона
SELECT customer.phone, SUM(device_repair.price) AS damage
FROM device_repair
JOIN device_rent_ownership ON device_rent_ownership.device_ownership_id = device_repair.device_ownership_id
JOIN device_rent ON device_rent.id = device_rent_ownership.device_rent_id
JOIN customer ON customer.id = device_rent.customer_id
GROUP BY customer.id
ORDER BY damage DESC
LIMIT 1;

-- Подсчет выручки по годам
SELECT
    a.year AS year,
    rent_income,
    ensurance_income,
    fine_income,
    repair_expenses,
    rent_income + ensurance_income + fine_income - repair_expenses AS total_revenue
FROM (
    SELECT
        EXTRACT(YEAR FROM device_rent.begin_timestamp) AS year,
        SUM(device_model_rent_price.price) AS rent_income,
        SUM((device_rent.is_insured::integer) * 500)::money AS ensurance_income
    FROM (
        SELECT device_rent.id AS device_rent_id, MAX(device_model_rent_price.update_timestamp) AS latest_price_update
        FROM device_rent
        JOIN device_model_rent_price ON device_rent.begin_timestamp >= device_model_rent_price.update_timestamp
        GROUP BY device_rent.id
    ) AS device_rents_prices
    JOIN device_model_rent_price ON device_model_rent_price.update_timestamp = latest_price_update
    JOIN device_rent ON device_rent.id = device_rent_id
    GROUP BY EXTRACT(YEAR FROM device_rent.begin_timestamp)
) AS a
JOIN (
    SELECT EXTRACT(YEAR FROM device_ownership.end_timestamp) AS year, SUM(damage_fine.fine) as fine_income
    FROM damage_fine 
    JOIN device_ownership ON damage_fine.device_ownership_id = device_ownership.id
    GROUP BY EXTRACT(YEAR FROM device_ownership.end_timestamp)
) AS b ON a.year = b.year
JOIN (
    SELECT EXTRACT(YEAR FROM begin_timestamp) AS year, SUM(price) AS repair_expenses FROM device_repair
    GROUP BY EXTRACT(YEAR FROM begin_timestamp)
) AS c ON b.year = c.year
ORDER BY year DESC;

-- Средняя длина комментариев пользователей разных типов устройств
SELECT device_model.kind, char_length(string_agg(feedback.message, ''))::float / COUNT(*) AS wordiness
FROM feedback
JOIN device_rent ON feedback.device_rent_id = device_rent.id
JOIN customer ON customer.id = device_rent.customer_id
JOIN device_model ON device_model.id = device_rent.device_model_id
WHERE feedback.message IS NOT NULL
GROUP BY device_model.kind
ORDER BY wordiness DESC;
