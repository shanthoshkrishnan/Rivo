import {
  RecommendationRequest,
  RecommendationResponse,
  WorkerOccupation,
  IncomeProfile,
  ScenarioResponse,
  DataSource,
} from '../types/api';

const API_BASE = '/api/v1';

export async function checkBackendHealth(): Promise<{ status: string; version?: string } | null> {
  try {
    const res = await fetch('/health');
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
      {
        occupation_key: 'nurse',
        occupation_label: 'Nurse / Healthcare Worker',
        nic_code: 'Q8610',
        description: 'Registered nurses and other healthcare support staff',
      },
      {
        occupation_key: 'teacher',
        occupation_label: 'School Teacher',
        nic_code: 'P8510',
        description: 'Primary, secondary and higher secondary teachers',
      },
      {
        occupation_key: 'bus_driver',
        occupation_label: 'MTC Bus Driver',
        nic_code: 'H4931',
        description: 'Metropolitan Transport Corporation bus drivers',
      },
      {
        occupation_key: 'delivery_rider',
        occupation_label: 'Delivery Rider',
        nic_code: 'H5320',
        description: 'Food, parcel and logistics delivery riders',
      },
      {
        occupation_key: 'construction_worker',
        occupation_label: 'Construction Worker',
        nic_code: 'F4110',
        description: 'Informal and formal construction labourers',
      },
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

export async function searchRecommendations(
  req: RecommendationRequest
): Promise<RecommendationResponse> {
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

export async function evaluateScenario(params: {
  scenario_type: 'transit' | 'housing';
  occupation_key: string;
  commute_threshold_minutes: number;
  transit_params?: any;
  housing_params?: any;
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
