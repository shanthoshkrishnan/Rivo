// RIVO Frontend — API Type Definitions (Phase 3)
// =================================================
// These types mirror the backend Pydantic schemas exactly.
// Phase 3 additions:
//   - TransitDetails: full transit step info (agency, line, stops, times)
//   - RouteStep: one step inside a door-to-door itinerary
//   - TrafficInfo: live vs historical traffic for road modes
//   - RouteResult: extended with steps, departure/arrival times, traffic, source_label
//   - ItineraryRequest: request body for /api/v1/routes/itinerary

export type DataFreshness = 'LIVE' | 'RECENT' | 'PERIODIC' | 'ESTIMATED' | 'HISTORICAL' | 'LOW_DATA';
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

// ─── Worker / Occupation ────────────────────────────────────────────────────
export interface WorkerOccupation {
  occupation_key: string;
  occupation_label: string;
  nic_code: string;
  description?: string;
}

export interface IncomeProfile {
  occupation_key: string;
  geography_level: string;
  income_p25?: number;
  income_median?: number;
  income_p75?: number;
  confidence: ConfidenceLevel;
  survey_year: number;
  data_freshness: DataFreshness;
  source_name: string;
}

// ─── Transit Step Details ────────────────────────────────────────────────────
/** Agency, line, stop names, and times for one transit leg. */
export interface TransitDetails {
  agency?: string;           // e.g. "MTC" or "CMRL"
  line?: string;             // full route name
  line_short_name?: string;  // e.g. "21B" or "Blue Line"
  vehicle_type?: string;     // BUS | HEAVY_RAIL | SUBWAY | FERRY
  headsign?: string;         // destination shown on board
  departure_stop?: string;   // boarding stop name
  arrival_stop?: string;     // alighting stop name
  departure_time?: string;   // ISO-8601
  arrival_time?: string;     // ISO-8601
  num_stops?: number;
}

/** One step in a door-to-door route (walk / transit / wait). */
export interface RouteStep {
  type: 'WALK' | 'TRANSIT' | 'WAIT' | 'DRIVE';
  instruction?: string;      // human-readable description
  duration_seconds?: number;
  distance_m?: number;
  polyline?: string;         // encoded polyline for this step
  transit?: TransitDetails;  // only set when type === 'TRANSIT'
}

// ─── Traffic Info (road modes) ───────────────────────────────────────────────
export interface TrafficInfo {
  normal_duration_seconds?: number;
  traffic_duration_seconds?: number;
  /** 'LIVE_TRAFFIC' | 'HISTORICAL' */
  traffic_status?: string;
}

// ─── Route Result ────────────────────────────────────────────────────────────
export interface RouteResult {
  mode: string;              // TRANSIT | DRIVE | TWO_WHEELER | WALK
  provider: string;          // google | gtfs | otp | mock
  distance_m?: number;
  duration_seconds?: number;
  duration_minutes?: number;  // derived by backend
  walk_seconds?: number;
  wait_seconds?: number;
  in_vehicle_seconds?: number;
  transfer_count?: number;
  fare_amount?: number;      // INR one-way
  route_geometry?: string;   // encoded polyline (full route)
  observed_at?: string;      // ISO-8601
  data_freshness: DataFreshness;

  // Phase 3: full itinerary
  steps: RouteStep[];

  // Phase 3: departure / arrival times
  departure_time?: string;   // ISO-8601
  arrival_time?: string;     // ISO-8601

  // Phase 3: traffic info for road modes
  traffic?: TrafficInfo;

  // Phase 3: human-readable source label for provenance panel
  source_label?: string;     // e.g. "Google Routes API" / "CUMTA GTFS"

  // UI badges
  is_fastest?: boolean;
  is_cheapest?: boolean;
  is_fewest_transfers?: boolean;

  // Backward-compat aliases (some components may use these)
  distance_km?: number;
  duration_min?: number;
  fare_inr?: number;
  transfers?: number;
  walking_duration_minutes?: number;
  is_preferred?: boolean;
  monthly_commute_cost?: number;
  fuel_litres_monthly?: number;
  is_anomaly?: boolean;
  transit_summary?: Record<string, any>;
}

