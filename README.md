# База данных для сервиса "Мой девайс"

## Создание и заполнение базы данных

``` shell
# Создаем базу данных
psql -c 'CREATE DATABASE my_device;'
# Устанавливаем зависимости скрипта
pip install -r requirements.txt
# Заполняем базу данных
python3 manager.py fill
```

## Примеры запросов

### 1. Частоты встречаемости подписок по количеству продлений

```sql
SELECT continuations, COUNT(*) FROM (
    SELECT id, (SELECT COUNT(*) FROM succeeding_device_rents(id)) AS continuations FROM device_rent
) AS t GROUP BY continuations;
```

```
 continuations | count 
---------------+-------
             0 |  4979
             1 |  2431
             2 |  1186
             3 |   579
             4 |   291
             5 |   149
             6 |    78
             7 |    42
             8 |    27
             9 |    15
            10 |     7
            11 |     6
            12 |     3
            13 |     1
            14 |     1
            15 |     1
(16 rows)

```

### 2. Топ-5 людей по количеству поставленных звезд

```sql
SELECT customer.first_name, customer.last_name, SUM(feedback.stars) AS total_stars
FROM feedback
JOIN device_rent ON feedback.device_rent_id = device_rent.id
JOIN customer ON device_rent.customer_id = customer.id
GROUP BY customer.id
ORDER BY total_stars DESC
LIMIT 5;
```

```
 first_name | last_name | total_stars 
------------+-----------+-------------
 Вероника   | Климова   |          32
 Ева        | Никитина  |          30
 Елизавета  | Лопатина  |          28
 Ксения     | Маркова   |          27
 Даниил     | Кошелев   |          26
(5 rows)

```

### 3. Телефон человека, нанесшего больше всего урона

```sql
SELECT customer.phone, SUM(device_repair.price) AS damage
FROM device_repair
JOIN device_rent_ownership ON device_rent_ownership.device_ownership_id = device_repair.device_ownership_id
JOIN device_rent ON device_rent.id = device_rent_ownership.device_rent_id
JOIN customer ON customer.id = device_rent.customer_id
GROUP BY customer.id
ORDER BY damage DESC
LIMIT 1;
```

```
       phone        |   damage    
--------------------+-------------
 +7 (563) 969-57-25 | $136,500.00
(1 row)

```

### 4. Подсчет выручки по годам

```sql
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
```

```
 year |  rent_income   | ensurance_income | fine_income | repair_expenses | total_revenue  
------+----------------+------------------+-------------+-----------------+----------------
 2022 |  $1,523,200.00 |        $5,500.00 |  $14,000.00 |      $11,000.00 |  $1,531,700.00
 2021 | $64,302,130.00 |      $533,500.00 | $212,500.00 |     $164,500.00 | $64,883,630.00
 2020 | $58,559,040.00 |      $440,000.00 | $161,500.00 |     $122,500.00 | $59,038,040.00
 2019 | $54,944,560.00 |      $456,500.00 | $119,000.00 |      $89,000.00 | $55,431,060.00
 2018 | $54,089,560.00 |      $478,500.00 | $157,000.00 |     $141,500.00 | $54,583,560.00
 2017 | $28,269,510.00 |      $269,500.00 |  $89,500.00 |      $68,500.00 | $28,560,010.00
(6 rows)

```

### 5. Средняя длина комментариев пользователей разных типов устройств

```sql
SELECT device_model.kind, char_length(string_agg(feedback.message, ''))::float / COUNT(*) AS wordiness
FROM feedback
JOIN device_rent ON feedback.device_rent_id = device_rent.id
JOIN customer ON customer.id = device_rent.customer_id
JOIN device_model ON device_model.id = device_rent.device_model_id
WHERE feedback.message IS NOT NULL
GROUP BY device_model.kind
ORDER BY wordiness DESC;
```

```
       kind       |     wordiness      
------------------+--------------------
 tv               | 22.307692307692307
 scooter          | 21.759493670886076
 exercise_machine | 21.063492063492063
 bicycle          | 19.428571428571427
 game_console     | 13.538461538461538
(5 rows)

```
