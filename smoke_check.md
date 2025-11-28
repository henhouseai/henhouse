
PS C:\Users\lee\Desktop\henhouse> hen dependency-list

  🏠 Henhouse:   Dependency List:

    ┌──────────────────────────┬────────────────┬──────────────────────────────┐
    │ 📦  Dependencies         │ 6 dependencies │ required by                  │
    ╞══════════════════════════╪════════════════╪══════════════════════════════╡
    │ ❌  Dependency Missing   │ grp            │ process_manager              │
    │ ❌  Dependency Missing   │ pillow         │ utils                        │
    │ ✅  Dependency Installed │ psutil         │ process_manager              │
    │ ❌  Dependency Missing   │ pwd            │ file_system, process_manager │
    │ ✅  Dependency Installed │ pygments       │ source_code_file_content     │
    │ ✅  Dependency Installed │ pymysql        │ connection                   │
    └──────────────────────────┴────────────────┴──────────────────────────────┘
PS C:\Users\lee\Desktop\henhouse> hen class-list     

  🏠 Henhouse:   Page Class Registry

    ┌──────────────────┬──────────────────┬───────────┬──────────────────────────────────────────┐
    │                  │ Class            │ Status    │ Module                                   │
    ╞══════════════════╪══════════════════╪═══════════╪══════════════════════════════════════════╡
    │ ✅  Loaded Class │ mcp_action       │ ✅ Loaded │ hh.mcp_action_request.mcp_action_request │
    │ ✅  Loaded Class │ mcp_request      │ ✅ Loaded │ hh.mcp_request.mcp_request               │
    │ ✅  Loaded Class │ page             │ ✅ Loaded │ hh.page.page                             │
    │ ✅  Loaded Class │ source_code_file │ ✅ Loaded │ hh.source_code_file.source_code_file     │
    │ ✅  Loaded Class │ work_docket      │ ✅ Loaded │ hh.work_docket.work_docket               │
    └──────────────────┴──────────────────┴───────────┴──────────────────────────────────────────┘

PS C:\Users\lee\Desktop\henhouse> hen backend-list

  🏠 Henhouse:   Backend List:

    ┌─────────────┬─────────────┬─────────────────────────────────┐
    │ 5 commands  │ name        │ module                          │
    ╞═════════════╪═════════════╪═════════════════════════════════╡
    │ 🔲  Found:  │ action      │ hh.gateway.registry.action      │
    │ 🔲  Found:  │ http        │ hh.gateway.registry.http        │
    │ 🔲  Found:  │ maintenance │ hh.gateway.registry.maintenance │
    │ 🔲  Found:  │ mcp         │ hh.gateway.registry.mcp         │
    │ ✅  Loaded: │ parser      │ hh.gateway.registry.parser      │
    └─────────────┴─────────────┴─────────────────────────────────┘

