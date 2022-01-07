--- База данных my_device ---

--- Пользователь --------------------------------------------------------------

CREATE TABLE customer (
    id serial PRIMARY KEY,
    phone varchar (20) NOT NULL UNIQUE,
    password_md5 uuid NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    registration_timestamp timestamp DEFAULT CURRENT_TIMESTAMP,

    CHECK (phone ~ '^(\+\d{1,2} )?(\(\d{3}\) )?\d{3}-\d{2}-\d{2}$')
);

COMMENT ON TABLE customer IS 'Пользоветель сервиса';
COMMENT ON COLUMN customer.id IS 'Уникальный идентификатор';
COMMENT ON COLUMN customer.phone IS 'Номер телефона';
COMMENT ON COLUMN customer.password_md5 IS 'MD5-хеш пароля';
COMMENT ON COLUMN customer.first_name IS 'Имя';
COMMENT ON COLUMN customer.last_name IS 'Фамилия';
COMMENT ON COLUMN customer.registration_timestamp IS 'Дата и время регистрации';

--- Производитель устройства --------------------------------------------------

CREATE TABLE manufacturer (
    id serial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    country text
);

COMMENT ON TABLE manufacturer IS 'Производитель устройства';
COMMENT ON COLUMN manufacturer.id IS 'Уникальный идентификатор';
COMMENT ON COLUMN manufacturer.name IS 'Название бренда';
COMMENT ON COLUMN manufacturer.country IS 'Страна производителя';

--- Тип устройства ------------------------------------------------------------

CREATE TYPE device_kind AS enum (
    'scooter', 'bicycle', 'exercise_machine', 'game_console', 'tv'
);

COMMENT ON TYPE device_kind IS 'Тип устройства';

--- Модель устройства ---------------------------------------------------------

CREATE TABLE device_model (
    id serial PRIMARY KEY,
    manufacturer_id integer REFERENCES manufacturer (id) ON DELETE SET NULL,
    kind device_kind,
    name text
);

COMMENT ON TABLE device_model IS 'Модель устройства';
COMMENT ON COLUMN device_model.id IS 'Уникальный идентификатор';
COMMENT ON COLUMN device_model.manufacturer_id IS 'Уникальный идентификатор производителя';
COMMENT ON COLUMN device_model.kind IS 'Тип девайса';
COMMENT ON COLUMN device_model.name IS 'Название модели';

--- Характеристика модели устройства ------------------------------------------

CREATE TABLE device_model_property (
    device_model_id integer NOT NULL REFERENCES device_model (id) ON DELETE CASCADE,
    key text NOT NULL,
    value text,

	PRIMARY KEY (device_model_id, key)
);

COMMENT ON TABLE device_model_property IS 'Характеристика модели устройства';
COMMENT ON COLUMN device_model_property.device_model_id IS 'Уникальный идентификатор';
COMMENT ON COLUMN device_model_property.key IS 'Название характеристики';
COMMENT ON COLUMN device_model_property.value IS 'Значение характеристики';

--- Ссылка на изображение модели устройства -----------------------------------

CREATE TABLE device_model_image (
    device_model_id integer NOT NULL REFERENCES device_model (id) ON DELETE CASCADE,
    image_url text NOT NULL,

    PRIMARY KEY (device_model_id, image_url)
);

COMMENT ON TABLE device_model_image IS 'Ссылка на изображение модели устройства';
COMMENT ON COLUMN device_model_image.device_model_id IS 'Уникальный идентификатор модели устройства';
COMMENT ON COLUMN device_model_image.image_url IS 'URL изображения';

--- Цена аренды устройсва -----------------------------------------------------

CREATE TABLE device_model_rent_price (
    device_model_id integer NOT NULL REFERENCES device_model (id) ON DELETE CASCADE,
    price money NOT NULL,
    update_timestamp timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,

	PRIMARY KEY (device_model_id, update_timestamp)
);

COMMENT ON TABLE device_model_rent_price IS 'Цена аренды устройсва';
COMMENT ON COLUMN device_model_rent_price.device_model_id IS 'Уникальный идентификатор модели устройства';
COMMENT ON COLUMN device_model_rent_price.price IS 'Цена за аренду';
COMMENT ON COLUMN device_model_rent_price.update_timestamp IS 'Дата и время, с которых начинает действовать цена';

--- Экземпляр устройства ------------------------------------------------------

