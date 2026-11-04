SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `files` (
  `id` int NOT NULL AUTO_INCREMENT,
  `file_name` varchar(255) NOT NULL,
  `file_path` varchar(1024) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `mime_type` varchar(128) DEFAULT NULL,
  `size_bytes` bigint DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `uploaded` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_modified` datetime DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_file_path` (`file_path`(255)),
  KEY `idx_uploaded` (`uploaded`),
  KEY `idx_visibility` (`visibility`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `file_groups` (
  `page_id` int NOT NULL,
  `file_id` int NOT NULL,
  `file_rank` int NOT NULL,
  PRIMARY KEY (`page_id`, `file_id`, `file_rank`),
  KEY `idx_file` (`file_id`),
  KEY `idx_page_rank` (`page_id`, `file_rank`),
  CONSTRAINT `fk_file_groups_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_file_groups_file` FOREIGN KEY (`file_id`) REFERENCES `files` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
