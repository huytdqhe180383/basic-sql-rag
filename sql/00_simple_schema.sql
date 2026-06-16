-- Simple SQL-RAG schema: 7 tables matching the CSV sources directly.
-- No staging/core/mart separation, no normalization splits.
-- Kept in public schema for minimal qualification overhead.

DROP TABLE IF EXISTS public.inventory CASCADE;
DROP TABLE IF EXISTS public.sales CASCADE;
DROP TABLE IF EXISTS public.geography CASCADE;
DROP TABLE IF EXISTS public.products CASCADE;
DROP TABLE IF EXISTS public.order_items CASCADE;
DROP TABLE IF EXISTS public.orders CASCADE;
DROP TABLE IF EXISTS public.customers CASCADE;

CREATE TABLE public.geography (
    zip      INTEGER PRIMARY KEY,
    city     TEXT NOT NULL,
    region   TEXT NOT NULL,
    district TEXT NOT NULL
);

CREATE TABLE public.products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    segment      TEXT NOT NULL,
    size         TEXT NOT NULL,
    color        TEXT NOT NULL,
    price        NUMERIC(14, 2) NOT NULL,
    cogs         NUMERIC(14, 2) NOT NULL
);

CREATE TABLE public.customers (
    customer_id         INTEGER PRIMARY KEY,
    zip                 INTEGER NOT NULL REFERENCES public.geography(zip),
    signup_date         DATE NOT NULL,
    gender              TEXT NOT NULL,
    age_group           TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL
);

CREATE TABLE public.orders (
    order_id        INTEGER PRIMARY KEY,
    order_date      DATE NOT NULL,
    customer_id     INTEGER NOT NULL REFERENCES public.customers(customer_id),
    zip             INTEGER NOT NULL REFERENCES public.geography(zip),
    order_status    TEXT NOT NULL,
    payment_method  TEXT NOT NULL,
    device_type     TEXT NOT NULL,
    order_source    TEXT NOT NULL
);

CREATE TABLE public.order_items (
    order_item_id   INTEGER PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES public.orders(order_id),
    product_id      INTEGER NOT NULL REFERENCES public.products(product_id),
    quantity        INTEGER NOT NULL,
    unit_price      NUMERIC(14, 2) NOT NULL,
    discount_amount NUMERIC(14, 2) NOT NULL,
    promo_id        TEXT,
    promo_id_2      TEXT
);

CREATE TABLE public.sales (
    Date    DATE NOT NULL,
    Revenue NUMERIC(14, 2) NOT NULL,
    COGS    NUMERIC(14, 2) NOT NULL
);

CREATE TABLE public.inventory (
    snapshot_date    DATE NOT NULL,
    product_id       INTEGER NOT NULL REFERENCES public.products(product_id),
    stock_on_hand    INTEGER NOT NULL,
    units_received   INTEGER NOT NULL,
    units_sold       INTEGER NOT NULL,
    stockout_days    INTEGER NOT NULL,
    days_of_supply   NUMERIC(14, 2) NOT NULL,
    fill_rate        NUMERIC(5, 4) NOT NULL,
    stockout_flag    BOOLEAN NOT NULL,
    overstock_flag   BOOLEAN NOT NULL,
    reorder_flag     BOOLEAN NOT NULL,
    sell_through_rate NUMERIC(5, 4) NOT NULL,
    year             INTEGER NOT NULL,
    month            INTEGER NOT NULL
);