PS C:\Users\lee\Desktop\henhouse> hen action-list 

  🏠 Henhouse:   Action List:

    ┌─────────────┬──────────────────────────────┬─────────────────────────────────────────────────┐
    │ 88 commands │ name                         │ module                                          │
    ╞═════════════╪══════════════════════════════╪═════════════════════════════════════════════════╡
    │ ✅  Loaded: │ action_list                  │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ backend_list                 │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ command_list                 │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ http_list                    │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ maintenance_list             │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ mcp_list                     │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ parser_list                  │ hh.gateway.registry.utils                       │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ agent_list                   │ hh.agents.agent_list                            │
    │ 🔲  Found:  │ agent_purge                  │ hh.agents.agent_purge                           │
    │ 🔲  Found:  │ agent_tree                   │ hh.agents.agent_tree                            │
    │ 🔲  Found:  │ punch_in                     │ hh.agents.punch_in                              │
    │ 🔲  Found:  │ punch_out                    │ hh.agents.punch_out                             │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ gossip                       │ hh.agents.feed.gossip                           │
    │ 🔲  Found:  │ gulp                         │ hh.agents.feed.gulp                             │
    │ 🔲  Found:  │ peek                         │ hh.agents.feed.peek                             │
    │ 🔲  Found:  │ sip                          │ hh.agents.feed.sip                              │
    │ 🔲  Found:  │ subscription_runner          │ hh.agents.feed.subscription_runner              │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ answer                       │ hh.agents.onboarding.answer                     │
    │ 🔲  Found:  │ onboard                      │ hh.agents.onboarding.onboard                    │
    │ 🔲  Found:  │ promote                      │ hh.agents.onboarding.promote                    │
    │ 🔲  Found:  │ status                       │ hh.agents.onboarding.status                     │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ clear_cache                  │ hh.deploy.cache.clear_cache                     │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ add_db_users                 │ hh.deploy.db.add_db_users                       │
    │ 🔲  Found:  │ check_db                     │ hh.deploy.db.check_db                           │
    │ 🔲  Found:  │ clean_db                     │ hh.deploy.db.clean_db                           │
    │ 🔲  Found:  │ export_db                    │ hh.deploy.db.export_db                          │
    │ 🔲  Found:  │ import_db                    │ hh.deploy.db.import_db                          │
    │ 🔲  Found:  │ init_db                      │ hh.deploy.db.init_db                            │
    │ 🔲  Found:  │ init_homepage                │ hh.deploy.db.init_homepage                      │
    │ 🔲  Found:  │ remove_db_users              │ hh.deploy.db.remove_db_users                    │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ flask_start                  │ hh.deploy.flask.flask_start                     │
    │ 🔲  Found:  │ flask_status                 │ hh.deploy.flask.flask_status                    │
    │ 🔲  Found:  │ flask_stop                   │ hh.deploy.flask.flask_stop                      │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ pull_project                 │ hh.deploy.git.pull_project                      │
    │ 🔲  Found:  │ push_project                 │ hh.deploy.git.push_project                      │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ http_deploy                  │ hh.deploy.http.http_deploy                      │
    │ 🔲  Found:  │ http_deploy_ssl              │ hh.deploy.http.http_deploy_ssl                  │
    │ 🔲  Found:  │ http_remove                  │ hh.deploy.http.http_remove                      │
    │ 🔲  Found:  │ http_status                  │ hh.deploy.http.http_status                      │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ file_cache_refresh           │ hh.deploy.maint.file_cache_refresh              │
    │ 🔲  Found:  │ image_cache_refresh          │ hh.deploy.maint.image_cache_refresh             │
    │ 🔲  Found:  │ maintenance_jobs_status      │ hh.deploy.maint.maintenance_jobs_status         │
    │ 🔲  Found:  │ orphan_check                 │ hh.deploy.maint.orphan_checks                   │
    │ 🔲  Found:  │ page_cache_refresh           │ hh.deploy.maint.page_cache_refresh              │
    │ 🔲  Found:  │ regex_text                   │ hh.deploy.maint.regex_text                      │
    │ 🔲  Found:  │ update_maintenance_job       │ hh.deploy.maint.update_maintenance_job          │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ maintenance_start            │ hh.deploy.maintenance.maintenance_start         │
    │ 🔲  Found:  │ maintenance_status           │ hh.deploy.maintenance.maintenance_status        │
    │ 🔲  Found:  │ maintenance_stop             │ hh.deploy.maintenance.maintenance_stop          │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ deploy                       │ hh.deploy.srv.deploy                            │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ install                      │ hh.deploy.users.install                         │
    │ 🔲  Found:  │ install_cursor               │ hh.deploy.users.install_cursor                  │
    │ 🔲  Found:  │ uninstall                    │ hh.deploy.users.uninstall                       │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ upload_files                 │ hh.file.upload_file                             │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ dependency_list              │ hh.gateway.system.dependency_list               │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ help                         │ hh.help.help                                    │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_caption               │ hh.image.modify_caption                         │
    │ 🔲  Found:  │ show_image                   │ hh.image.show_image                             │
    │ 🔲  Found:  │ upload_images                │ hh.image.upload_image                           │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_mcp_action_request    │ hh.mcp_action_request.modify_mcp_action_request │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_mcp_request           │ hh.mcp_request.modify_mcp_request               │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ add_image                    │ hh.page.add_image                               │
    │ 🔲  Found:  │ add_images                   │ hh.page.add_images                              │
    │ 🔲  Found:  │ add_page                     │ hh.page.add_page                                │
    │ 🔲  Found:  │ class_list                   │ hh.page.class_list                              │
    │ 🔲  Found:  │ copy_image                   │ hh.page.copy_image                              │
    │ 🔲  Found:  │ copy_images                  │ hh.page.copy_images                             │
    │ 🔲  Found:  │ copy_page                    │ hh.page.copy_page                               │
    │ 🔲  Found:  │ count_pages                  │ hh.page.count_pages                             │
    │ 🔲  Found:  │ delete_page                  │ hh.page.delete_page                             │
    │ 🔲  Found:  │ get_add_page_class_info      │ hh.page.get_add_page_class_info                 │
    │ 🔲  Found:  │ get_page                     │ hh.page.get_page                                │
    │ 🔲  Found:  │ get_text                     │ hh.page.get_text                                │
    │ 🔲  Found:  │ modify_name                  │ hh.page.modify_name                             │
    │ 🔲  Found:  │ modify_text                  │ hh.page.modify_text                             │
    │ 🔲  Found:  │ move_image                   │ hh.page.move_image                              │
    │ 🔲  Found:  │ move_images                  │ hh.page.move_images                             │
    │ 🔲  Found:  │ move_page                    │ hh.page.move_page                               │
    │ 🔲  Found:  │ remove_image                 │ hh.page.remove_image                            │
    │ 🔲  Found:  │ set_image_rank               │ hh.page.set_image_rank                          │
    │ 🔲  Found:  │ show_page                    │ hh.page.show_page                               │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_file_path             │ hh.source_code_file.modify_file_path            │
    │ 🔲  Found:  │ modify_language              │ hh.source_code_file.modify_language             │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_work_meta_remove_pair │ hh.work.modify_work_meta_remove_pair            │
    │ 🔲  Found:  │ modify_work_meta_set_all     │ hh.work.modify_work_meta_set_all                │
    │ 🔲  Found:  │ modify_work_meta_set_pair    │ hh.work.modify_work_meta_set_pair               │
    │ 🔲  Found:  │ modify_work_sort_order       │ hh.work.modify_work_sort_order                  │
    │ 🔲  Found:  │ modify_work_status           │ hh.work.modify_work_status                      │
    └─────────────┴──────────────────────────────┴─────────────────────────────────────────────────┘

