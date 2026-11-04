SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `files` (
  `id` int NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `file_path` varchar(1024) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `mime_type` varchar(128) DEFAULT NULL,
  `size_bytes` bigint DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `uploaded` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_modified` datetime DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `pages` json DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_file_path` (`file_path`(255)),
  KEY `idx_uploaded` (`uploaded`),
  KEY `idx_visibility` (`visibility`),
  KEY `last_modified` (`last_modified`),
  KEY `cache_built_at` (`cache_built_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
