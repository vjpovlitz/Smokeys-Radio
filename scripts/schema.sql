-- Smokey's Radio - SQL Server schema (canonical)
-- Idempotent for fresh installs. For migrations from a previous schema,
-- see scripts/migrate_to_v2.sql.

IF DB_ID('SmokeysRadio') IS NULL
    CREATE DATABASE SmokeysRadio;
GO

USE SmokeysRadio;
GO

-- ---------- users ----------
IF OBJECT_ID('dbo.users', 'U') IS NULL
CREATE TABLE dbo.users (
    discord_user_id BIGINT        NOT NULL PRIMARY KEY,
    username        NVARCHAR(100) NOT NULL,
    display_name    NVARCHAR(100) NULL,
    first_seen      DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    last_seen       DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- ---------- guilds ----------
IF OBJECT_ID('dbo.guilds', 'U') IS NULL
CREATE TABLE dbo.guilds (
    guild_id    BIGINT        NOT NULL PRIMARY KEY,
    name        NVARCHAR(200) NULL,
    first_seen  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- ---------- songs ----------
IF OBJECT_ID('dbo.songs', 'U') IS NULL
CREATE TABLE dbo.songs (
    song_id          INT           IDENTITY(1,1) PRIMARY KEY,
    youtube_id       NVARCHAR(32)  NOT NULL UNIQUE,
    title            NVARCHAR(500) NOT NULL,
    uploader         NVARCHAR(200) NULL,    -- yt-dlp 'uploader' (channel name)
    duration_seconds INT           NULL,
    thumbnail_url    NVARCHAR(500) NULL,
    first_played     DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- ---------- plays ----------
IF OBJECT_ID('dbo.plays', 'U') IS NULL
CREATE TABLE dbo.plays (
    play_id            BIGINT        IDENTITY(1,1) PRIMARY KEY,
    song_id            INT           NOT NULL,
    user_id            BIGINT        NOT NULL,
    guild_id           BIGINT        NOT NULL,
    played_at          DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    source             NVARCHAR(20)  NULL,   -- 'url' or 'search'
    extraction_method  NVARCHAR(20)  NULL,   -- which bypass method succeeded
    search_query       NVARCHAR(500) NULL,   -- raw text the user typed (NULL for direct URLs)
    outcome            NVARCHAR(20)  NOT NULL DEFAULT 'started',  -- 'started' | 'completed' | 'skipped' | 'error'
    listened_seconds   INT           NULL,                         -- updated when playback ends
    CONSTRAINT FK_plays_song  FOREIGN KEY (song_id)  REFERENCES dbo.songs(song_id),
    CONSTRAINT FK_plays_user  FOREIGN KEY (user_id)  REFERENCES dbo.users(discord_user_id),
    CONSTRAINT FK_plays_guild FOREIGN KEY (guild_id) REFERENCES dbo.guilds(guild_id)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_plays_played_at' AND object_id = OBJECT_ID('dbo.plays'))
    CREATE INDEX IX_plays_played_at ON dbo.plays(played_at DESC);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_plays_song' AND object_id = OBJECT_ID('dbo.plays'))
    CREATE INDEX IX_plays_song ON dbo.plays(song_id);
GO
-- Composite indexes covering the actual query shapes
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_plays_user_played_at' AND object_id = OBJECT_ID('dbo.plays'))
    CREATE INDEX IX_plays_user_played_at ON dbo.plays(user_id, played_at DESC);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_plays_guild_played_at' AND object_id = OBJECT_ID('dbo.plays'))
    CREATE INDEX IX_plays_guild_played_at ON dbo.plays(guild_id, played_at DESC);
GO

-- ---------- commands ----------
IF OBJECT_ID('dbo.commands', 'U') IS NULL
CREATE TABLE dbo.commands (
    command_id    BIGINT         IDENTITY(1,1) PRIMARY KEY,
    command_name  NVARCHAR(50)   NOT NULL,
    user_id       BIGINT         NOT NULL,
    guild_id      BIGINT         NULL,
    executed_at   DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME(),
    success       BIT            NOT NULL DEFAULT 1,
    args          NVARCHAR(500)  NULL,
    error_message NVARCHAR(1000) NULL
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_commands_executed_at' AND object_id = OBJECT_ID('dbo.commands'))
    CREATE INDEX IX_commands_executed_at ON dbo.commands(executed_at DESC);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_commands_name' AND object_id = OBJECT_ID('dbo.commands'))
    CREATE INDEX IX_commands_name ON dbo.commands(command_name);
GO
