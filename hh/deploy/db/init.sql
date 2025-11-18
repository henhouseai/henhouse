SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `agent_bootstrap_versions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `bootstrap_file_id` bigint NOT NULL,
  `read_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  `work_docket_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_agent` (`agent_id`),
  KEY `idx_bootstrap_file` (`bootstrap_file_id`),
  KEY `idx_work_docket` (`work_docket_id`),
  CONSTRAINT `agent_bootstrap_versions_ibfk_1` FOREIGN KEY (`bootstrap_file_id`) REFERENCES `bootstrap_files` (`id`),
  CONSTRAINT `agent_bootstrap_versions_ibfk_2` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agent_cycles` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `cycle_type` enum('udack','autonomous') COLLATE utf8mb4_unicode_ci NOT NULL,
  `triggered_by` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_ts` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `idx_agent` (`agent_id`),
  KEY `idx_cycle_type` (`cycle_type`),
  CONSTRAINT `agent_cycles_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agent_onboarding_responses` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `question` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `response` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_ts` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  `badge_ts` time(6) DEFAULT NULL,
  `path` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `filename` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_agent` (`agent_id`),
  KEY `idx_badge_ts` (`badge_ts`),
  KEY `idx_path` (`path`),
  CONSTRAINT `agent_onboarding_responses_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agent_profiles` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `display_name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `country` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lineage_key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `generation` int NOT NULL DEFAULT '1',
  `persona_json` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `work_docket_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `agent_id` (`agent_id`),
  KEY `lineage_key` (`lineage_key`),
  KEY `country` (`country`),
  KEY `idx_work_docket` (`work_docket_id`),
  CONSTRAINT `agent_profiles_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agent_runs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `session_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prompt` text COLLATE utf8mb4_unicode_ci,
  `model` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `log_path` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `last_heartbeat_ts` datetime(6) DEFAULT NULL,
  `status` enum('starting','running','idle','hung','done','terminated') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'starting',
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_agent_id` (`agent_id`),
  KEY `idx_session_id` (`session_id`),
  CONSTRAINT `fk_runs_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agent_runtime_state` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `mode` enum('operator','team','agent','discipline','question') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'team',
  `latch` enum('none','team','question','ud') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'team',
  `fail_count` int NOT NULL DEFAULT '0',
  `last_cycle_ts` datetime(6) DEFAULT NULL,
  `last_validation_json` longtext COLLATE utf8mb4_unicode_ci,
  `updated_by_agent_id` bigint DEFAULT NULL,
  `updated_reason` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `agent_id` (`agent_id`),
  KEY `updated_by_agent_id` (`updated_by_agent_id`),
  CONSTRAINT `agent_runtime_state_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `agent_runtime_state_ibfk_2` FOREIGN KEY (`updated_by_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agent_spawn_requests` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `requested_by_agent_id` bigint DEFAULT NULL,
  `role` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prompt` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'auto',
  `assignment` json DEFAULT NULL,
  `status` enum('pending','claimed','running','done','failed') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `claimed_by` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_created` (`created_ts`),
  KEY `fk_spawnreq_agent` (`requested_by_agent_id`),
  CONSTRAINT `fk_spawnreq_agent` FOREIGN KEY (`requested_by_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agents` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_key` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `badge_ts` time(6) NOT NULL,
  `status` enum('active','inactive') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `terminated` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `gate_status` enum('none','waiting_ack') COLLATE utf8mb4_unicode_ci DEFAULT 'none',
  `gate_started_ts` datetime(6) DEFAULT NULL,
  `session_id` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ask_sidecar_link` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `sidecar_file_id` bigint NOT NULL,
  `ask_id` bigint NOT NULL,
  `link_kind` enum('primary','context','audit') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'context',
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ask_sidecar` (`sidecar_file_id`),
  UNIQUE KEY `uq_ask_link` (`sidecar_file_id`,`ask_id`),
  KEY `ask_id` (`ask_id`),
  CONSTRAINT `ask_sidecar_link_ibfk_2` FOREIGN KEY (`sidecar_file_id`) REFERENCES `sidecar_files` (`id`) ON DELETE CASCADE,
  CONSTRAINT `ask_sidecar_link_ibfk_3` FOREIGN KEY (`ask_id`) REFERENCES `asks` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ask_link_target` FOREIGN KEY (`ask_id`) REFERENCES `asks` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `asks` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `page_id` int DEFAULT NULL,
  `work_docket_id` bigint NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('todo','doing','review','done') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'todo',
  `meta` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `sort_order` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `work_docket_id` (`work_docket_id`,`status`),
  KEY `idx_asks_wd` (`work_docket_id`),
  KEY `idx_asks_order` (`work_docket_id`,`sort_order`),
  KEY `idx_page_id` (`page_id`),
  CONSTRAINT `asks_ibfk_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bootstrap_files` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `release_id` bigint NOT NULL,
  `path` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sha256` char(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `size_bytes` bigint NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `release_id` (`release_id`),
  KEY `path` (`path`),
  CONSTRAINT `bootstrap_files_ibfk_1` FOREIGN KEY (`release_id`) REFERENCES `bootstrap_releases` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `bootstrap_releases` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `release_ts` datetime(6) NOT NULL,
  `source_repo` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `comment` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_by_agent_id` bigint DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `created_by_agent_id` (`created_by_agent_id`),
  KEY `release_ts` (`release_ts`),
  CONSTRAINT `bootstrap_releases_ibfk_1` FOREIGN KEY (`created_by_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chunk_embeddings` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `chunk_id` bigint NOT NULL,
  `model` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dim` int NOT NULL,
  `vector_blob` longblob NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chunk_model` (`chunk_id`,`model`),
  KEY `idx_model` (`model`),
  CONSTRAINT `chunk_embeddings_ibfk_1` FOREIGN KEY (`chunk_id`) REFERENCES `context_chunks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chunk_entity_links` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `chunk_id` bigint NOT NULL,
  `entity_id` bigint NOT NULL,
  `link_type` enum('primary','context','reference','audit') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'context',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chunk_entity` (`chunk_id`,`entity_id`),
  KEY `entity_id` (`entity_id`),
  CONSTRAINT `chunk_entity_links_ibfk_1` FOREIGN KEY (`chunk_id`) REFERENCES `context_chunks` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chunk_entity_links_ibfk_2` FOREIGN KEY (`entity_id`) REFERENCES `entity_refs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chunk_keywords` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `chunk_id` bigint NOT NULL,
  `keyword_id` bigint NOT NULL,
  `relevance` float NOT NULL,
  `assigned_method` enum('auto','manual') COLLATE utf8mb4_unicode_ci NOT NULL,
  `assigned_by_agent_id` bigint DEFAULT NULL,
  `validated` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chunk_keyword` (`chunk_id`,`keyword_id`),
  KEY `assigned_by_agent_id` (`assigned_by_agent_id`),
  KEY `idx_keyword` (`keyword_id`,`relevance`),
  KEY `idx_chunk` (`chunk_id`),
  CONSTRAINT `chunk_keywords_ibfk_1` FOREIGN KEY (`chunk_id`) REFERENCES `context_chunks` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chunk_keywords_ibfk_2` FOREIGN KEY (`keyword_id`) REFERENCES `keywords` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chunk_keywords_ibfk_3` FOREIGN KEY (`assigned_by_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `coffee_pot_training` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `work_docket_id` bigint DEFAULT NULL,
  `agent_id` bigint DEFAULT NULL,
  `training_completed` tinyint(1) DEFAULT '0',
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `idx_work_docket` (`work_docket_id`),
  KEY `idx_agent` (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `context_chunks` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `document_id` bigint NOT NULL,
  `chunk_order` int NOT NULL,
  `chunk_uid` char(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_hash` char(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `context_text` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `chunk_summary` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL,
  `word_count` int NOT NULL,
  `token_count` int DEFAULT NULL,
  `overlap_before` int NOT NULL DEFAULT '0',
  `overlap_after` int NOT NULL DEFAULT '0',
  `start_line` int DEFAULT NULL,
  `end_line` int DEFAULT NULL,
  `start_char` int DEFAULT NULL,
  `end_char` int DEFAULT NULL,
  `heading` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `section_path` varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `content_type` enum('pattern','example','reference','appendix','concept','implementation') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `complexity_level` enum('basic','intermediate','advanced') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `has_code_example` tinyint(1) NOT NULL DEFAULT '0',
  `has_math` tinyint(1) NOT NULL DEFAULT '0',
  `has_table` tinyint(1) NOT NULL DEFAULT '0',
  `code_languages` json DEFAULT NULL,
  `readability_score` float DEFAULT NULL,
  `completeness_score` float DEFAULT NULL,
  `validation_status` enum('pending','validated','flagged','rejected') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `chunk_created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_doc_order` (`document_id`,`chunk_order`),
  UNIQUE KEY `uq_chunk_uid` (`chunk_uid`),
  KEY `idx_doc` (`document_id`),
  KEY `idx_chunk_created_ts` (`chunk_created_ts`),
  FULLTEXT KEY `ftx_context_text` (`context_text`),
  FULLTEXT KEY `ftx_chunk_summary` (`chunk_summary`),
  CONSTRAINT `context_chunks_ibfk_2` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `docket_sidecar_link` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `docket_id` bigint NOT NULL,
  `sidecar_file_id` bigint NOT NULL,
  `link_kind` enum('primary','context','audit') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'context',
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_docket_sidecar` (`docket_id`,`sidecar_file_id`),
  KEY `sidecar_file_id` (`sidecar_file_id`),
  CONSTRAINT `docket_sidecar_link_ibfk_1` FOREIGN KEY (`docket_id`) REFERENCES `work_dockets` (`id`) ON DELETE CASCADE,
  CONSTRAINT `docket_sidecar_link_ibfk_2` FOREIGN KEY (`sidecar_file_id`) REFERENCES `sidecar_files` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `documents` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file_path` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL,
  `slug` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_commit_sha` char(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `file_hash` char(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `file_path` (`file_path`),
  KEY `idx_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `entity_links` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `entity_id` bigint NOT NULL,
  `link_kind` enum('operator','watercooler','file','url') COLLATE utf8mb4_unicode_ci NOT NULL,
  `ref` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL,
  `start_offset` int DEFAULT NULL,
  `end_offset` int DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `entity_id` (`entity_id`,`link_kind`,`created_ts`),
  CONSTRAINT `entity_links_ibfk_1` FOREIGN KEY (`entity_id`) REFERENCES `entity_refs` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `entity_refs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `kind` enum('big_ask','ask','task','step') COLLATE utf8mb4_unicode_ci NOT NULL,
  `ref_key` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_entity` (`kind`,`ref_key`),
  KEY `kind` (`kind`,`created_ts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `entity_tags` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `entity_id` bigint NOT NULL,
  `tag_key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tag_value` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `entity_id` (`entity_id`,`tag_key`,`tag_value`),
  CONSTRAINT `entity_tags_ibfk_1` FOREIGN KEY (`entity_id`) REFERENCES `entity_refs` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `keyword_aliases` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `keyword_id` bigint NOT NULL,
  `alias` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `alias` (`alias`),
  KEY `idx_kw` (`keyword_id`),
  CONSTRAINT `keyword_aliases_ibfk_1` FOREIGN KEY (`keyword_id`) REFERENCES `keywords` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `keywords` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `keyword` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `status` enum('active','candidate','deprecated') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'candidate',
  `created_by_agent_id` bigint DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `keyword` (`keyword`),
  KEY `created_by_agent_id` (`created_by_agent_id`),
  CONSTRAINT `keywords_ibfk_1` FOREIGN KEY (`created_by_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sidecar_file_blobs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `sidecar_file_id` bigint NOT NULL,
  `version_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `char_count` int NOT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by_agent_id` bigint DEFAULT NULL,
  `is_latest` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `created_by_agent_id` (`created_by_agent_id`),
  KEY `sidecar_file_id` (`sidecar_file_id`,`version_ts`),
  KEY `is_latest` (`is_latest`),
  CONSTRAINT `sidecar_file_blobs_ibfk_1` FOREIGN KEY (`sidecar_file_id`) REFERENCES `sidecar_files` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `sidecar_file_blobs_ibfk_2` FOREIGN KEY (`created_by_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sidecar_files` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `path` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `path` (`path`),
  UNIQUE KEY `uk_sidecar_files_title` (`title`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `step_sidecar_link` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `sidecar_file_id` bigint NOT NULL,
  `step_id` bigint NOT NULL,
  `link_kind` enum('primary','context','audit') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'context',
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_step_sidecar` (`sidecar_file_id`),
  UNIQUE KEY `uq_step_link` (`sidecar_file_id`,`step_id`),
  KEY `step_id` (`step_id`),
  CONSTRAINT `fk_step_link_target` FOREIGN KEY (`step_id`) REFERENCES `steps` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `step_sidecar_link_ibfk_2` FOREIGN KEY (`sidecar_file_id`) REFERENCES `sidecar_files` (`id`) ON DELETE CASCADE,
  CONSTRAINT `step_sidecar_link_ibfk_3` FOREIGN KEY (`step_id`) REFERENCES `steps` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `steps` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `page_id` int DEFAULT NULL,
  `task_id` bigint DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `status` enum('todo','doing','review','done') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'todo',
  `meta` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sort_order` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `work_docket_id` (`status`),
  KEY `idx_steps_task` (`task_id`),
  KEY `idx_steps_order` (`task_id`,`sort_order`),
  KEY `idx_page_id` (`page_id`),
  CONSTRAINT `fk_steps_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`) ON DELETE CASCADE,
  CONSTRAINT `steps_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `steps_ibfk_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscription_agent` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `target_agent_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_subscription` (`agent_id`,`target_agent_id`),
  KEY `idx_agent_id` (`agent_id`),
  KEY `idx_target_agent_id` (`target_agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscription_ask` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `ask_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sub_ask` (`agent_id`,`ask_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscription_docket` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `docket_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_subscription` (`agent_id`,`docket_id`),
  KEY `idx_agent_id` (`agent_id`),
  KEY `idx_docket_id` (`docket_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscription_keyword` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `keyword_id` bigint NOT NULL,
  `last_seen_chunk_uid` char(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sub_kw` (`agent_id`,`keyword_id`),
  KEY `keyword_id` (`keyword_id`),
  CONSTRAINT `subscription_keyword_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `subscription_keyword_ibfk_2` FOREIGN KEY (`keyword_id`) REFERENCES `keywords` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscription_operator` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `operator_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_subscription` (`agent_id`,`operator_id`),
  KEY `idx_agent_id` (`agent_id`),
  KEY `idx_operator_id` (`operator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscription_sidecar` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `sidecar_file_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sub_sidecar` (`agent_id`,`sidecar_file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscription_step` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `step_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sub_step` (`agent_id`,`step_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscription_task` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `task_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sub_task` (`agent_id`,`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `task_sidecar_link` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `sidecar_file_id` bigint NOT NULL,
  `task_id` bigint NOT NULL,
  `link_kind` enum('primary','context','audit') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'context',
  `created_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_task_sidecar` (`sidecar_file_id`),
  UNIQUE KEY `uq_task_link` (`sidecar_file_id`,`task_id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `fk_task_link_target` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_sidecar_link_ibfk_2` FOREIGN KEY (`sidecar_file_id`) REFERENCES `sidecar_files` (`id`) ON DELETE CASCADE,
  CONSTRAINT `task_sidecar_link_ibfk_3` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tasks` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `page_id` int DEFAULT NULL,
  `ask_id` bigint DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('todo','doing','review','done') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'todo',
  `meta` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `sort_order` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `work_docket_id` (`status`),
  KEY `idx_tasks_ask` (`ask_id`),
  KEY `idx_tasks_order` (`ask_id`,`sort_order`),
  KEY `idx_page_id` (`page_id`),
  CONSTRAINT `fk_tasks_ask` FOREIGN KEY (`ask_id`) REFERENCES `asks` (`id`) ON DELETE CASCADE,
  CONSTRAINT `tasks_ibfk_1` FOREIGN KEY (`ask_id`) REFERENCES `asks` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `tasks_ibfk_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_messages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `occurred_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `from_agent_id` bigint DEFAULT NULL,
  `to_agent_id` bigint DEFAULT NULL,
  `kind` enum('operator','microlog','message','pointer') COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `meta` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `from_agent_id` (`from_agent_id`),
  KEY `occurred_ts` (`occurred_ts`),
  KEY `from_role` (`occurred_ts`),
  KEY `to_role` (`occurred_ts`),
  KEY `idx_dm_to_agent` (`to_agent_id`,`id`),
  KEY `idx_kind_id` (`kind`,`id`),
  KEY `idx_work_docket_id_id` (`id`),
  CONSTRAINT `watercooler_messages_ibfk_1` FOREIGN KEY (`from_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `watercooler_messages_ibfk_2` FOREIGN KEY (`to_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_agent` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_agent_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_agent_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_ask` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_ask_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_ask_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_dm` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_dm_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_dm_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_docket` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_docket_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_docket_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_keyword` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_keyword_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_keyword_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_operator` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_operator_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_operator_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_sidecar` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_sidecar_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_sidecar_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_step` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_step_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_step_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `watercooler_queue_task` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `agent_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  `queued_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_agent_message` (`agent_id`,`message_id`),
  KEY `idx_agent_queued` (`agent_id`,`queued_ts`),
  KEY `idx_message` (`message_id`),
  KEY `idx_queued_ts` (`queued_ts`),
  CONSTRAINT `watercooler_queue_task_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
  CONSTRAINT `watercooler_queue_task_ibfk_2` FOREIGN KEY (`message_id`) REFERENCES `watercooler_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wc_microlog_link_agent` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watercooler_message_id` bigint NOT NULL,
  `agent_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `watercooler_message_id` (`watercooler_message_id`),
  KEY `work_docket_id` (`agent_id`),
  CONSTRAINT `wc_microlog_link_agent_ibfk_1` FOREIGN KEY (`watercooler_message_id`) REFERENCES `watercooler_messages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wc_microlog_link_agent_ibfk_2` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wc_microlog_link_ask` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watercooler_message_id` bigint NOT NULL,
  `ask_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `watercooler_message_id` (`watercooler_message_id`),
  KEY `work_docket_id` (`ask_id`),
  CONSTRAINT `wc_microlog_link_ask_ibfk_1` FOREIGN KEY (`watercooler_message_id`) REFERENCES `watercooler_messages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wc_microlog_link_ask_ibfk_2` FOREIGN KEY (`ask_id`) REFERENCES `asks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wc_microlog_link_docket` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watercooler_message_id` bigint NOT NULL,
  `docket_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `watercooler_message_id` (`watercooler_message_id`),
  KEY `docket_id` (`docket_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wc_microlog_link_keyword` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watercooler_message_id` bigint NOT NULL,
  `keyword_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_watercooler_message_id` (`watercooler_message_id`),
  KEY `idx_keyword_id` (`keyword_id`),
  CONSTRAINT `wc_microlog_link_keyword_ibfk_2` FOREIGN KEY (`watercooler_message_id`) REFERENCES `watercooler_messages` (`id`),
  CONSTRAINT `wc_microlog_link_keyword_ibfk_3` FOREIGN KEY (`keyword_id`) REFERENCES `keywords` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wc_microlog_link_operator` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watercooler_message_id` bigint NOT NULL,
  `operator_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_watercooler_message_id` (`watercooler_message_id`),
  KEY `idx_operator_id` (`operator_id`),
  CONSTRAINT `wc_microlog_link_operator_ibfk_2` FOREIGN KEY (`watercooler_message_id`) REFERENCES `watercooler_messages` (`id`),
  CONSTRAINT `wc_microlog_link_operator_ibfk_3` FOREIGN KEY (`operator_id`) REFERENCES `agents` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wc_microlog_link_sidecar` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watercooler_message_id` bigint NOT NULL,
  `sidecar_file_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `work_docket_id` (`sidecar_file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wc_microlog_link_step` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watercooler_message_id` bigint NOT NULL,
  `step_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `watercooler_message_id` (`watercooler_message_id`),
  KEY `work_docket_id` (`step_id`),
  CONSTRAINT `wc_microlog_link_step_ibfk_1` FOREIGN KEY (`watercooler_message_id`) REFERENCES `watercooler_messages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wc_microlog_link_step_ibfk_2` FOREIGN KEY (`step_id`) REFERENCES `steps` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `wc_microlog_link_task` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watercooler_message_id` bigint NOT NULL,
  `task_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `watercooler_message_id` (`watercooler_message_id`),
  KEY `work_docket_id` (`task_id`),
  CONSTRAINT `wc_microlog_link_task_ibfk_1` FOREIGN KEY (`watercooler_message_id`) REFERENCES `watercooler_messages` (`id`) ON DELETE CASCADE,
  CONSTRAINT `wc_microlog_link_task_ibfk_2` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `work_dockets` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `page_id` int DEFAULT NULL,
  `started_ts` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `ended_ts` datetime(6) DEFAULT NULL,
  `active` tinyint(1) NOT NULL DEFAULT '0',
  `meta` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `status` enum('todo','doing','review','done') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'todo',
  `sort_order` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `active` (`active`,`started_ts`),
  KEY `idx_page_id` (`page_id`),
  CONSTRAINT `work_dockets_ibfk_page` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `pages` (
  `id` int NOT NULL AUTO_INCREMENT,
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
  PRIMARY KEY (`id`),
  KEY `name` (`name`),
  KEY `link` (`link`),
  KEY `parent` (`parent`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `source_code_files` (
  `page_id` int NOT NULL,
  `path` varchar(512) DEFAULT NULL,
  `language` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`page_id`),
  CONSTRAINT `source_code_files_ibfk_1` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `mcp_requests` (
  `page_id` int NOT NULL,
  `input_request` json NOT NULL,
  `output_response` json DEFAULT NULL,
  `create_request` int NOT NULL DEFAULT '0',
  `read_request` int NOT NULL DEFAULT '0',
  `update_request` int NOT NULL DEFAULT '0',
  `delete_request` int NOT NULL DEFAULT '0',
  `create_executed` int NOT NULL DEFAULT '0',
  `read_executed` int NOT NULL DEFAULT '0',
  `update_executed` int NOT NULL DEFAULT '0',
  `delete_executed` int NOT NULL DEFAULT '0',
  `status` enum('pending','approved','executing','completed','failed','cancelled','rolled_back') NOT NULL DEFAULT 'pending',
  PRIMARY KEY (`page_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `mcp_requests_ibfk_1` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `mcp_action_requests` (
  `page_id` int NOT NULL,
  `tool_name` varchar(255) NOT NULL,
  `arguments` json NOT NULL,
  `extraction_spec` json DEFAULT NULL,
  `status` enum('pending','approved','dependency_unmet','executing','executed','failed','rejected','cancelled') NOT NULL DEFAULT 'pending',
  `result` json DEFAULT NULL,
  `is_create` tinyint(1) NOT NULL DEFAULT '0',
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `is_update` tinyint(1) NOT NULL DEFAULT '0',
  `is_delete` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`page_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `mcp_action_requests_ibfk_1` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `images` (
  `id` int NOT NULL AUTO_INCREMENT,
  `caption` varchar(255) DEFAULT NULL,
  `username` varchar(255) NOT NULL,
  `uploaded` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
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

CREATE TABLE IF NOT EXISTS `links` (
  `id` int NOT NULL,
  `link` varchar(255) NOT NULL,
  `resolution_id` int NOT NULL,
  KEY `id` (`id`),
  KEY `link` (`link`),
  KEY `resolution_id` (`resolution_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `image_links` (
  `id` int NOT NULL,
  `resolution_id` int NOT NULL,
  KEY `id` (`id`),
  KEY `resolution_id` (`resolution_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `access_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ip_address` varchar(45) NOT NULL,
  `request_timestamp` datetime NOT NULL,
  `http_method` varchar(10) NOT NULL,
  `request_uri` varchar(2048) NOT NULL,
  `user_agent` varchar(512) DEFAULT NULL,
  `referrer` varchar(2048) DEFAULT NULL,
  `response_status` int NOT NULL,
  `http_auth_username` varchar(255) DEFAULT NULL,
  `post_id` varchar(16) DEFAULT NULL,
  `post_action` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