CREATE TABLE device (
    id serial PRIMARY KEY,
    model_id integer REFERENCES device_model (id) ON DELETE SET NULL,
    purchase_timestamp timestamp DEFAULT CURRENT_TIMESTAMP,
    retirement_timestamp timestamp,
    condition smallint CHECK (condition BETWEEN 1 AND 10),
    price money
);

COMMENT ON TABLE device IS 'Экземпляр устройства';
COMMENT ON COLUMN device.id IS 'Уникальный идентификатор';
COMMENT ON COLUMN device.model_id IS 'Уникальный идентификатор модели';
COMMENT ON COLUMN device.purchase_timestamp IS 'Дата и время покупки';
COMMENT ON COLUMN device.condition IS 'Состояние сохранности по шкале от 1 до 10';
COMMENT ON COLUMN device.price IS 'Цена закупки';

--- Статус возврата устройства ------------------------------------------------

CREATE TYPE device_return_status AS enum (
    'period_expired', 'early_return', 'breakage'
);

COMMENT ON TYPE device_return_status IS 'Статус возврата девайса';

--- Период фактического владения устройством ----------------------------------

CREATE TABLE device_ownership (
    id serial PRIMARY KEY,
    device_id integer REFERENCES device (id) ON DELETE SET NULL,
    begin_timestamp timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_timestamp timestamp,
    city varchar (50) DEFAULT 'Москва',
    return_status device_return_status DEFAULT 'period_expired',
    CHECK ((end_timestamp IS NULL) OR (begin_timestamp < end_timestamp))
);

COMMENT ON TABLE device_ownership IS 'Период фактического владения устройством';
COMMENT ON COLUMN device_ownership.device_id IS 'Уникальный идентификатор';
COMMENT ON COLUMN device_ownership.begin_timestamp IS 'Дата и время начала владения устройством';
COMMENT ON COLUMN device_ownership.end_timestamp IS 'Дата и время окончания влядения устройством';
COMMENT ON COLUMN device_ownership.city IS 'Город, в котором находилось устройство';
COMMENT ON COLUMN device_ownership.return_status IS 'Статус возврата устройства';

-- Провека того, что временная метка принадлежит хотя бы одному периоду владения устройством
CREATE OR REPLACE FUNCTION is_within_device_ownership(required_device_id integer, ts timestamp)
    RETURNS BOOLEAN
    LANGUAGE PLpgSQL AS
$func$
BEGIN
    RETURN (SELECT COUNT (*) FROM device_ownership WHERE
        (device_id = required_device_id) AND
        (end_timestamp IS NOT NULL) AND
        (ts BETWEEN begin_timestamp AND end_timestamp)
    ) > 0;
END
$func$;

ALTER TABLE device_ownership ADD CONSTRAINT device_ownership_check_begin_timestamp
    CHECK (NOT is_within_device_ownership(device_id, begin_timestamp));

ALTER TABLE device_ownership ADD CONSTRAINT device_ownership_check_end_timestamp
    CHECK ((end_timestamp IS NULL) OR (NOT is_within_device_ownership(device_id, end_timestamp)));

--- Период формальной аренды устройства ---------------------------------------

CREATE TABLE device_rent (
    id serial PRIMARY KEY,
    customer_id integer REFERENCES customer (id) ON DELETE SET NULL,
    device_model_id integer REFERENCES device_model (id) ON DELETE SET NULL,
    begin_timestamp timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_timestamp timestamp,
    is_insured boolean DEFAULT FALSE,
    previous_device_rent_id integer REFERENCES device_rent (id) ON DELETE SET NULL,
    CHECK ((end_timestamp IS NULL) OR (begin_timestamp < end_timestamp)),
    CHECK (previous_device_rent_id <> id)
);

COMMENT ON TABLE device_rent IS 'Период формальной аренды устройства';
COMMENT ON COLUMN device_rent.id IS 'Уникальный идентификатор';
COMMENT ON COLUMN device_rent.device_model_id IS 'Уникальный идентификатор модели';
COMMENT ON COLUMN device_rent.begin_timestamp IS 'Дата и время начала аренды устройства';
COMMENT ON COLUMN device_rent.end_timestamp IS 'Дата и время конца аренды устройства';
COMMENT ON COLUMN device_rent.is_insured IS 'Наличие страховки устройства';
COMMENT ON COLUMN device_rent.previous_device_rent_id IS 'Предыдущий период аренды в случае продления';

