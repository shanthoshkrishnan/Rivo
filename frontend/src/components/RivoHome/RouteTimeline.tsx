/**
 * RIVO — Route Timeline Component (Phase 3)
 * ============================================
 * Displays the full door-to-door transit itinerary as a vertical timeline.
 *
 * Shows:
 *   Walk → Board transit (agency, line, headsign) → Transfer → Alight → Walk → Arrive
 *
 * Rules:
 *   - All values come from the RouteResult steps (from Google Routes or GTFS).
 *   - NEVER shows invented stop names, bus numbers or departure times.
 *   - Shows provider + freshness badge so user knows what is LIVE vs ESTIMATED.
 *   - If no steps available (e.g., mock provider), shows simplified summary.
 */
import React from 'react';
import { RouteResult, RouteStep } from '../../types/api';

interface RouteTimelineProps {
  route: RouteResult;
  /** Optional refresh callback — invoked when user clicks "Refresh live data" */
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

// ── Freshness badge ──────────────────────────────────────────────────────────
const FRESHNESS_COLORS: Record<string, string> = {
  LIVE: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
  RECENT: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  PERIODIC: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  ESTIMATED: 'bg-slate-500/20 text-slate-300 border border-slate-500/30',
  HISTORICAL: 'bg-slate-500/20 text-slate-300 border border-slate-500/30',
};

function FreshnessBadge({ freshness }: { freshness: string }) {
  const cls = FRESHNESS_COLORS[freshness] || FRESHNESS_COLORS.ESTIMATED;
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider ${cls}`}>
      {freshness}
    </span>
  );
}

// ── Step icon ────────────────────────────────────────────────────────────────
function StepIcon({ type, vehicleType }: { type: string; vehicleType?: string }) {
  if (type === 'WALK') {
    return (
      <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center text-base">
        🚶
      </div>
    );
  }
  if (type === 'TRANSIT') {
    const vt = (vehicleType || '').toLowerCase();
    if (vt.includes('subway') || vt.includes('metro') || vt.includes('heavy_rail')) {
      return <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-base">🚇</div>;
    }
    if (vt.includes('bus')) {
      return <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-base">🚌</div>;
    }
    return <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-base">🚆</div>;
  }
  if (type === 'WAIT') {
    return <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-base">⏳</div>;
  }
  return <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center text-base">🚗</div>;
}

// ── Format seconds ───────────────────────────────────────────────────────────
function fmtSec(sec?: number | null): string {
  if (!sec) return '';
  const m = Math.round(sec / 60);
  return `${m} min`;
}

// ── Format datetime string ────────────────────────────────────────────────────
function fmtTime(iso?: string | null): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
  } catch {
    return '';
  }
}

// ── Single step row ──────────────────────────────────────────────────────────
function StepRow({ step }: { step: RouteStep }) {
  const td = step.transit;
  const durationLabel = fmtSec(step.duration_seconds);

  return (
    <div className="flex gap-3 items-start">
      {/* Icon + connector */}
      <div className="flex flex-col items-center">
        <StepIcon type={step.type} vehicleType={td?.vehicle_type} />
        <div className="w-px flex-1 bg-slate-600 my-1 min-h-[16px]" />
      </div>

      {/* Step content */}
      <div className="flex-1 pb-4">
        {step.type === 'WALK' && (
          <div>
            <div className="text-sm font-medium text-slate-200">
              Walk {durationLabel && <span className="text-slate-400 font-normal">{durationLabel}</span>}
            </div>
            {step.instruction && step.instruction !== `Walk ` && (
              <div className="text-xs text-slate-400 mt-0.5">{step.instruction}</div>
            )}
            {step.distance_m && (
              <div className="text-xs text-slate-500">{Math.round(step.distance_m)} m</div>
            )}
          </div>
        )}

        {step.type === 'TRANSIT' && td && (
          <div>
            {/* Departure */}
            {td.departure_time && (
              <div className="text-base font-bold text-white font-mono mb-1">
                {fmtTime(td.departure_time)}
              </div>
            )}

            {/* Agency + Line + Headsign */}
            <div className="text-sm font-semibold text-slate-100">
              {td.agency && <span className="text-cyan-400">{td.agency}</span>}
              {td.line_short_name && (
                <span className="ml-1 bg-slate-700 px-1.5 py-0.5 rounded text-xs font-mono">
                  {td.line_short_name}
                </span>
              )}
              {td.line && td.line !== td.line_short_name && (
                <span className="ml-1 text-slate-300 font-normal">{td.line}</span>
              )}
            </div>

            {/* Departure stop */}
            {td.departure_stop && (
              <div className="text-xs text-slate-400 mt-1">
                📍 Board at <span className="text-slate-200">{td.departure_stop}</span>
              </div>
            )}

            {/* Headsign */}
            {td.headsign && (
              <div className="text-xs text-slate-400">
                → toward <span className="text-slate-200">{td.headsign}</span>
              </div>
            )}

            {/* Duration bar */}
            <div className="my-1.5 pl-2 border-l-2 border-slate-600 py-1">
              <div className="text-xs text-slate-400">{durationLabel}{td.num_stops ? ` · ${td.num_stops} stops` : ''}</div>
            </div>

            {/* Arrival stop */}
            {td.arrival_stop && (
              <div className="text-xs text-slate-400">
                🏁 Alight at <span className="text-slate-200">{td.arrival_stop}</span>
              </div>
            )}

            {td.arrival_time && (
              <div className="text-sm font-mono text-slate-300 mt-0.5">{fmtTime(td.arrival_time)}</div>
            )}
          </div>
        )}

        {step.type === 'WAIT' && (
          <div className="text-sm text-slate-400">
            Wait {durationLabel && <span>{durationLabel}</span>} at stop
          </div>
        )}
      </div>
    </div>
  );
}

// ── Simplified summary (when no steps available) ──────────────────────────────
function SimpleSummary({ route }: { route: RouteResult }) {
  const totalMin = route.duration_seconds ? Math.round(route.duration_seconds / 60) : null;
  const walkMin = route.walk_seconds ? Math.round(route.walk_seconds / 60) : null;
  const inVehicleMin = route.in_vehicle_seconds ? Math.round(route.in_vehicle_seconds / 60) : null;

  return (
    <div className="space-y-2 text-sm text-slate-300">
      {route.departure_time && (
        <div className="flex items-center gap-2">
          <span className="text-slate-400 w-14 font-mono text-xs">{fmtTime(route.departure_time)}</span>
          <span>Departure</span>
        </div>
      )}
      {walkMin !== null && walkMin > 0 && (
        <div className="flex items-center gap-2">
          <span className="w-14" />
          <span>🚶 Walk {walkMin} min to transit</span>
        </div>
      )}
      {inVehicleMin !== null && inVehicleMin > 0 && (
        <div className="flex items-center gap-2">
          <span className="w-14" />
          <span>🚌 Transit {inVehicleMin} min</span>
        </div>
      )}
      {walkMin !== null && walkMin > 0 && (
        <div className="flex items-center gap-2">
          <span className="w-14" />
          <span>🚶 Walk {walkMin} min to workplace</span>
        </div>
      )}
      {route.arrival_time && (
        <div className="flex items-center gap-2">
          <span className="text-slate-400 w-14 font-mono text-xs">{fmtTime(route.arrival_time)}</span>
          <span className="font-semibold text-white">Arrival</span>
        </div>
      )}
      {totalMin && (
        <div className="pt-1 text-slate-400 text-xs">
          {totalMin} min total
          {route.fare_amount != null && ` · ₹${route.fare_amount} estimated fare`}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function RouteTimeline({ route, onRefresh, isRefreshing }: RouteTimelineProps) {
  const totalMin = route.duration_seconds ? Math.round(route.duration_seconds / 60) : null;
  const transferCount = route.transfer_count ?? 0;
  const hasSteps = route.steps && route.steps.length > 0;

  const monthlyCommute = route.fare_amount != null
    ? Math.round(route.fare_amount * 2 * 22)
    : null;

  const monthlyHours = route.duration_seconds
    ? Math.round((route.duration_seconds / 60) * 2 * 22 / 60 * 10) / 10
    : null;

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-white text-sm">
            {route.mode === 'TRANSIT' ? '🚌 Transit Route' :
             route.mode === 'DRIVE' ? '🚗 Drive Route' :
             route.mode === 'TWO_WHEELER' ? '🛵 Two-Wheeler' : '🚶 Walking Route'}
          </span>
          <FreshnessBadge freshness={route.data_freshness} />
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors disabled:opacity-50"
          >
            {isRefreshing ? '⟳ Refreshing…' : '↻ Refresh live data'}
          </button>
        )}
      </div>

      {/* Provider source label */}
      {route.source_label && (
        <div className="text-[10px] text-slate-500 font-mono">
          Source: {route.source_label}
          {route.observed_at && (
            <span className="ml-2">
              · {new Date(route.observed_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3 py-2 border-y border-slate-700/50">
        <div className="text-center">
          <div className="text-lg font-bold text-white">{totalMin ?? '—'}</div>
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">min door-to-door</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-white">
            {route.fare_amount != null ? `₹${route.fare_amount}` : '—'}
          </div>
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">one-way fare</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-white">{transferCount}</div>
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">
            {transferCount === 1 ? 'transfer' : 'transfers'}
          </div>
        </div>
      </div>

      {/* Itinerary steps OR simplified summary */}
      <div className="pt-1">
        {hasSteps ? (
          <div>
            {/* Departure time header */}
            {route.departure_time && (
              <div className="flex items-center gap-2 mb-3">
                <span className="text-base font-bold text-white font-mono">
                  {fmtTime(route.departure_time)}
                </span>
                <span className="text-xs text-slate-400">departure</span>
              </div>
            )}

            {/* Steps */}
            {route.steps.map((step, i) => (
              <StepRow key={i} step={step} />
            ))}

            {/* Arrival */}
            {route.arrival_time && (
              <div className="flex items-center gap-2 mt-1">
                <div className="w-8 h-8 rounded-full bg-cyan-600 flex items-center justify-center text-base">🏁</div>
                <div>
                  <div className="text-base font-bold text-white font-mono">{fmtTime(route.arrival_time)}</div>
                  <div className="text-xs text-slate-400">arrival at workplace</div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <SimpleSummary route={route} />
        )}
      </div>

      {/* Monthly cost and time tax */}
      {(monthlyCommute != null || monthlyHours != null) && (
        <div className="pt-2 border-t border-slate-700/50 grid grid-cols-2 gap-3">
          {monthlyCommute != null && (
            <div>
              <div className="text-xs text-slate-400">Monthly commute cost</div>
              <div className="text-sm font-semibold text-amber-300">₹{monthlyCommute.toLocaleString()}/mo</div>
              <div className="text-[10px] text-slate-500">fare × 2 × 22 work days</div>
            </div>
          )}
          {monthlyHours != null && (
            <div>
              <div className="text-xs text-slate-400">Monthly commute hours</div>
              <div className="text-sm font-semibold text-[#F7C948]">{monthlyHours} hrs/mo</div>
              <div className="text-[10px] text-slate-500">time tax (shown separately)</div>
            </div>
          )}
        </div>
      )}

      {/* Traffic info for road modes */}
      {route.traffic && route.traffic.traffic_status === 'LIVE_TRAFFIC' && (
        <div className="text-xs text-slate-400 bg-slate-700/30 rounded-lg px-3 py-2">
          🚦 <span className="text-emerald-400 font-semibold">Live traffic</span>:{' '}
          {route.traffic.traffic_duration_seconds
            ? `${Math.round(route.traffic.traffic_duration_seconds / 60)} min (traffic-adjusted)`
            : 'Traffic data applied'}{' '}
          {route.traffic.normal_duration_seconds &&
            route.traffic.traffic_duration_seconds &&
            route.traffic.traffic_duration_seconds !== route.traffic.normal_duration_seconds && (
              <span className="text-slate-500 ml-1">
                (free-flow: {Math.round(route.traffic.normal_duration_seconds / 60)} min)
              </span>
            )}
        </div>
      )}

      {/* Fallback notice */}
      {route.provider === 'mock' && (
        <div className="text-xs text-amber-400/80 bg-amber-500/10 rounded-lg px-3 py-2 border border-amber-500/20">
          ⚠ Estimated route — live data unavailable. Configure GOOGLE_ROUTES_API_KEY for live transit routing.
        </div>
      )}
      {route.provider === 'gtfs' && (
        <div className="text-xs text-blue-400/80 bg-blue-500/10 rounded-lg px-3 py-2 border border-blue-500/20">
          ℹ CUMTA GTFS network data (PERIODIC). Configure GOOGLE_ROUTES_API_KEY for live real-time routing.
        </div>
      )}
    </div>
  );
}
