SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `pages` (
  `id` int NOT NULL,
  `display_name` varchar(255) DEFAULT NULL,
  `prepared_text` longtext,
  `children_summary` json DEFAULT NULL,
  `image_summary` json DEFAULT NULL,
  `file_summary` json DEFAULT NULL,
  `links_out` json DEFAULT NULL,
  `metadata` json DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `images` (
  `id` int NOT NULL,
  `instances` json DEFAULT NULL,
  `pages` json DEFAULT NULL,
  `metadata` json DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `files` (
  `id` int NOT NULL,
  `pages` json DEFAULT NULL,
  `metadata` json DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

