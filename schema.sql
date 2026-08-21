-- Dimension table: one row per station
CREATE TABLE stations (
    station_id      VARCHAR(20) PRIMARY KEY,
    station_name    VARCHAR(200) NOT NULL,
    latitude         DECIMAL(9,6),
    longitude        DECIMAL(9,6)
);

-- Fact table: one row per ride
CREATE TABLE rides (
    ride_id           VARCHAR(50) PRIMARY KEY,
    rideable_type     VARCHAR(30),
    started_at        TIMESTAMP NOT NULL,
    ended_at          TIMESTAMP NOT NULL,
    start_station_id  VARCHAR(20) REFERENCES stations(station_id),
    end_station_id    VARCHAR(20) REFERENCES stations(station_id),
    member_casual     VARCHAR(10) NOT NULL CHECK (member_casual IN ('member', 'casual'))
);

-- Indexes on columns we'll filter/group by constantly
CREATE INDEX idx_rides_started_at ON rides(started_at);
CREATE INDEX idx_rides_member_casual ON rides(member_casual);
CREATE INDEX idx_rides_start_station ON rides(start_station_id);