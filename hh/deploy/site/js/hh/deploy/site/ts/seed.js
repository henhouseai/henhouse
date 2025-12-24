/**
 * Seed data reader - reads initial data from JSON script tag.
 */
/**
 * Read seed data from the JSON script tag in the HTML head.
 * Returns empty object if script tag not found or invalid JSON.
 */
export function getSeedData() {
    const scriptElement = document.getElementById('hh-seed-data');
    if (!scriptElement || !scriptElement.textContent) {
        return {};
    }
    try {
        const data = JSON.parse(scriptElement.textContent);
        return data;
    }
    catch (e) {
        console.error('Failed to parse seed data:', e);
        return {};
    }
}
