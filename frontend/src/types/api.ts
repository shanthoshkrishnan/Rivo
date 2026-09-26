export type DataFreshness = 'LIVE' | 'RECENT' | 'PERIODIC' | 'ESTIMATED' | 'HISTORICAL' | 'LOW_DATA';
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

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

export interface RouteStep {
  mode: string;
  duration_minutes: number;
  instruction?: string;
}

export interface RouteResult {
  mode: string;
  duration_minutes: number;
  distance_km: number;
  fare_inr: number;
  transfers: number;
  walking_duration_minutes: number;
  provider: string;
  data_freshness: DataFreshness;
  steps: RouteStep[];
  is_fastest?: boolean;
  is_cheapest?: boolean;
  is_fewest_transfers?: boolean;
  is_preferred?: boolean;
}

export interface FacilityAccess {
  nearest_minutes?: number;
  count_within_threshold?: number;
  meets_threshold?: boolean;
}

export interface AffordabilityBreakdown {
  monthly_rent?: number;
  monthly_maintenance?: number;
  monthly_transport_cost?: number;
  monthly_total_cost?: number;
  housing_burden_pct?: number;
  transport_burden_pct?: number;
  cash_burden_pct?: number;
  monthly_commute_hours?: number;
}

export interface ExplainabilityBlock {
  passes_all_hard_constraints: boolean;
  positive_reasons: string[];
  negative_reasons: string[];
  confidence: ConfidenceLevel;
  data_freshness: DataFreshness;
}

export interface RecommendationResult {
  listing_id: string;
  provider: string;
  locality?: string;
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
  score_total?: number;
  score_components?: Record<string, number>;
  explainability?: ExplainabilityBlock;
  data_freshness: DataFreshness;
  first_seen_at?: string;
  last_seen_at?: string;
}

export interface RecommendationResponse {
  total: number;
  page: number;
  page_size: number;
  results: RecommendationResult[];
  search_metadata?: Record<string, any>;
}

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

export interface ScenarioMetrics {
  worker_reach_30min?: number;
  worker_reach_45min?: number;
  worker_reach_60min?: number;
  affordable_listings?: number;
  commute_median_minutes?: number;
}

export interface ScenarioResponse {
  scenario_id: string;
  occupation_key: string;
  before: ScenarioMetrics;
  after: ScenarioMetrics;
  delta_worker_reach_45min?: number;
  delta_affordable_listings?: number;
  computed_at: string;
  data_freshness: DataFreshness;
}

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
