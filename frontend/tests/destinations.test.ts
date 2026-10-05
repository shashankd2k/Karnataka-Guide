import { describe, it, expect } from 'vitest';
import { DESTINATIONS } from '../src/data/destinations';

describe('Destinations Catalog Data', () => {
  it('contains exactly the 6 canonical Karnataka destinations', () => {
    expect(DESTINATIONS).toHaveLength(6);
    const slugs = DESTINATIONS.map((d) => d.slug);
    expect(slugs).toEqual(['belur', 'halebidu', 'hampi', 'badami', 'pattadakal', 'aihole']);
  });

  it('verifies all destination coordinates are within Karnataka geographical bounds', () => {
    // Karnataka bounds: lat ~11.5 to 18.5, lon ~74.0 to 78.6
    DESTINATIONS.forEach((dest) => {
      const [lat, lon] = dest.coordinates;
      expect(lat).toBeGreaterThan(11.0);
      expect(lat).toBeLessThan(19.0);
      expect(lon).toBeGreaterThan(73.5);
      expect(lon).toBeLessThan(79.0);
    });
  });

  it('contains valid English and Kannada descriptions and suggested queries', () => {
    DESTINATIONS.forEach((dest) => {
      expect(dest.name).toBeTruthy();
      expect(dest.kannadaName).toBeTruthy();
      expect(dest.shortDescription).toBeTruthy();
      expect(dest.kannadaDescription).toBeTruthy();
      expect(dest.imageAsset.endsWith('.svg')).toBe(true);
      expect(dest.suggestedQueries.length).toBeGreaterThanOrEqual(2);

      dest.suggestedQueries.forEach((q) => {
        expect(q.en).toBeTruthy();
        expect(q.kn).toBeTruthy();
      });
    });
  });
});
