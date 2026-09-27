import {
  RecommendationRequest,
  RecommendationResponse,
  RecommendationResult,
  WorkerOccupation,
  IncomeProfile,
  ScenarioResponse,
  DataSource,
  ItineraryRequest,
  RouteResult,
} from '../types/api';

const API_BASE = '/api/v1';

export interface RouteComparison {
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  routes: RouteResult[];
  computed_at: string;
  data_freshness: string;
}

export async function checkBackendHealth(): Promise<{
  status: string;
  version?: string;
  google_routes?: string;
  google_places?: string;
} | null> {
  try {
    const res = await fetch('/health');
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchSystemIntegrations(): Promise<{
  google_maps: string;
  google_places: string;
  google_routes: string;
  rental_provider: string;
  gtfs: string;
  mock_mode: boolean;
} | null> {
  try {
    const res = await fetch(`${API_BASE}/system/integrations`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchOccupations(): Promise<WorkerOccupation[]> {
  try {
    const res = await fetch(`${API_BASE}/workers/occupations`);
    if (!res.ok) throw new Error('Failed to load occupations');
    return await res.json();
  } catch (err) {
    console.warn('Using fallback occupations', err);
    return [
      { occupation_key: 'nurse', occupation_label: 'Nurse / Healthcare Worker', nic_code: 'Q8610', description: 'Registered nurses and other healthcare support staff' },
      { occupation_key: 'teacher', occupation_label: 'School Teacher', nic_code: 'P8510', description: 'Primary, secondary and higher secondary teachers' },
      { occupation_key: 'bus_driver', occupation_label: 'MTC Bus Driver', nic_code: 'H4931', description: 'Metropolitan Transport Corporation bus drivers' },
      { occupation_key: 'delivery_rider', occupation_label: 'Delivery Rider', nic_code: 'H5320', description: 'Food, parcel and logistics delivery riders' },
      { occupation_key: 'construction_worker', occupation_label: 'Construction Worker', nic_code: 'F4110', description: 'Informal and formal construction labourers' },
    ];
  }
}

export async function fetchIncomeProfile(occupationKey: string): Promise<IncomeProfile | null> {
  try {
    const res = await fetch(`${API_BASE}/workers/income/${occupationKey}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function searchRecommendations(req: RecommendationRequest): Promise<RecommendationResponse> {
  const res = await fetch(`${API_BASE}/recommendations/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to search recommendations');
  }
  return await res.json();
}

export interface RecommendationDetailRequest {
  listing_id: string;
  workplace_lat: number;
  workplace_lon: number;
  workplace_label?: string;
  preferred_modes?: string[];
  worker?: unknown;
  family?: unknown;
  work_days_per_month?: number;
}

export interface RecommendationDetailResponse {
  result: RecommendationResult;
  rental_source_notice: string;
  google_status: string;
  request_summary: Record<string, unknown>;
}

export async function fetchRecommendationDetail(
  req: RecommendationDetailRequest
): Promise<RecommendationDetailResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/recommendations/detail`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn('Recommendation detail fetch failed', err);
    return null;
  }
}

/**
 * Fetch the full door-to-door itinerary for a selected listing.
 * Call ONLY after the user selects a specific listing — not during bulk search.
 */
export async function fetchItinerary(req: ItineraryRequest): Promise<RouteResult | null> {
  try {
    const res = await fetch(`${API_BASE}/routes/itinerary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn('Itinerary fetch failed', err);
    return null;
  }
}

/** Fetch multi-mode route comparison for an origin→destination pair. */
export async function fetchRouteComparison(params: {
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  departure_time?: string;
  modes?: string[];
}): Promise<RouteComparison | null> {
  try {
    const res = await fetch(`${API_BASE}/routes/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn('Route comparison fetch failed', err);
    return null;
  }
}

/** Fetch nearby facilities (school / hospital / pharmacy). */
export async function fetchNearbyFacilities(params: {
  latitude: number;
  longitude: number;
  facility_type: 'school' | 'hospital' | 'pharmacy';
  radius_km?: number;
  limit?: number;
}): Promise<{ facility_type: string; results: unknown[]; data_freshness: string } | null> {
  try {
    const qs = new URLSearchParams({
      latitude: String(params.latitude),
      longitude: String(params.longitude),
      facility_type: params.facility_type,
      radius_km: String(params.radius_km ?? 3.0),
      limit: String(params.limit ?? 5),
    });
    const res = await fetch(`${API_BASE}/facilities/nearby?${qs}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function evaluateScenario(params: {
  scenario_type: 'transit' | 'housing';
  occupation_key: string;
  income_band?: 'p25' | 'median' | 'p75';
  monthly_income?: number;
  commute_threshold_minutes: number;
  work_days_per_month?: number;
  transit_params?: unknown;
  housing_params?: unknown;
}): Promise<ScenarioResponse> {
  const res = await fetch(`${API_BASE}/scenarios/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to evaluate scenario');
  }
  return await res.json();
}

export async function fetchDataSources(): Promise<DataSource[]> {
  try {
    const res = await fetch(`${API_BASE}/data/sources`);
    if (!res.ok) throw new Error('Failed to load data sources');
    return await res.json();
  } catch (err) {
    console.warn('Using fallback data sources', err);
    return [];
  }
}

export interface WorkplaceResult {
  name: string;
  area: string;
  category: string;
  latitude: number;
  longitude: number;
}

export async function searchWorkplaces(query: string): Promise<WorkplaceResult[]> {
  try {
    const res = await fetch(`${API_BASE}/facilities/search-workplaces?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error('Place search failed');
    return await res.json();
  } catch (err) {
    console.warn('Workplace search fallback', err);
    // Instant fallback for local development or offline scenarios
    const fallbackWorkplaces: WorkplaceResult[] = [
      { name: 'Tidel Park', area: 'Taramani, OMR', category: 'IT & Tech Park', latitude: 12.9892, longitude: 80.2494 },
      { name: 'TCS Siruseri (SIPCOT IT Park)', area: 'Siruseri, OMR', category: 'IT Park', latitude: 12.8277, longitude: 80.2195 },
      { name: 'DLF Cybercity', area: 'Manapakkam / Porur', category: 'IT & Business Hub', latitude: 13.0183, longitude: 80.1772 },
      { name: 'Guindy Industrial Estate / SIDCO', area: 'Guindy', category: 'Industrial & Tech', latitude: 13.0067, longitude: 80.2023 },
      { name: 'Rajiv Gandhi Govt General Hospital (RGGGH)', area: 'Park Town, Central', category: 'Govt Hospital', latitude: 13.0815, longitude: 80.2785 },
      { name: 'Government Stanley Medical College', area: 'Royapuram, North Chennai', category: 'Govt Hospital', latitude: 13.1075, longitude: 80.2885 },
      { name: 'Kilpauk Medical College (KMC)', area: 'Kilpauk', category: 'Govt Hospital', latitude: 13.0784, longitude: 80.2435 },
      { name: 'Ambattur Industrial Estate', area: 'Ambattur OT', category: 'Manufacturing & MSME', latitude: 13.1143, longitude: 80.1548 },
      { name: 'Chennai Central Railway Station', area: 'Park Town / George Town', category: 'Transit & Commercial', latitude: 13.0827, longitude: 80.2707 },
      { name: 'Koyambedu Wholesale Market & CMBT', area: 'Koyambedu', category: 'Commercial & Transit', latitude: 13.0694, longitude: 80.1948 },
      { name: 'Ascendas International Tech Park', area: 'Taramani', category: 'IT Park', latitude: 12.9880, longitude: 80.2443 },
      { name: 'IIT Madras Research Park', area: 'Kanagam / Taramani', category: 'Research & Tech', latitude: 12.9915, longitude: 80.2425 },
      { name: 'Sriperumbudur Automotive Corridor', area: 'Sriperumbudur', category: 'Manufacturing Hub', latitude: 12.9675, longitude: 79.9442 },
      { name: 'Mahindra World City', area: 'Chengalpattu', category: 'Special Economic Zone', latitude: 12.7380, longitude: 80.0050 },
      { name: 'Tambaram Railway Station & GST Market', area: 'Tambaram West', category: 'Transit & Retail', latitude: 12.9249, longitude: 80.1197 },
      { name: 'Anna Nagar Roundtana Hub', area: 'Anna Nagar East', category: 'Commercial Center', latitude: 13.0850, longitude: 80.2120 },
      { name: 'T. Nagar Panagal Park', area: 'T. Nagar', category: 'Retail & Trade', latitude: 13.0405, longitude: 80.2337 },
    ];
    const q = query.toLowerCase().trim();
    if (!q) return fallbackWorkplaces.slice(0, 6);
    return fallbackWorkplaces.filter(
      w => w.name.toLowerCase().includes(q) || w.area.toLowerCase().includes(q) || w.category.toLowerCase().includes(q)
    );
  }
}

export interface MapFacility {
  id: string;
  name: string;
  type: string;
  category: 'school' | 'hospital' | 'pharmacy' | 'transit' | 'workplace';
  latitude: number;
  longitude: number;
  address?: string;
  line?: string;
  area?: string;
  distance_km?: number;
  source: string;
  verification_state: string;
}

export interface FacilityLayersResponse {
  schools: MapFacility[];
  hospitals: MapFacility[];
  pharmacies: MapFacility[];
  transit: MapFacility[];
  workplaces: MapFacility[];
}

export async function fetchFacilityLayers(params?: {
  lat?: number;
  lon?: number;
  radius_km?: number;
}): Promise<FacilityLayersResponse> {
  try {
    const query = new URLSearchParams();
    if (params?.lat !== undefined) query.set('lat', params.lat.toString());
    if (params?.lon !== undefined) query.set('lon', params.lon.toString());
    if (params?.radius_km !== undefined) query.set('radius_km', params.radius_km.toString());

    const res = await fetch(`${API_BASE}/facilities/layers?${query.toString()}`);
    if (!res.ok) throw new Error('Failed to load facility layers');
    return await res.json();
  } catch (err) {
    console.warn('Facility layers fetch failed', err);
    return { schools: [], hospitals: [], pharmacies: [], transit: [], workplaces: [] };
  }
}