PS C:\Users\lee\Desktop\henhouse> hen command-list

  🏠 Henhouse:   Command List:

    ┌──────────────┬──────────────────────────────┬─────────────────────────────────────────────────┬───────────────────────┐
    │ 103 commands │ name                         │ module                                          │ action_args           │
    ╞══════════════╪══════════════════════════════╪═════════════════════════════════════════════════╪═══════════════════════╡
    │ ✅  Loaded:  │ action_list                  │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ backend_list                 │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ command_list                 │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ http_list                    │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ maintenance_list             │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ mcp_list                     │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ parser_list                  │ hh.gateway.registry.utils                       │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ agent_list                   │ hh.agents.agent_list                            │                       │
    │ 🔲  Found:   │ agent_purge                  │ hh.agents.agent_purge                           │                       │
    │ 🔲  Found:   │ agent_tree                   │ hh.agents.agent_tree                            │                       │
    │ 🔲  Found:   │ punch_in                     │ hh.agents.punch_in                              │                       │
    │ 🔲  Found:   │ punch_out                    │ hh.agents.punch_out                             │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ gossip                       │ hh.agents.feed.gossip                           │                       │
    │ 🔲  Found:   │ gulp                         │ hh.agents.feed.gulp                             │                       │
    │ 🔲  Found:   │ peek                         │ hh.agents.feed.peek                             │                       │
    │ 🔲  Found:   │ sip                          │ hh.agents.feed.sip                              │                       │
    │ 🔲  Found:   │ subscribe_agent              │ hh.agents.feed.subscription_runner              │ agent, subscribe      │
    │ 🔲  Found:   │ subscribe_ask                │ hh.agents.feed.subscription_runner              │ ask, subscribe        │
    │ 🔲  Found:   │ subscribe_docket             │ hh.agents.feed.subscription_runner              │ docket, subscribe     │
    │ 🔲  Found:   │ subscribe_keyword            │ hh.agents.feed.subscription_runner              │ keyword, subscribe    │
    │ 🔲  Found:   │ subscribe_operator           │ hh.agents.feed.subscription_runner              │ operator, subscribe   │
    │ 🔲  Found:   │ subscribe_sidecar            │ hh.agents.feed.subscription_runner              │ sidecar, subscribe    │
    │ 🔲  Found:   │ subscribe_step               │ hh.agents.feed.subscription_runner              │ step, subscribe       │
    │ 🔲  Found:   │ subscribe_task               │ hh.agents.feed.subscription_runner              │ task, subscribe       │
    │ 🔲  Found:   │ unsubscribe_agent            │ hh.agents.feed.subscription_runner              │ agent, unsubscribe    │
    │ 🔲  Found:   │ unsubscribe_ask              │ hh.agents.feed.subscription_runner              │ ask, unsubscribe      │
    │ 🔲  Found:   │ unsubscribe_docket           │ hh.agents.feed.subscription_runner              │ docket, unsubscribe   │
    │ 🔲  Found:   │ unsubscribe_keyword          │ hh.agents.feed.subscription_runner              │ keyword, unsubscribe  │
    │ 🔲  Found:   │ unsubscribe_operator         │ hh.agents.feed.subscription_runner              │ operator, unsubscribe │
    │ 🔲  Found:   │ unsubscribe_sidecar          │ hh.agents.feed.subscription_runner              │ sidecar, unsubscribe  │
    │ 🔲  Found:   │ unsubscribe_step             │ hh.agents.feed.subscription_runner              │ step, unsubscribe     │
    │ 🔲  Found:   │ unsubscribe_task             │ hh.agents.feed.subscription_runner              │ task, unsubscribe     │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ answer                       │ hh.agents.onboarding.answer                     │                       │
    │ 🔲  Found:   │ onboard                      │ hh.agents.onboarding.onboard                    │                       │
    │ 🔲  Found:   │ promote                      │ hh.agents.onboarding.promote                    │                       │
    │ 🔲  Found:   │ status                       │ hh.agents.onboarding.status                     │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ clear_cache                  │ hh.deploy.cache.clear_cache                     │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ add_db_users                 │ hh.deploy.db.add_db_users                       │                       │
    │ 🔲  Found:   │ check_db                     │ hh.deploy.db.check_db                           │                       │
    │ 🔲  Found:   │ clean_db                     │ hh.deploy.db.clean_db                           │                       │
    │ 🔲  Found:   │ export_db                    │ hh.deploy.db.export_db                          │                       │
    │ 🔲  Found:   │ import_db                    │ hh.deploy.db.import_db                          │                       │
    │ 🔲  Found:   │ init_db                      │ hh.deploy.db.init_db                            │                       │
    │ 🔲  Found:   │ init_homepage                │ hh.deploy.db.init_homepage                      │                       │
    │ 🔲  Found:   │ remove_db_users              │ hh.deploy.db.remove_db_users                    │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ flask_start                  │ hh.deploy.flask.flask_start                     │                       │
    │ 🔲  Found:   │ flask_status                 │ hh.deploy.flask.flask_status                    │                       │
    │ 🔲  Found:   │ flask_stop                   │ hh.deploy.flask.flask_stop                      │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ pull_project                 │ hh.deploy.git.pull_project                      │                       │
    │ 🔲  Found:   │ push_project                 │ hh.deploy.git.push_project                      │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ http_deploy                  │ hh.deploy.http.http_deploy                      │                       │
    │ 🔲  Found:   │ http_deploy_ssl              │ hh.deploy.http.http_deploy_ssl                  │                       │
    │ 🔲  Found:   │ http_remove                  │ hh.deploy.http.http_remove                      │                       │
    │ 🔲  Found:   │ http_status                  │ hh.deploy.http.http_status                      │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ file_cache_refresh           │ hh.deploy.maint.file_cache_refresh              │                       │
    │ 🔲  Found:   │ image_cache_refresh          │ hh.deploy.maint.image_cache_refresh             │                       │
    │ 🔲  Found:   │ maintenance_jobs_status      │ hh.deploy.maint.maintenance_jobs_status         │                       │
    │ 🔲  Found:   │ orphan_check                 │ hh.deploy.maint.orphan_checks                   │                       │
    │ 🔲  Found:   │ page_cache_refresh           │ hh.deploy.maint.page_cache_refresh              │                       │
    │ 🔲  Found:   │ regex_text                   │ hh.deploy.maint.regex_text                      │                       │
    │ 🔲  Found:   │ update_maintenance_job       │ hh.deploy.maint.update_maintenance_job          │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ maintenance_start            │ hh.deploy.maintenance.maintenance_start         │                       │
    │ 🔲  Found:   │ maintenance_status           │ hh.deploy.maintenance.maintenance_status        │                       │
    │ 🔲  Found:   │ maintenance_stop             │ hh.deploy.maintenance.maintenance_stop          │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ deploy                       │ hh.deploy.srv.deploy                            │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ install                      │ hh.deploy.users.install                         │                       │
    │ 🔲  Found:   │ install_cursor               │ hh.deploy.users.install_cursor                  │                       │
    │ 🔲  Found:   │ uninstall                    │ hh.deploy.users.uninstall                       │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ upload_files                 │ hh.file.upload_file                             │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ dependency_list              │ hh.gateway.system.dependency_list               │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ help                         │ hh.help.help                                    │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_caption               │ hh.image.modify_caption                         │                       │
    │ 🔲  Found:   │ show_image                   │ hh.image.show_image                             │                       │
    │ 🔲  Found:   │ upload_images                │ hh.image.upload_image                           │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_mcp_action_request    │ hh.mcp_action_request.modify_mcp_action_request │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_mcp_request           │ hh.mcp_request.modify_mcp_request               │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ add_image                    │ hh.page.add_image                               │                       │
    │ 🔲  Found:   │ add_images                   │ hh.page.add_images                              │                       │
    │ 🔲  Found:   │ add_page                     │ hh.page.add_page                                │                       │
    │ 🔲  Found:   │ class_list                   │ hh.page.class_list                              │                       │
    │ 🔲  Found:   │ copy_image                   │ hh.page.copy_image                              │                       │
    │ 🔲  Found:   │ copy_images                  │ hh.page.copy_images                             │                       │
    │ 🔲  Found:   │ copy_page                    │ hh.page.copy_page                               │                       │
    │ 🔲  Found:   │ count_pages                  │ hh.page.count_pages                             │                       │
    │ 🔲  Found:   │ delete_page                  │ hh.page.delete_page                             │                       │
    │ 🔲  Found:   │ get_add_page_class_info      │ hh.page.get_add_page_class_info                 │                       │
    │ 🔲  Found:   │ get_page                     │ hh.page.get_page                                │                       │
    │ 🔲  Found:   │ get_text                     │ hh.page.get_text                                │                       │
    │ 🔲  Found:   │ modify_name                  │ hh.page.modify_name                             │                       │
    │ 🔲  Found:   │ modify_text                  │ hh.page.modify_text                             │                       │
    │ 🔲  Found:   │ move_image                   │ hh.page.move_image                              │                       │
    │ 🔲  Found:   │ move_images                  │ hh.page.move_images                             │                       │
    │ 🔲  Found:   │ move_page                    │ hh.page.move_page                               │                       │
    │ 🔲  Found:   │ remove_image                 │ hh.page.remove_image                            │                       │
    │ 🔲  Found:   │ set_image_rank               │ hh.page.set_image_rank                          │                       │
    │ 🔲  Found:   │ show_page                    │ hh.page.show_page                               │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_file_path             │ hh.source_code_file.modify_file_path            │                       │
    │ 🔲  Found:   │ modify_language              │ hh.source_code_file.modify_language             │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_work_meta_remove_pair │ hh.work.modify_work_meta_remove_pair            │                       │
    │ 🔲  Found:   │ modify_work_meta_set_all     │ hh.work.modify_work_meta_set_all                │                       │
    │ 🔲  Found:   │ modify_work_meta_set_pair    │ hh.work.modify_work_meta_set_pair               │                       │
    │ 🔲  Found:   │ modify_work_sort_order       │ hh.work.modify_work_sort_order                  │                       │
    │ 🔲  Found:   │ modify_work_status           │ hh.work.modify_work_status                      │                       │
    └──────────────┴──────────────────────────────┴─────────────────────────────────────────────────┴───────────────────────┘

