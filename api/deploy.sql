-- DROP TABLE IF EXISTS Friends CASCADE;
-- DROP TABLE IF EXISTS Locations CASCADE;
-- DROP TABLE IF EXISTS Users CASCADE;
-- DROP TABLE IF EXISTS FriendRequests CASCADE;
-- DROP TABLE IF EXISTS LocationHistory CASCADE;

SET TIME ZONE 'UTC';

CREATE TABLE IF NOT EXISTS Users(
    username varchar(360) PRIMARY KEY NOT NULL,
    avatar varchar(400),
    currentSongName varchar(360),
    currentSongGenre varchar(360),
    currentSongArtist varchar(360),
    currentSongId varchar(120),
    currentLat decimal,  --lat/long used to identify
    currentLong decimal
);

--locations to store top data for last 24hr
CREATE TABLE IF NOT EXISTS Locations(
    city varchar(360) UNIQUE PRIMARY KEY, --name of city location
    topSongName varchar(360), --song info
    topSongGenre varchar(360), --song info
    topSongId varchar(120), --song info
    topSongArtist varchar(360), --song info for top at location
    topGenre varchar(360) --current top genre at the location
);

CREATE TABLE IF NOT EXISTS Friends(
    curUser VARCHAR(360) REFERENCES Users(username),
    friend VARCHAR(360) REFERENCES Users(username),
    UNIQUE (curUser, friend)
);

CREATE TABLE IF NOT EXISTS FriendRequests(
    sender VARCHAR(360) REFERENCES Users(username),
    receiver VARCHAR(360) REFERENCES Users(username)
);

CREATE TABLE IF NOT EXISTS LocationHistory(
    username VARCHAR(360) REFERENCES Users(username),
    city VARCHAR(360) REFERENCES Locations(city),
    playTimeStamp timestamp with time zone,
    songName varchar(360), --song info
    songGenre varchar(360), --song info
    songId varchar(120), --song info
    songArtist varchar(360) --song info for top at location
);

CREATE TABLE IF NOT EXISTS LocationFollow(
    username VARCHAR(360) REFERENCES Users(username),
    city VARCHAR(360) REFERENCES Locations(city)
);