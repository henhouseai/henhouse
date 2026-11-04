SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `pages` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `link` varchar(255) DEFAULT NULL,
  `text` text,
  `metadata` json DEFAULT NULL,
  `parent` int DEFAULT NULL,
  `class` varchar(255) DEFAULT NULL,
  `last_modified` datetime DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `displayStyle` int NOT NULL DEFAULT '1',
  `viewCount` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `name` (`name`),
  KEY `link` (`link`),
  KEY `parent` (`parent`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `links` (
  `id` int NOT NULL,
  `link` varchar(255) NOT NULL,
  `resolution_id` int NOT NULL,
  KEY `id` (`id`),
  KEY `link` (`link`),
  KEY `resolution_id` (`resolution_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
