SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `video` (
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

CREATE TABLE IF NOT EXISTS `video_groups` (
  `page_id` int NOT NULL,
  `video_id` int NOT NULL,
  `video_rank` int NOT NULL,
  PRIMARY KEY (`page_id`, `video_id`, `video_rank`),
  KEY `idx_page_rank` (`page_id`, `video_rank`),
  KEY `idx_video` (`video_id`),
  CONSTRAINT `fk_video_groups_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_video_groups_video` FOREIGN KEY (`video_id`) REFERENCES `video` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `video_instances` (
  `video_id` int NOT NULL,
  `instance_type` varchar(32) NOT NULL,
  `file_path` varchar(1024) NOT NULL,
  `mime_type` varchar(128) NOT NULL,
  `size_bytes` bigint NOT NULL,
  `width` int DEFAULT NULL,
  `height` int DEFAULT NULL,
  `duration_seconds` decimal(10,2) DEFAULT NULL,
  `bitrate` int DEFAULT NULL,
  KEY `idx_video_id` (`video_id`),
  CONSTRAINT `fk_video_instances_video` FOREIGN KEY (`video_id`) REFERENCES `video` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
