SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `images` (
  `id` int NOT NULL AUTO_INCREMENT,
  `caption` varchar(255) DEFAULT NULL,
  `username` varchar(255) NOT NULL,
  `uploaded` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_modified` datetime DEFAULT NULL,
  `cache_built_at` datetime DEFAULT NULL,
  `comments` varchar(255) DEFAULT NULL,
  `visibility` int NOT NULL DEFAULT '1',
  `viewCount` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `username` (`username`),
  KEY `uploaded` (`uploaded`),
  KEY `visibility` (`visibility`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `image_groups` (
  `page_id` int NOT NULL,
  `image_id` int NOT NULL,
  `image_rank` int NOT NULL,
  PRIMARY KEY (`page_id`, `image_id`, `image_rank`),
  KEY `idx_page_rank` (`page_id`, `image_rank`),
  KEY `idx_image` (`image_id`),
  CONSTRAINT `fk_image_groups_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_image_groups_image` FOREIGN KEY (`image_id`) REFERENCES `images` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `image_instances` (
  `image_id` int NOT NULL,
  `width` int NOT NULL,
  `height` int NOT NULL,
  `src` varchar(255) NOT NULL,
  `filesize` int NOT NULL,
  KEY `idx_image_id` (`image_id`),
  CONSTRAINT `fk_image_instances_image` FOREIGN KEY (`image_id`) REFERENCES `images` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `image_links` (
  `id` int NOT NULL,
  `resolution_id` int NOT NULL,
  KEY `id` (`id`),
  KEY `resolution_id` (`resolution_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
