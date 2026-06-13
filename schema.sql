-- =============================================================================
-- Rank Tracker — Schema MySQL completo
-- Charset: utf8mb4 / Collation: utf8mb4_unicode_ci
-- =============================================================================

CREATE DATABASE IF NOT EXISTS ranktracker
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ranktracker;

-- -----------------------------------------------------------------------------
-- 1. projects
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id          INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    name        VARCHAR(255)     NOT NULL,
    domain      VARCHAR(255)     NOT NULL,
    country     VARCHAR(10)      NOT NULL DEFAULT 'ES',
    language    VARCHAR(10)      NOT NULL DEFAULT 'es',
    device      ENUM('desktop','mobile','tablet') NOT NULL DEFAULT 'desktop',
    gsc_site_url VARCHAR(500)    NULL,
    is_active   TINYINT(1)       NOT NULL DEFAULT 1,
    created_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_domain (domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 2. keywords
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS keywords (
    id          INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    keyword     VARCHAR(500)     NOT NULL,
    language    VARCHAR(10)      NOT NULL DEFAULT 'es',
    country     VARCHAR(10)      NOT NULL DEFAULT 'ES',
    PRIMARY KEY (id),
    UNIQUE KEY uq_keyword_lang_country (keyword(191), language, country)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 3. project_keywords
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_keywords (
    id               INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    project_id       INT UNSIGNED  NOT NULL,
    keyword_id       INT UNSIGNED  NOT NULL,
    target_position  TINYINT UNSIGNED NULL,
    tag              VARCHAR(100)  NULL,
    is_active        TINYINT(1)    NOT NULL DEFAULT 1,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_project_keyword (project_id, keyword_id),
    KEY fk_pk_keyword (keyword_id),
    CONSTRAINT fk_pk_project  FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT fk_pk_keyword  FOREIGN KEY (keyword_id) REFERENCES keywords (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 4. rankings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rankings (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    project_keyword_id  INT UNSIGNED    NOT NULL,
    check_date          DATE            NOT NULL,
    position            SMALLINT UNSIGNED NULL,
    url                 TEXT            NULL,
    impressions         INT UNSIGNED    NULL,
    clicks              INT UNSIGNED    NULL,
    click_through_rate  DECIMAL(7,4)    NULL,
    avg_position_gsc    DECIMAL(6,2)    NULL,
    source              ENUM('gsc','dataforseo') NOT NULL DEFAULT 'dataforseo',
    raw_payload         JSON            NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ranking_date_source (project_keyword_id, check_date, source),
    KEY idx_ranking_pk_date (project_keyword_id, check_date),
    CONSTRAINT fk_ranking_pk FOREIGN KEY (project_keyword_id)
        REFERENCES project_keywords (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 5. competitors
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS competitors (
    id          INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    project_id  INT UNSIGNED  NOT NULL,
    domain      VARCHAR(255)  NOT NULL,
    name        VARCHAR(255)  NULL,
    is_active   TINYINT(1)    NOT NULL DEFAULT 1,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_project_competitor (project_id, domain),
    CONSTRAINT fk_comp_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 6. competitor_rankings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS competitor_rankings (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    project_keyword_id  INT UNSIGNED    NOT NULL,
    competitor_id       INT UNSIGNED    NOT NULL,
    check_date          DATE            NOT NULL,
    position            SMALLINT UNSIGNED NULL,
    url                 TEXT            NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_competitor_ranking_date (project_keyword_id, competitor_id, check_date),
    KEY fk_cr_competitor (competitor_id),
    CONSTRAINT fk_cr_pk         FOREIGN KEY (project_keyword_id)
        REFERENCES project_keywords (id) ON DELETE CASCADE,
    CONSTRAINT fk_cr_competitor FOREIGN KEY (competitor_id)
        REFERENCES competitors (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 7. alerts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id                  INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    project_keyword_id  INT UNSIGNED  NOT NULL,
    alert_type          ENUM(
                          'position_drop','position_gain',
                          'entered_top10','left_top10',
                          'entered_top3','not_found'
                        ) NOT NULL,
    threshold_positions TINYINT UNSIGNED NULL,
    channel             ENUM('email','webhook','slack') NOT NULL DEFAULT 'email',
    channel_config      JSON          NOT NULL DEFAULT ('{}'),
    is_active           TINYINT(1)    NOT NULL DEFAULT 1,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY fk_alert_pk (project_keyword_id),
    CONSTRAINT fk_alert_pk FOREIGN KEY (project_keyword_id)
        REFERENCES project_keywords (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 8. alert_events
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alert_events (
    id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    alert_id           INT UNSIGNED    NOT NULL,
    triggered_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    previous_position  SMALLINT UNSIGNED NULL,
    current_position   SMALLINT UNSIGNED NULL,
    message            TEXT            NULL,
    sent               TINYINT(1)      NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_alert_event_alert_date (alert_id, triggered_at),
    CONSTRAINT fk_ae_alert FOREIGN KEY (alert_id) REFERENCES alerts (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- Vistas
-- =============================================================================

-- Vista 1: ranking actual por keyword (última fecha disponible, cualquier fuente)
CREATE OR REPLACE VIEW v_current_rankings AS
SELECT
    pk.id            AS project_keyword_id,
    pk.project_id,
    pk.keyword_id,
    k.keyword,
    pk.tag,
    pk.target_position,
    r.position       AS current_position,
    r.url            AS best_url,
    r.impressions,
    r.clicks,
    r.click_through_rate AS ctr,
    r.avg_position_gsc,
    r.source,
    r.check_date
FROM project_keywords pk
JOIN keywords k ON k.id = pk.keyword_id
JOIN rankings r ON r.project_keyword_id = pk.id
JOIN (
    SELECT project_keyword_id, MAX(check_date) AS max_date
    FROM rankings
    GROUP BY project_keyword_id
) latest ON latest.project_keyword_id = r.project_keyword_id
         AND latest.max_date = r.check_date
WHERE pk.is_active = 1;


-- Vista 2: resumen por proyecto (KPIs del dashboard)
CREATE OR REPLACE VIEW v_project_summary AS
SELECT
    p.id                                                   AS project_id,
    p.name                                                 AS project_name,
    p.domain,
    COUNT(pk.id)                                           AS total_keywords,
    SUM(cr.current_position <= 3)                          AS keywords_top3,
    SUM(cr.current_position <= 10)                         AS keywords_top10,
    SUM(cr.current_position <= 100)                        AS keywords_top100,
    SUM(cr.current_position IS NULL)                       AS keywords_not_found,
    ROUND(AVG(cr.current_position), 1)                     AS avg_position,
    MAX(cr.check_date)                                     AS last_check
FROM projects p
JOIN project_keywords pk  ON pk.project_id = p.id AND pk.is_active = 1
LEFT JOIN v_current_rankings cr ON cr.project_keyword_id = pk.id
WHERE p.is_active = 1
GROUP BY p.id, p.name, p.domain;
