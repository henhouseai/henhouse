-- Example data for self-doc module
-- ID range: 20000-29999 (self-doc module block, alphabetically after accounting)
-- All example data should be idempotent and safe to re-run
-- Top-level examples should use parent=1 (homepage)

-- Example: Create sample documentation page (if not exists)
-- INSERT INTO pages (id, parent, name, link, class, text, last_modified, username, visibility, displayStyle)
-- SELECT 20000, 1, 'Example Documentation', 'self_doc_example_docs', 'page',
--        'Sample documentation content', NOW(), 'system', 1, 1
-- WHERE NOT EXISTS (SELECT 1 FROM pages WHERE id = 20000);

-- Note: Uncomment and customize when ready to add example data
