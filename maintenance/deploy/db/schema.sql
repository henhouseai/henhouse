-- Maintenance module schema (main database)
-- Job queue used by maintenance/job_queue.py, the maintenance worker, and media transcode jobs.
-- Loaded by the core init_db_35_module_schemas hook.

CREATE TABLE IF NOT EXISTS `maintenance_jobs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `job_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('pending','running','done','error') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `payload_json` json NOT NULL,
  `progress_json` json DEFAULT NULL,
  `priority` int NOT NULL DEFAULT 0,
  `attempts` int NOT NULL DEFAULT 0,
  `error_message` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `started_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_status_priority` (`status`,`priority`,`created_at`),
  KEY `idx_job_type` (`job_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
