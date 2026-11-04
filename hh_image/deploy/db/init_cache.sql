SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `images` (
  `id` int NOT NULL,
  `caption` varchar(255) DEFAULT NULL,
  `username` varchar(255) NOT NULL,
  `uploaded` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_modified` datetime DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `viewCount` int NOT NULL DEFAULT '0',
  `instances` json DEFAULT NULL,
  `pages` json DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `username` (`username`),
  KEY `uploaded` (`uploaded`),
  KEY `visibility` (`visibility`),
  KEY `last_modified` (`last_modified`),
  KEY `cache_built_at` (`cache_built_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
