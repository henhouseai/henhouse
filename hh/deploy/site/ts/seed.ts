/**
 * Seed data reader - reads initial data from JSON script tag.
 */

export interface SeedData {
  page?: {
    id?: number | string;
    name?: string;
    title?: string;
    class?: string;
    [key: string]: any;
  };
  menu?: any;
  user?: any;
  [key: string]: any;
}

/**
 * Read seed data from the JSON script tag in the HTML head.
 * Returns empty object if script tag not found or invalid JSON.
 */
export function getSeedData(): SeedData {
  const scriptElement = document.getElementById('hh-seed-data');
  if (!scriptElement || !scriptElement.textContent) {
    return {};
  }
  
  try {
    const data = JSON.parse(scriptElement.textContent);
    return data as SeedData;
  } catch (e) {
    console.error('Failed to parse seed data:', e);
    return {};
  }
}

