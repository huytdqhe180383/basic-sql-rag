-- Simple SQL-RAG schema: 3 tables matching the CSV sources directly.
-- No staging/core/mart separation, no normalization splits.
-- Kept in public schema for minimal qualification overhead.

DROP SCHEMA IF EXISTS stg CASCADE;
DROP SCHEMA IF EXISTS core CASCADE;
DROP SCHEMA IF EXISTS mart CASCADE;

DROP TABLE IF EXISTS public.order_items CASCADE;
DROP TABLE IF EXISTS public.orders CASCADE;
DROP TABLE IF EXISTS public.customers CASCADE;

CREATE TABLE public.customers (
    customer_id         INTEGER PRIMARY KEY,
    zip                 INTEGER NOT NULL,
    signup_date         DATE NOT NULL,
    gender              TEXT NOT NULL,
    age_group           TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL
);

CREATE TABLE public.orders (
    order_id        INTEGER PRIMARY KEY,
    order_date      DATE NOT NULL,
    customer_id     INTEGER NOT NULL REFERENCES public.customers(customer_id),
    zip             INTEGER NOT NULL,
    order_status    TEXT NOT NULL,
    payment_method  TEXT NOT NULL,
    device_type     TEXT NOT NULL,
    order_source    TEXT NOT NULL
);

CREATE TABLE public.order_items (
    order_item_id   INTEGER PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES public.orders(order_id),
    product_id      INTEGER NOT NULL,
    quantity        INTEGER NOT NULL,
    unit_price      NUMERIC(14, 2) NOT NULL,
    discount_amount NUMERIC(14, 2) NOT NULL,
    promo_id        TEXT,
    promo_id_2      TEXT
);