// ─── Facility Access ─────────────────────────────────────────────────────────
export interface FacilityAccess {
  nearest_name?: string;
  nearest_minutes?: number;
  distance_m?: number;
  count_within_threshold?: number;
  meets_threshold?: boolean;
  facility_status?: 'available' | 'unavailable' | 'insufficient_data';
  source_name?: string;
}

// ─── Affordability ───────────────────────────────────────────────────────────
export interface AffordabilityBreakdown {
  monthly_rent?: number;
  monthly_maintenance?: number;
  monthly_transport_cost?: number;
  monthly_total_cost?: number;
  housing_burden_pct?: number;
  transport_burden_pct?: number;
  cash_burden_pct?: number;
  /** Time tax: one_way_min × 2 × work_days / 60. Displayed separately. */
  monthly_commute_hours?: number;
}

// ─── Explainability ──────────────────────────────────────────────────────────
export interface ExplainabilityBlock {
  passes_all_hard_constraints: boolean;
  positive_reasons: string[];
  negative_reasons: string[];
  confidence: ConfidenceLevel;
  data_freshness: DataFreshness;
}

// ─── Recommendation ──────────────────────────────────────────────────────────
export interface RecommendationResult {
  listing_id: string;
  provider: string;
  locality?: string;
  address?: string;
  deposit?: number;
  bhk?: number;
  area_sqft?: number;
  furnishing?: string;
  property_type?: string;
  latitude?: number;
  longitude?: number;
  rent_monthly?: number;
  maintenance_monthly?: number;
  best_route?: RouteResult;
  all_routes: RouteResult[];
  affordability?: AffordabilityBreakdown;
  school_access?: FacilityAccess;
  hospital_access?: FacilityAccess;
  pharmacy_access?: FacilityAccess;
  nearest_facilities?: Record<string, { name: string; distance_m: number; travel_time_min?: number }>;
  rejection_reasons?: string[];
  is_demo?: boolean;
  coordinate_source?: string;
  score_total?: number;
  score_components?: Record<string, number>;
  explainability?: ExplainabilityBlock;
  data_freshness: DataFreshness;
  availability_status?: 'AVAILABLE' | 'PENDING_CONFIRMATION' | 'RECENTLY_SEEN' | 'UNAVAILABLE' | 'UNKNOWN';
  verification_status?: 'UNVERIFIED' | 'LOCATION_VERIFIED' | 'OWNER_ATTESTED' | 'RIVO_VERIFIED';
  geocode_confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  source_name?: string;
  observed_at?: string;
  first_seen_at?: string;
  last_seen_at?: string;
  market_comparison?: MarketComparison;
  rent_percentiles?: { p25?: number; p50?: number; p75?: number };
}

export interface MarketComparison {
  asking_rent: number;
  expected_range_min?: number;
  expected_range_max?: number;
  median_estimate?: number;
  market_position: 'WITHIN_RANGE' | 'ABOVE_RANGE' | 'BELOW_RANGE' | 'INSUFFICIENT_DATA';
  market_position_label: string;
  confidence: string;
  model_version: string;
}


export interface RecommendationResponse {
  total: number;
  page: number;
  page_size: number;
  results: RecommendationResult[];
  rejected_results?: RecommendationResult[];
  search_metadata?: Record<string, unknown>;
}

// ─── Request Types ───────────────────────────────────────────────────────────
export interface FamilyContext {
  adults: number;
  children: number;
  child_age_bands: string[];
  school_max_minutes?: number;
  hospital_max_minutes?: number;
  pharmacy_max_minutes?: number;
  require_within_threshold?: boolean;
}

export interface WorkerContext {
  occupation_key?: string;
  household_income_monthly?: number;
  income_band?: string;
}

