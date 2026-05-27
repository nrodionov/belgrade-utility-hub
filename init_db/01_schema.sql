--
-- PostgreSQL database dump
--

\restrict mfJYyAmAZLDBQw32walDhdOcqCxUhyXtfWBa1UpSjsE56dWQkW8X8O8rSOfflLP

-- Dumped from database version 15.17
-- Dumped by pg_dump version 15.17

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: events; Type: TABLE; Schema: public; Owner: belgrade_user
--

CREATE TABLE public.events (
    id integer NOT NULL,
    category text NOT NULL,
    title_sr text NOT NULL,
    description_sr text,
    region text,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone,
    source_url text,
    hash_id text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    title_ru text,
    title_en text,
    description_ru text,
    description_en text,
    municipality text[],
    title_sl text,
    description_sl text
);


ALTER TABLE public.events OWNER TO belgrade_user;

--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: belgrade_user
--

CREATE SEQUENCE public.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.events_id_seq OWNER TO belgrade_user;

--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: belgrade_user
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: system_stats; Type: TABLE; Schema: public; Owner: belgrade_user
--

CREATE TABLE public.system_stats (
    key text NOT NULL,
    val_text text,
    val_ts timestamp with time zone
);


ALTER TABLE public.system_stats OWNER TO belgrade_user;

--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: belgrade_user
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: events events_hash_id_key; Type: CONSTRAINT; Schema: public; Owner: belgrade_user
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_hash_id_key UNIQUE (hash_id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: belgrade_user
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: system_stats system_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: belgrade_user
--

ALTER TABLE ONLY public.system_stats
    ADD CONSTRAINT system_stats_pkey PRIMARY KEY (key);


--
-- Name: idx_events_category; Type: INDEX; Schema: public; Owner: belgrade_user
--

CREATE INDEX idx_events_category ON public.events USING btree (category);


--
-- Name: idx_events_hash_id; Type: INDEX; Schema: public; Owner: belgrade_user
--

CREATE INDEX idx_events_hash_id ON public.events USING btree (hash_id);


--
-- Name: idx_events_start_time; Type: INDEX; Schema: public; Owner: belgrade_user
--

CREATE INDEX idx_events_start_time ON public.events USING btree (start_time DESC);


--
-- PostgreSQL database dump complete
--

\unrestrict mfJYyAmAZLDBQw32walDhdOcqCxUhyXtfWBa1UpSjsE56dWQkW8X8O8rSOfflLP

