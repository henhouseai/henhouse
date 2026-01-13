-- Example data for accounting module
-- ID range: 10000-19999 (accounting module block)
-- All example data should be idempotent and safe to re-run
-- Top-level examples should use parent=1 (homepage)

-- Example: Create a sample fiscal year (if not exists)
-- INSERT INTO pages (id, parent, name, link, class, text, last_modified, username, visibility, displayStyle)
-- SELECT 10000, 1, 'Example Fiscal Year 2024', 'accounting_example_fiscal_2024', 'fiscal_period',
--        '', NOW(), 'system', 1, 1
-- WHERE NOT EXISTS (SELECT 1 FROM pages WHERE id = 10000);

-- Note: Uncomment and customize when ready to add example data