export interface RecommendationRequest {
  min_rent_monthly?: number;
  max_rent_monthly: number;
  bhk?: number;
  property_type?: string;
  workplace_lat: number;
  workplace_lon: number;
  workplace_label?: string;
  max_commute_minutes: number;
  max_transfers?: number;
  max_walk_minutes?: number;
  preferred_modes: string[];
  worker?: WorkerContext;
  family?: FamilyContext;
  search_lat?: number;
  search_lon?: number;
  search_radius_km?: number;
  work_days_per_month?: number;
  page?: number;
  page_size?: number;
}

/** POST /api/v1/routes/itinerary — full trip plan for a selected listing. */
export interface ItineraryRequest {
  home_lat: number;
  home_lon: number;
  workplace_lat: number;
  workplace_lon: number;
  departure_time?: string;   // ISO-8601
  mode: string;              // TRANSIT | DRIVE | TWO_WHEELER | WALK
}

// ─── Scenario ────────────────────────────────────────────────────────────────
export interface ScenarioMetrics {
  worker_reach_30min?: number;
  worker_reach_45min?: number;
  worker_reach_60min?: number;
  worker_reach_lower_bound?: number;
  worker_reach_upper_bound?: number;
  affordable_listings?: number;
  commute_median_minutes?: number;
  catchment_sqkm?: number;
}

export interface ScenarioStateMetrics {
  reachable_workers: number;
  median_commute_minutes: number;
  affordable_listings: number;
  monthly_transport_cost: number;
  monthly_rent_estimate: number;
  monthly_income: number;
  housing_burden_pct: number;
  transport_burden_pct: number;
  cash_burden_pct: number;
}

export interface ScenarioChangeMetrics {
  workers_reached: number;
  commute_minutes_saved_per_trip: number;
  affordable_listings_added: number;
  monthly_transport_savings: number;
  annual_transport_savings: number;
}

export interface ScenarioWorkerImpact {
  time_saved_per_trip_minutes: number;
  work_days_per_month: number;
  monthly_time_saved_hours: number;
  annual_time_saved_hours: number;
  monthly_money_saved: number;
  annual_money_saved: number;
}

export interface ScenarioConfidence {
  level: string;
  data_type: string;
  sources: string[];
  disclaimer: string;
}

export interface ScenarioMapData {
  corridors: Array<{
    id: string;
    name: string;
    short_name: string;
    color: string;
    length_km: number;
    is_selected: boolean;
    coordinates: [number, number][];
  }>;
  stations: Array<{
    name: string;
    lat: number;
    lon: number;
    type?: string;
  }>;
  catchment_circles: Array<{
    name: string;
    lat: number;
    lon: number;
    radius_meters: number;
    type: string;
  }>;
  housing_sites: Array<{
    id: string;
    name: string;
    lat: number;
    lon: number;
    target_rent: number;
    units: number;
    is_selected: boolean;
  }>;
  employment_clusters: Array<{
    id: string;
    name: string;
    category: string;
    lat: number;
    lon: number;
    estimated_workers: number;
  }>;
  current_reachable_area: [number, number][];
  proposed_reachable_area: [number, number][];
}

export interface ScenarioResponse {
  scenario_id: string;
  occupation_key: string;
  scenario_type?: 'transit' | 'housing';
  scenario_name?: string;
  scenario_status_label?: string;
  project_status?: string;
  before: ScenarioMetrics;
  after: ScenarioMetrics;
  current?: ScenarioStateMetrics;
  proposed?: ScenarioStateMetrics;
  change?: ScenarioChangeMetrics;
  worker_impact?: ScenarioWorkerImpact;
  confidence_detail?: ScenarioConfidence;
  map_data?: ScenarioMapData;
  delta_worker_reach_45min?: number;
  delta_affordable_listings?: number;
  computed_at: string;
  data_freshness: DataFreshness;
  confidence?: string;
  methodology?: string;
  affected_neighborhoods?: string[];
}

// ─── Data Sources ────────────────────────────────────────────────────────────
export interface DataSource {
  id: string;
  source_name: string;
  layer?: string;
  source_url?: string;
  retrieved_at?: string;
  effective_date?: string;
  license?: string;
  attribution?: string;
  data_freshness?: DataFreshness;
  update_frequency?: string;
}
