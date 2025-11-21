SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `pages` (
  `id` int NOT NULL,
  `parent_id` int DEFAULT NULL,
  `class` varchar(255) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `link` varchar(255) DEFAULT NULL,
  `text` longtext,
  `metadata` json DEFAULT NULL,
  `prepared_text` longtext,
  `children_summary` json DEFAULT NULL,
  `image_summary` json DEFAULT NULL,
  `file_summary` json DEFAULT NULL,
  `links_out` json DEFAULT NULL,
  `source_last_modified` datetime DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  `cache_version` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `images` (
  `id` int NOT NULL,
  `caption` varchar(255) DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `uploaded` datetime DEFAULT NULL,
  `last_modified` datetime DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `viewCount` int NOT NULL DEFAULT '0',
  `instances` json DEFAULT NULL,
  `pages` json DEFAULT NULL,
  `source_last_modified` datetime DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  `cache_version` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `files` (
  `id` int NOT NULL,
  `file_name` varchar(255) DEFAULT NULL,
  `file_path` varchar(1024) DEFAULT NULL,
  `mime_type` varchar(128) DEFAULT NULL,
  `size_bytes` bigint DEFAULT NULL,
  `username` varchar(255) DEFAULT NULL,
  `uploaded` datetime DEFAULT NULL,
  `last_modified` datetime DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `pages` json DEFAULT NULL,
  `source_last_modified` datetime DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  `cache_version` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

