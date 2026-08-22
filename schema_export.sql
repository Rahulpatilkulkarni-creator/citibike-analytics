--
-- PostgreSQL database dump
--

\restrict 0sgewMLuznnCOrhQsBoMbZw3GdncQznLHwZDum0y6s8iFeroWP71PSW3VMe50x9

-- Dumped from database version 17.11
-- Dumped by pg_dump version 17.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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
-- Name: rides; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rides (
    ride_id character varying(50) NOT NULL,
    rideable_type character varying(30),
    started_at timestamp without time zone NOT NULL,
    ended_at timestamp without time zone NOT NULL,
    start_station_id character varying(20),
    end_station_id character varying(20),
    member_casual character varying(10) NOT NULL,
    CONSTRAINT rides_member_casual_check CHECK (((member_casual)::text = ANY ((ARRAY['member'::character varying, 'casual'::character varying])::text[])))
);


ALTER TABLE public.rides OWNER TO postgres;

--
-- Name: stations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stations (
    station_id character varying(20) NOT NULL,
    station_name character varying(200) NOT NULL,
    latitude numeric(9,6),
    longitude numeric(9,6)
);


ALTER TABLE public.stations OWNER TO postgres;

--
-- Name: weather; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.weather (
    date date NOT NULL,
    temp_mean_c numeric(5,2),
    precipitation_mm numeric(6,2),
    windspeed_max_kmh numeric(5,2)
);


ALTER TABLE public.weather OWNER TO postgres;

--
-- Name: rides rides_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rides
    ADD CONSTRAINT rides_pkey PRIMARY KEY (ride_id);


--
-- Name: stations stations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations
    ADD CONSTRAINT stations_pkey PRIMARY KEY (station_id);


--
-- Name: weather weather_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.weather
    ADD CONSTRAINT weather_pkey PRIMARY KEY (date);


--
-- Name: idx_rides_member_casual; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rides_member_casual ON public.rides USING btree (member_casual);


--
-- Name: idx_rides_start_station; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rides_start_station ON public.rides USING btree (start_station_id);


--
-- Name: idx_rides_started_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rides_started_at ON public.rides USING btree (started_at);


--
-- Name: rides rides_end_station_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rides
    ADD CONSTRAINT rides_end_station_id_fkey FOREIGN KEY (end_station_id) REFERENCES public.stations(station_id);


--
-- Name: rides rides_start_station_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rides
    ADD CONSTRAINT rides_start_station_id_fkey FOREIGN KEY (start_station_id) REFERENCES public.stations(station_id);


--
-- PostgreSQL database dump complete
--

\unrestrict 0sgewMLuznnCOrhQsBoMbZw3GdncQznLHwZDum0y6s8iFeroWP71PSW3VMe50x9