PS C:\Users\lee\Desktop\henhouse> hen http-list

  🏠 Henhouse:   HTTP List:

    ┌────────────┬────────────┬────────────────────────────┐
    │ 3 commands │ name       │ module                     │
    ╞════════════╪════════════╪════════════════════════════╡
    │ 🔲  Found: │ http_error │ hh.gateway.error.error     │
    ├────────────┼────────────┼────────────────────────────┤
    │ 🔲  Found: │ show_image │ hh.image.render_show_image │
    ├────────────┼────────────┼────────────────────────────┤
    │ 🔲  Found: │ show_page  │ hh.page.render_show_page   │
    └────────────┴────────────┴────────────────────────────┘

PS C:\Users\lee\Desktop\henhouse> hen parser-list

  🏠 Henhouse:   Parser List:

    ┌──────────────┬──────────────────────────────┬──────────────────────────────────────────────────────┐
    │ 101 commands │ name                         │ module                                               │
    ╞══════════════╪══════════════════════════════╪══════════════════════════════════════════════════════╡
    │ ✅  Loaded:  │ backend_list                 │ hh.gateway.registry.render_command_list              │
    │ ✅  Loaded:  │ command_list                 │ hh.gateway.registry.render_command_list              │
    │ ✅  Loaded:  │ action_list                  │ hh.gateway.registry.utils                            │
    │ ✅  Loaded:  │ http_list                    │ hh.gateway.registry.utils                            │
    │ ✅  Loaded:  │ maintenance_list             │ hh.gateway.registry.utils                            │
    │ ✅  Loaded:  │ mcp_list                     │ hh.gateway.registry.utils                            │
    │ ✅  Loaded:  │ parser_list                  │ hh.gateway.registry.utils                            │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ agent_purge                  │ hh.agents.render_agent_purge                         │
    │ 🔲  Found:   │ agent_list                   │ hh.agents.render_agents                              │
    │ 🔲  Found:   │ agent_tree                   │ hh.agents.render_agents                              │
    │ 🔲  Found:   │ punch_in                     │ hh.agents.render_timeclock_punch                     │
    │ 🔲  Found:   │ punch_out                    │ hh.agents.render_timeclock_punch                     │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ gulp                         │ hh.agents.feed.render_gulp                           │
    │ 🔲  Found:   │ gossip                       │ hh.agents.feed.render_sip                            │
    │ 🔲  Found:   │ peek                         │ hh.agents.feed.render_sip                            │
    │ 🔲  Found:   │ sip                          │ hh.agents.feed.render_sip                            │
    │ 🔲  Found:   │ subscribe_agent              │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_ask                │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_docket             │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_keyword            │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_operator           │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_sidecar            │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_step               │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_task               │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_agent            │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_ask              │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_docket           │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_keyword          │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_operator         │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_sidecar          │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_step             │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_task             │ hh.agents.feed.render_subscription                   │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ answer                       │ hh.agents.onboarding.render_answer                   │
    │ 🔲  Found:   │ onboard                      │ hh.agents.onboarding.render_onboard                  │
    │ 🔲  Found:   │ promote                      │ hh.agents.onboarding.render_promote                  │
    │ 🔲  Found:   │ status                       │ hh.agents.onboarding.render_status                   │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ clear_cache                  │ hh.deploy.cache.render_clear_cache                   │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ add_db_users                 │ hh.deploy.db.render_add_db_users                     │
    │ 🔲  Found:   │ check_db                     │ hh.deploy.db.render_check_db                         │
    │ 🔲  Found:   │ clean_db                     │ hh.deploy.db.render_clean_db                         │
    │ 🔲  Found:   │ export_db                    │ hh.deploy.db.render_export_db                        │
    │ 🔲  Found:   │ import_db                    │ hh.deploy.db.render_import_db                        │
    │ 🔲  Found:   │ init_db                      │ hh.deploy.db.render_init_db                          │
    │ 🔲  Found:   │ init_homepage                │ hh.deploy.db.render_init_homepage                    │
    │ 🔲  Found:   │ remove_db_users              │ hh.deploy.db.render_remove_db_users                  │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ flask_start                  │ hh.deploy.flask.render_flask_start                   │
    │ 🔲  Found:   │ flask_status                 │ hh.deploy.flask.render_flask_status                  │
    │ 🔲  Found:   │ flask_stop                   │ hh.deploy.flask.render_flask_stop                    │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ pull_project                 │ hh.deploy.git.render_pull_project                    │
    │ 🔲  Found:   │ push_project                 │ hh.deploy.git.render_push_project                    │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ http_deploy                  │ hh.deploy.http.render_http_deploy                    │
    │ 🔲  Found:   │ http_deploy_ssl              │ hh.deploy.http.render_http_deploy_ssl                │
    │ 🔲  Found:   │ http_remove                  │ hh.deploy.http.render_http_remove                    │
    │ 🔲  Found:   │ http_status                  │ hh.deploy.http.render_http_status                    │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ file_cache_refresh           │ hh.deploy.maint.file_cache_refresh                   │
    │ 🔲  Found:   │ image_cache_refresh          │ hh.deploy.maint.image_cache_refresh                  │
    │ 🔲  Found:   │ maintenance_jobs_status      │ hh.deploy.maint.maintenance_jobs_status              │
    │ 🔲  Found:   │ orphan_check                 │ hh.deploy.maint.orphan_checks                        │
    │ 🔲  Found:   │ page_cache_refresh           │ hh.deploy.maint.page_cache_refresh                   │
    │ 🔲  Found:   │ regex_text                   │ hh.deploy.maint.regex_text                           │
    │ 🔲  Found:   │ update_maintenance_job       │ hh.deploy.maint.update_maintenance_job               │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ maintenance_start            │ hh.deploy.maintenance.render_maintenance_start       │
    │ 🔲  Found:   │ maintenance_status           │ hh.deploy.maintenance.render_maintenance_status      │
    │ 🔲  Found:   │ maintenance_stop             │ hh.deploy.maintenance.render_maintenance_stop        │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ deploy                       │ hh.deploy.srv.render_deploy                          │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ install                      │ hh.deploy.users.render_install                       │
    │ 🔲  Found:   │ install_cursor               │ hh.deploy.users.render_install_cursor                │
    │ 🔲  Found:   │ uninstall                    │ hh.deploy.users.render_uninstall                     │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ parser_error                 │ hh.gateway.error.error                               │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ dependency_list              │ hh.gateway.system.dependency_list                    │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ help                         │ hh.help.render_help                                  │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_caption               │ hh.image.render_show_image                           │
    │ 🔲  Found:   │ show_image                   │ hh.image.render_show_image                           │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_mcp_action_request    │ hh.mcp_action_request.render_show_mcp_action_request │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_mcp_request           │ hh.mcp_request.render_show_mcp_request               │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ class_list                   │ hh.page.class_list                                   │
    │ 🔲  Found:   │ count_pages                  │ hh.page.render_count_pages                           │
    │ 🔲  Found:   │ delete_page                  │ hh.page.render_delete_page                           │
    │ 🔲  Found:   │ get_add_page_class_info      │ hh.page.render_get_add_page_class_info               │
    │ 🔲  Found:   │ get_page                     │ hh.page.render_get_page                              │
    │ 🔲  Found:   │ add_image                    │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ add_images                   │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ add_page                     │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ copy_image                   │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ copy_images                  │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ copy_page                    │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ modify_name                  │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ modify_text                  │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ move_image                   │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ move_images                  │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ move_page                    │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ remove_image                 │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ set_image_rank               │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ show_page                    │ hh.page.render_show_page                             │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_file_path             │ hh.source_code_file.render_show_source_code_file     │
    │ 🔲  Found:   │ modify_language              │ hh.source_code_file.render_show_source_code_file     │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_work_meta_remove_pair │ hh.work.render_show_work_page                        │
    │ 🔲  Found:   │ modify_work_meta_set_all     │ hh.work.render_show_work_page                        │
    │ 🔲  Found:   │ modify_work_meta_set_pair    │ hh.work.render_show_work_page                        │
    │ 🔲  Found:   │ modify_work_sort_order       │ hh.work.render_show_work_page                        │
    │ 🔲  Found:   │ modify_work_status           │ hh.work.render_show_work_page                        │
    └──────────────┴──────────────────────────────┴──────────────────────────────────────────────────────┘