CREATE OR REPLACE FUNCTION device_rent_end_timestamp(idx integer)
    RETURNS timestamp
    LANGUAGE PLpgSQL AS
$func$
BEGIN
    RETURN (SELECT end_timestamp FROM device_rent WHERE id = idx);
END
$func$;

ALTER TABLE device_rent ADD CONSTRAINT device_rent_check_previous_device_rent_end_timestamp
    CHECK ((previous_device_rent_id IS NULL) OR (device_rent_end_timestamp(previous_device_rent_id) = begin_timestamp));

-- Получение последовательности всех последующих продленных аренд
CREATE OR REPLACE FUNCTION succeeding_device_rents(device_rent_id integer)
    RETURNS SETOF device_rent
    LANGUAGE PLpgSQL AS
$func$
DECLARE
    x device_rent%rowtype;
BEGIN
    LOOP
        SELECT * FROM device_rent WHERE previous_device_rent_id = device_rent_id INTO x;
        EXIT WHEN x IS NULL;
        RETURN NEXT x;
        device_rent_id := x.id;
    END LOOP;
END
$func$;

-- Автоматическая инициализация времени окончания аренды
CREATE OR REPLACE FUNCTION device_rent_default_end_timestamp() 
    RETURNS trigger
    LANGUAGE plpgsql AS
$func$
BEGIN
    NEW.end_timestamp := NEW.begin_timestamp + interval '1 month';
    RETURN NEW;
END
$func$;

CREATE TRIGGER device_rent_default_end_timestamp_trigger
BEFORE INSERT ON device_rent
FOR EACH ROW
WHEN (NEW.end_timestamp IS NULL)
EXECUTE PROCEDURE device_rent_default_end_timestamp();

--- Связь периодов аренды устройств и вледения ими ---------------------------

CREATE TABLE device_rent_ownership (
    device_rent_id integer REFERENCES device_rent (id) ON DELETE CASCADE,
    device_ownership_id integer REFERENCES device_ownership (id) ON DELETE CASCADE,
    PRIMARY KEY (device_rent_id, device_ownership_id)
);

--- Отзыв пользователя об аранде девайса --------------------------------------

CREATE TABLE feedback (
    device_rent_id serial PRIMARY KEY REFERENCES device_rent (id) ON DELETE CASCADE,
    stars smallint NOT NULL CHECK (stars BETWEEN 1 AND 5),
    timestamp timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message text
);

COMMENT ON TABLE feedback IS 'Отзыв пользователя об аранде девайса';
COMMENT ON COLUMN feedback.stars IS 'Количество звезд (от 1 до 5)';
COMMENT ON COLUMN feedback.timestamp IS 'Дата и время отзыва';
COMMENT ON COLUMN feedback.message IS 'Текст отзыва пользователя';

--- Починка сломанного устройства ---------------------------------------------

CREATE TABLE device_repair (
    id serial PRIMARY KEY,
    device_ownership_id integer REFERENCES device_ownership (id) ON DELETE CASCADE,
    price money,
    begin_timestamp timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_timestamp timestamp,
    CHECK ((end_timestamp IS NULL) OR (begin_timestamp < end_timestamp))
);

COMMENT ON TABLE device_repair IS 'Починка сломанного устройства';
COMMENT ON COLUMN device_repair.device_ownership_id IS 'Уникальный идентификатор периода владения, в котором устройство сломалось';
COMMENT ON COLUMN device_repair.price IS 'Цена ремонта';
COMMENT ON COLUMN device_repair.begin_timestamp IS 'Дата и время начала ремонта';
COMMENT ON COLUMN device_repair.end_timestamp IS 'Дата и время окончания ремонта';

--- Штраф за поломку устройства -----------------------------------------------

CREATE TABLE damage_fine (
    device_ownership_id integer PRIMARY KEY REFERENCES device_ownership (id) ON DELETE CASCADE,
    fine money NOT NULL,
    device_repair_id integer REFERENCES device_repair (id) ON DELETE SET NULL
);

COMMENT ON TABLE damage_fine IS 'Штраф за поломку устройства';
COMMENT ON COLUMN damage_fine.device_ownership_id IS 'Уникальный идентификатор периода владения устройством, во время которого случилась поломка';
COMMENT ON COLUMN damage_fine.fine IS 'Размер  штрафа';
COMMENT ON COLUMN damage_fine.device_repair_id IS 'Уникальный идентификатор починки устройства';
