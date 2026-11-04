SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `pages` (
  `id` int NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `link` varchar(255) DEFAULT NULL,
  `text` text,
  `parent` int DEFAULT NULL,
  `class` varchar(255) DEFAULT NULL,
  `last_modified` datetime DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `displayStyle` int NOT NULL DEFAULT '1',
  `viewCount` int NOT NULL DEFAULT '0',
  `display_name` varchar(255) DEFAULT NULL,
  `prepared_text` longtext,
  `children_summary` json DEFAULT NULL,
  `media_summary` json DEFAULT NULL,
  `links_out` json DEFAULT NULL,
  `metadata` json DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `name` (`name`),
  KEY `link` (`link`),
  KEY `parent` (`parent`),
  KEY `last_modified` (`last_modified`),
  KEY `cache_built_at` (`cache_built_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