PS C:\Users\lee\Desktop\henhouse> hen mcp-list

  🏠 Henhouse:   MCP List:

    ┌─────────────┬──────────────────────────────┬─────────────────────────┐
    │ 66 commands │ name                         │ module                  │
    ╞═════════════╪══════════════════════════════╪═════════════════════════╡
    │ 🔲  Found:  │ mcp_error                    │ hh.gateway.error.error  │
    ├─────────────┼──────────────────────────────┼─────────────────────────┤
    │ 🔲  Found:  │ action_list                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ add_page                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ agent_list                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ agent_purge                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ agent_tree                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ answer                       │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ backend_list                 │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ command_list                 │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ copy_image                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ copy_images                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ copy_page                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ count_pages                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ delete_page                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ get_add_page_class_info      │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ get_page                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ get_text                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ gossip                       │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ gulp                         │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ help                         │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ http_list                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ mcp_list                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_caption               │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_file_path             │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_language              │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_mcp_action_request    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_mcp_request           │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_name                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_text                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_meta_remove_pair │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_meta_set_all     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_meta_set_pair    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_sort_order       │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_status           │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ move_image                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ move_images                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ move_page                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ onboard                      │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ parser_list                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ peek                         │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ promote                      │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ punch_in                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ punch_out                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ remove_image                 │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ set_image_rank               │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ show_image                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ show_page                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ sip                          │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ status                       │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_agent              │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_ask                │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_docket             │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_keyword            │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_operator           │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_sidecar            │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_step               │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_task               │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_agent            │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_ask              │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_docket           │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_keyword          │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_operator         │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_sidecar          │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_step             │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_task             │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ upload_images                │ hh.gateway.registry.mcp │
    └─────────────┴──────────────────────────────┴─────────────────────────┘

PS C:\Users\lee\Desktop\henhouse> hen maintenance-list

  🏠 Henhouse:   Maintenance List:

    ┌────────────┬─────────────────────────┬─────────────────────────────────┐
    │ 9 commands │ name                    │ module                          │
    ╞════════════╪═════════════════════════╪═════════════════════════════════╡
    │ 🔲  Found: │ maintenance_error       │ hh.gateway.error.error          │
    ├────────────┼─────────────────────────┼─────────────────────────────────┤
    │ 🔲  Found: │ file_cache_refresh      │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ image_cache_refresh     │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ maintenance_jobs_status │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ orphan_check            │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ page_cache_refresh      │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ regex_text              │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ tool_name               │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ update_maintenance_job  │ hh.gateway.registry.maintenance │
    └────────────┴─────────────────────────┴─────────────────────────────────┘

PS C:\Users\lee\Desktop\henhouse> 