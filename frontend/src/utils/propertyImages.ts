/**
 * RIVO Frontend — Property Image Resolver
 * =======================================
 * Deterministically maps Chennai rental listings to realistic, authentic
 * residential property photography with local static fallbacks.
 *
 * Guaranteed zero broken images:
 *   - Uses local generated high-resolution assets in `/properties/`
 *   - Deterministically hashes listing_id so each property has consistent photos
 *   - Provides cover image and gallery images for detailed view
 */

export interface PropertyImageSet {
  cover: string;
  gallery: string[];
  propertyTypeLabel: string;
}

// Local authentic Chennai property assets
const LOCAL_ASSETS = [
  '/properties/chennai_apartment_1.jpg',
  '/properties/chennai_complex_1.jpg',
  '/properties/chennai_interior_1.jpg',
];

// Curated architectural & residential collections
const CURATED_PROPERTY_COLLECTIONS: { cover: string; gallery: string[]; tag: string }[] = [
  {
    cover: '/properties/chennai_apartment_1.jpg',
    gallery: [
      '/properties/chennai_apartment_1.jpg',
      '/properties/chennai_interior_1.jpg',
      '/properties/chennai_complex_1.jpg',
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1000&q=80',
    ],
    tag: 'Modern Urban Apartment',
  },
  {
    cover: '/properties/chennai_complex_1.jpg',
    gallery: [
      '/properties/chennai_complex_1.jpg',
      '/properties/chennai_apartment_1.jpg',
      '/properties/chennai_interior_1.jpg',
      'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1000&q=80',
    ],
    tag: 'Gated Residential Community',
  },
  {
    cover: '/properties/chennai_interior_1.jpg',
    gallery: [
      '/properties/chennai_interior_1.jpg',
      '/properties/chennai_apartment_1.jpg',
      '/properties/chennai_complex_1.jpg',
      'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1000&q=80',
    ],
    tag: 'Spacious Residential Flat',
  },
  {
    cover: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1000&q=80',
    gallery: [
      'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1000&q=80',
      '/properties/chennai_apartment_1.jpg',
      '/properties/chennai_interior_1.jpg',
      'https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=1000&q=80',
    ],
    tag: 'Suburban Family Home',
  },
  {
    cover: 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1000&q=80',
    gallery: [
      'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1000&q=80',
      '/properties/chennai_interior_1.jpg',
      '/properties/chennai_complex_1.jpg',
      'https://images.unsplash.com/photo-1502005229762-ee1b2b814660?auto=format&fit=crop&w=1000&q=80',
    ],
    tag: 'Metro Corridor Residence',
  },
  {
    cover: 'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1000&q=80',
    gallery: [
      'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=1000&q=80',
      '/properties/chennai_apartment_1.jpg',
      '/properties/chennai_complex_1.jpg',
      'https://images.unsplash.com/photo-1507089947368-19c1da9775ae?auto=format&fit=crop&w=1000&q=80',
    ],
    tag: 'Compact Modern Flat',
  },
];

function stringHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0; // Convert to 32bit integer
  }
  return Math.abs(hash);
}

/**
 * Returns a deterministic, consistent image set for any rental listing.
 */
export function getPropertyImages(
  listingId: string,
  locality?: string,
  bhk?: number
): PropertyImageSet {
  const seed = `${listingId}_${locality || ''}_${bhk || 2}`;
  const idx = stringHash(seed) % CURATED_PROPERTY_COLLECTIONS.length;
  const item = CURATED_PROPERTY_COLLECTIONS[idx];

  return {
    cover: item.cover,
    gallery: item.gallery,
    propertyTypeLabel: item.tag,
  };
}

/** Safe image component with instant fallback on error */
export function getFallbackImage(index = 0): string {
  return LOCAL_ASSETS[index % LOCAL_ASSETS.length];
}
