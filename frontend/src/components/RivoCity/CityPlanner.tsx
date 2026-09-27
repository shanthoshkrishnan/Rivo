import React, { useState, useEffect } from 'react';
import {
  Compass,
  TrendingUp,
  Clock,
  Home,
  Users,
  Layers,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  ArrowRight,
  Wallet,
  Building2,
  Train,
  CheckCircle2,
  Calendar,
} from 'lucide-react';
import { WorkerOccupation, ScenarioResponse } from '../../types/api';
import { evaluateScenario } from '../../services/api';
import { CityMap } from './CityMap';

interface CityPlannerProps {
  occupations: WorkerOccupation[];
}

export const CityPlanner: React.FC<CityPlannerProps> = ({ occupations }) => {
  // Scenario State Controls
  const [selectedOccupation, setSelectedOccupation] = useState<string>('nurse');
  const [incomeBand, setIncomeBand] = useState<'p25' | 'median' | 'p75'>('median');
  const [commuteThreshold, setCommuteThreshold] = useState<number>(45);
  const [scenarioType, setScenarioType] = useState<'transit' | 'housing'>('transit');
  const [transitCorridor, setTransitCorridor] = useState<string>('cmrl_c4');
  const [housingLocality, setHousingLocality] = useState<string>('ambattur');
  const [housingUnits, setHousingUnits] = useState<number>(120);
  const [housingRent, setHousingRent] = useState<number>(14000);
  const [targetBhk, setTargetBhk] = useState<string>('1-2 BHK');

  // Evaluation Status
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [scenarioResult, setScenarioResult] = useState<ScenarioResponse | null>(null);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);
  const [showMethodology, setShowMethodology] = useState<boolean>(false);

  // Run evaluation
  const runEvaluation = async (overrides?: {
    occ?: string;
    inc?: 'p25' | 'median' | 'p75';
    commute?: number;
    type?: 'transit' | 'housing';
    corridor?: string;
    locality?: string;
    units?: number;
    rent?: number;
  }) => {
    setIsEvaluating(true);
    setEvaluationError(null);

    const activeOcc = overrides?.occ ?? selectedOccupation;
    const activeInc = overrides?.inc ?? incomeBand;
    const activeCommute = overrides?.commute ?? commuteThreshold;
    const activeType = overrides?.type ?? scenarioType;
    const activeCorridor = overrides?.corridor ?? transitCorridor;
    const activeLocality = overrides?.locality ?? housingLocality;
    const activeUnits = overrides?.units ?? housingUnits;
    const activeRent = overrides?.rent ?? housingRent;

    try {
      const payload: any = {
        scenario_type: activeType,
        occupation_key: activeOcc,
        income_band: activeInc,
        commute_threshold_minutes: activeCommute,
        work_days_per_month: 26,
      };

      if (activeType === 'transit') {
        payload.transit_params = {
          corridor_id: activeCorridor,
          description:
            activeCorridor === 'cmrl_c4'
              ? 'CMRL Phase II: Corridor 4 (Lighthouse ↔ Poonamallee Bypass)'
              : activeCorridor === 'cmrl_c3'
              ? 'CMRL Phase II: Corridor 3 (Madhavaram ↔ SIPCOT Siruseri)'
              : activeCorridor === 'cmrl_c5'
              ? 'CMRL Phase II: Corridor 5 (Madhavaram ↔ Sholinganallur)'
              : 'MTC High-Frequency Feeder: Ambattur ↔ Anna Nagar',
        };
      } else {
        payload.housing_params = {
          site_locality: activeLocality,
          units: activeUnits,
          avg_rent_monthly: activeRent,
          target_bhk: targetBhk,
          description: `Workforce Housing Supply: ${activeLocality}`,
        };
      }

      const res = await evaluateScenario(payload);
      setScenarioResult(res);
    } catch (err: any) {
      console.error('Scenario evaluation failed', err);
      setEvaluationError(err.message || 'Failed to evaluate scenario. Please try again.');
    } finally {
      setIsEvaluating(false);
    }
  };

  // Run initial evaluation on mount for instant visual load
  useEffect(() => {
    runEvaluation();
  }, []);

  // Quick Demo Presets
  const applyPreset = (presetKey: 'omr' | 'housing' | 'north') => {
    if (presetKey === 'omr') {
      setSelectedOccupation('nurse');
      setIncomeBand('median');
      setCommuteThreshold(45);
      setScenarioType('transit');
      setTransitCorridor('cmrl_c5');
      runEvaluation({
        occ: 'nurse',
        inc: 'median',
        commute: 45,
        type: 'transit',
        corridor: 'cmrl_c5',
      });
    } else if (presetKey === 'housing') {
      setSelectedOccupation('nurse');
      setIncomeBand('p25');
      setCommuteThreshold(45);
      setScenarioType('housing');
      setHousingLocality('ambattur');
      setHousingUnits(120);
      setHousingRent(13500);
      runEvaluation({
        occ: 'nurse',
        inc: 'p25',
        commute: 45,
        type: 'housing',
        locality: 'ambattur',
        units: 120,
        rent: 13500,
      });
    } else if (presetKey === 'north') {
      setSelectedOccupation('bus_driver');
      setIncomeBand('p25');
      setCommuteThreshold(45);
      setScenarioType('transit');
      setTransitCorridor('cmrl_c3');
      runEvaluation({
        occ: 'bus_driver',
        inc: 'p25',
        commute: 45,
        type: 'transit',
        corridor: 'cmrl_c3',
      });
    }
  };

  // Derived display values with dynamic backend fallback
  const current = scenarioResult?.current ?? {
    reachable_workers: 2150,
    median_commute_minutes: 42.0,
    affordable_listings: 35,
    monthly_transport_cost: 2860,
    monthly_rent_estimate: 7800,
    monthly_income: 24000,
    housing_burden_pct: 32.5,
    transport_burden_pct: 11.9,
    cash_burden_pct: 44.4,
  };

  const proposed = scenarioResult?.proposed ?? {
    reachable_workers: 2660,
    median_commute_minutes: 37.6,
    affordable_listings: 53,
    monthly_transport_cost: 2470,
    monthly_rent_estimate: 7800,
    monthly_income: 24000,
    housing_burden_pct: 32.5,
    transport_burden_pct: 10.3,
    cash_burden_pct: 42.8,
  };

  const change = scenarioResult?.change ?? {
    workers_reached: 510,
    commute_minutes_saved_per_trip: 4.4,
    affordable_listings_added: 18,
    monthly_transport_savings: 390,
    annual_transport_savings: 4680,
  };

  const workerImpact = scenarioResult?.worker_impact ?? {
    time_saved_per_trip_minutes: 4.4,
    work_days_per_month: 26,
    monthly_time_saved_hours: 3.81,
    annual_time_saved_hours: 45.76,
    monthly_money_saved: 390,
    annual_money_saved: 4680,
  };

  // Selected corridor display name
  const corridorDisplayNames: Record<string, string> = {
    cmrl_c4: 'Corridor 4 (Lighthouse ↔ Poonamallee Bypass)',
    cmrl_c3: 'Corridor 3 (Madhavaram ↔ SIPCOT)',
    cmrl_c5: 'Corridor 5 (Madhavaram ↔ Sholinganallur)',
    mtc_feeder: 'MTC Feeder (Ambattur ↔ Anna Nagar)',
  };

  return (
    <div className="max-w-[1240px] mx-auto space-y-8 animate-fadeIn pb-16">
      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* A. TIGHT PROFESSIONAL HERO BANNER                                   */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="bg-[#0B1F3A] text-white rounded-2xl p-6 sm:p-7 border border-[#162B4E] shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-2 max-w-3xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/10 text-[#F7C948] text-xs font-bold tracking-wide">
              <Compass className="w-3.5 h-3.5 text-[#F7C948]" />
              <span>RIVO CITY • SCENARIO PLANNER</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white leading-tight">
              Plan housing and transport around the people who keep Chennai moving.
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Test a transit or housing intervention and see which workers gain affordable access to jobs — and how much commute time and money they could save.
            </p>
          </div>

          <div className="shrink-0 bg-white/5 border border-white/10 rounded-xl p-3 sm:text-right text-xs">
            <div className="text-[#94A3B8] font-medium text-[11px]">Planning Model</div>
            <div className="text-[#F7C948] font-bold text-sm">PLFS + CMRL Phase-II</div>
            <div className="text-[10px] text-slate-400 mt-0.5">GCC 2025 Wards • 800m Buffers</div>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* B. SCENARIO SETUP & QUICK DEMO PRESETS                              */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl p-5 sm:p-6 border border-[#E2E8F0] shadow-xs space-y-5">
        {/* Presets Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#F1F5F9] pb-4">
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#102033]">
            <Sparkles className="w-4 h-4 text-[#1261D6]" />
            <span>Quick Demo Presets:</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => applyPreset('omr')}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#F8FAFC] hover:bg-[#EEF5FF] text-[#1261D6] border border-[#CBD5E1] transition-colors cursor-pointer flex items-center space-x-1.5"
            >
              <span>1. OMR Worker Access</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-white font-bold text-[#64748B]">CMRL C5</span>
            </button>
            <button
              type="button"
              onClick={() => applyPreset('housing')}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#F8FAFC] hover:bg-[#ECFDF5] text-[#059669] border border-[#CBD5E1] transition-colors cursor-pointer flex items-center space-x-1.5"
            >
              <span>2. Affordable Family Housing</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-white font-bold text-[#64748B]">Ambattur</span>
            </button>
            <button
              type="button"
              onClick={() => applyPreset('north')}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#F8FAFC] hover:bg-[#EEF5FF] text-[#1261D6] border border-[#CBD5E1] transition-colors cursor-pointer flex items-center space-x-1.5"
            >
              <span>3. North Chennai Access</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-white font-bold text-[#64748B]">CMRL C3</span>
            </button>
          </div>
        </div>

        {/* 2-Column Controls Area */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* LEFT COLUMN: SCENARIO PARAMETERS (6 cols) */}
          <div className="lg:col-span-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#102033] flex items-center space-x-1.5">
                <Users className="w-3.5 h-3.5 text-[#1261D6]" />
                <span>Worker Profile</span>
              </span>
              <span className="text-[10px] font-bold text-[#1261D6] bg-[#EEF5FF] px-2 py-0.5 rounded border border-[#CBD5E1]">
                Target Demographic
              </span>
            </div>

            {/* Essential Worker Selector */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[#607080]">Essential Worker</label>
              <select
                value={selectedOccupation}
                onChange={(e) => setSelectedOccupation(e.target.value)}
                className="w-full text-xs p-2.5 rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] text-[#102033] outline-none font-semibold focus:border-[#1261D6]"
              >
                {occupations.map((o) => (
                  <option key={o.occupation_key} value={o.occupation_key}>
                    {o.occupation_label}
                  </option>
                ))}
              </select>
            </div>

            {/* Income Level & Commute Threshold */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Income Percentile */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-[#607080]">
                  Income Level (PLFS 2025)
                </label>
                <div className="flex rounded-xl p-1 bg-[#F8FAFC] border border-[#CBD5E1]">
                  {(['p25', 'median', 'p75'] as const).map((band) => (
                    <button
                      key={band}
                      type="button"
                      onClick={() => setIncomeBand(band)}
                      className={`flex-1 py-1.5 text-xs font-semibold rounded-lg capitalize transition-colors cursor-pointer ${
                        incomeBand === band
                          ? 'bg-[#0B1F3A] text-white shadow-xs font-bold'
                          : 'text-[#607080] hover:text-[#102033]'
                      }`}
                    >
                      {band}
                    </button>
                  ))}
                </div>
              </div>

              {/* Maximum Acceptable Commute */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-[#607080]">
                  Commute Threshold
                </label>
                <div className="flex rounded-xl p-1 bg-[#F8FAFC] border border-[#CBD5E1]">
                  {([30, 45, 60] as const).map((mins) => (
                    <button
                      key={mins}
                      type="button"
                      onClick={() => setCommuteThreshold(mins)}
                      className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                        commuteThreshold === mins
                          ? 'bg-[#1261D6] text-white shadow-xs font-bold'
                          : 'text-[#607080] hover:text-[#102033]'
                      }`}
                    >
                      {mins} min
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: INTERVENTION (6 cols) */}
          <div className="lg:col-span-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#102033] flex items-center space-x-1.5">
                <Building2 className="w-3.5 h-3.5 text-[#059669]" />
                <span>Intervention Mechanism</span>
              </span>
              <span className="text-[10px] font-bold text-[#D97706] bg-[#FEF3C7] px-2 py-0.5 rounded border border-[#FDE68A]">
                Scenario Simulation
              </span>
            </div>

            {/* Mode Buttons */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setScenarioType('transit')}
                className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer flex items-center justify-center space-x-2 ${
                  scenarioType === 'transit'
                    ? 'bg-[#0B1F3A] text-white border-[#0B1F3A] shadow-xs'
                    : 'bg-[#F8FAFC] text-[#607080] border-[#E2E8F0] hover:bg-white'
                }`}
              >
                <Train className="w-3.5 h-3.5 text-[#F7C948]" />
                <span>Transit Expansion</span>
              </button>
              <button
                type="button"
                onClick={() => setScenarioType('housing')}
                className={`py-2 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer flex items-center justify-center space-x-2 ${
                  scenarioType === 'housing'
                    ? 'bg-[#0B1F3A] text-white border-[#0B1F3A] shadow-xs'
                    : 'bg-[#F8FAFC] text-[#607080] border-[#E2E8F0] hover:bg-white'
                }`}
              >
                <Home className="w-3.5 h-3.5 text-[#10B981]" />
                <span>Affordable Housing</span>
              </button>
            </div>

            {/* Sub-controls conditional on Intervention Mode */}
            {scenarioType === 'transit' ? (
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-[#607080]">
                  Project / Corridor (CMRL Phase II Official DPR)
                </label>
                <select
                  value={transitCorridor}
                  onChange={(e) => setTransitCorridor(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] text-[#102033] outline-none font-semibold focus:border-[#1261D6]"
                >
                  <option value="cmrl_c4">CMRL Corridor 4: Lighthouse ↔ Poonamallee Bypass (26.1 km, 27 stns)</option>
                  <option value="cmrl_c3">CMRL Corridor 3: Madhavaram ↔ SIPCOT Siruseri (45.4 km, 47 stns)</option>
                  <option value="cmrl_c5">CMRL Corridor 5: Madhavaram ↔ Sholinganallur (44.6 km, 45 stns)</option>
                  <option value="mtc_feeder">MTC High-Frequency Feeder: Ambattur Industrial Hub ↔ Anna Nagar</option>
                </select>
                <span className="text-[10px] text-[#64748B] block mt-1">
                  Status: Scenario simulation — under construction (targeted late 2028).
                </span>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="block text-xs font-semibold text-[#607080]">Housing Locality</label>
                    <select
                      value={housingLocality}
                      onChange={(e) => setHousingLocality(e.target.value)}
                      className="w-full text-xs p-2 rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] text-[#102033] font-semibold"
                    >
                      <option value="ambattur">Ambattur Industrial Hub</option>
                      <option value="porur">Porur / Poonamallee Node</option>
                      <option value="sholinganallur">Sholinganallur / OMR Sector</option>
                      <option value="madhavaram">North Chennai / Madhavaram</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="block text-xs font-semibold text-[#607080]">Affordable Rent Target</label>
                    <select
                      value={housingRent}
                      onChange={(e) => setHousingRent(Number(e.target.value))}
                      className="w-full text-xs p-2 rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] text-[#102033] font-semibold"
                    >
                      <option value={12000}>₹12,000 / month (Targeted P25)</option>
                      <option value={14000}>₹14,000 / month (Median Buffer)</option>
                      <option value={16000}>₹16,000 / month (Ceiling)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="flex items-center justify-between p-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <span className="text-[#607080]">Planned Units:</span>
                    <span className="font-bold text-[#102033]">{housingUnits} units</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                    <span className="text-[#607080]">Target Config:</span>
                    <span className="font-bold text-[#102033]">1–2 BHK Workforce</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ONE PRIMARY ACTION BUTTON */}
        <div className="pt-2 border-t border-[#F1F5F9]">
          <button
            type="button"
            onClick={() => runEvaluation()}
            disabled={isEvaluating}
            className="w-full min-h-[44px] py-2.5 px-6 rounded-xl bg-[#1261D6] hover:bg-[#0E4EB0] text-white text-sm font-bold shadow-sm transition-all flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
          >
            {isEvaluating ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Simulating Urban Spatial Reach...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-[#F7C948]" />
                <span>Evaluate Scenario</span>
              </>
            )}
          </button>
        </div>

        {evaluationError && (
          <div className="p-3 bg-red-50 text-red-700 text-xs rounded-xl border border-red-200">
            {evaluationError}
          </div>
        )}
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* C. SPATIAL IMPACT MAP (MANDATORY REAL LEAFLET MAP)                  */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-[#1261D6]" />
            <h2 className="text-base font-bold text-[#102033]">
              Spatial Accessibility Surface: Chennai Catchment Expansion
            </h2>
          </div>
          <span className="text-[11px] font-semibold text-[#D97706] bg-[#FEF3C7] px-2.5 py-0.5 rounded-full border border-[#FDE68A]">
            Scenario simulation — not current service
          </span>
        </div>

        <CityMap
          mapData={scenarioResult?.map_data}
          scenarioType={scenarioType}
          selectedCorridorName={corridorDisplayNames[transitCorridor]}
          selectedHousingName={housingLocality}
          currentWorkers={current.reachable_workers}
          proposedWorkers={proposed.reachable_workers}
          gainWorkers={change.workers_reached}
        />
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* D. MAIN RESULT — WORKER IMPACT SUMMARY CARDS                        */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-base font-bold text-[#102033]">
            Scenario Impact on Worker Accessibility
          </h2>
          <span className="text-xs text-[#607080] font-medium">
            Threshold: {commuteThreshold} min door-to-door
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Workers Gaining Access */}
          <div className="bg-white rounded-2xl p-5 border border-[#E2E8F0] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs text-[#607080] font-semibold uppercase tracking-wider">
              <span>Workers Gained</span>
              <Users className="w-4 h-4 text-[#059669]" />
            </div>
            <div className="text-3xl font-extrabold text-[#059669]">
              +{change.workers_reached.toLocaleString()}
            </div>
            <p className="text-[11px] text-[#607080]">
              Gain within {commuteThreshold}-minute threshold
            </p>
          </div>

          {/* Card 2: Commute Threshold */}
          <div className="bg-white rounded-2xl p-5 border border-[#E2E8F0] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs text-[#607080] font-semibold uppercase tracking-wider">
              <span>Target Commute</span>
              <Clock className="w-4 h-4 text-[#1261D6]" />
            </div>
            <div className="text-3xl font-extrabold text-[#102033]">
              {commuteThreshold} min
            </div>
            <p className="text-[11px] text-[#607080]">
              Acceptable door-to-door ceiling
            </p>
          </div>

          {/* Card 3: Projected Median Commute */}
          <div className="bg-white rounded-2xl p-5 border border-[#E2E8F0] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs text-[#607080] font-semibold uppercase tracking-wider">
              <span>Projected Commute</span>
              <TrendingUp className="w-4 h-4 text-[#06B6D4]" />
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-[#102033]">
                {proposed.median_commute_minutes} min
              </span>
              <span className="text-xs text-[#607080] line-through">
                {current.median_commute_minutes}m
              </span>
            </div>
            <p className="text-[11px] text-[#059669] font-semibold">
              ▼ {change.commute_minutes_saved_per_trip} min saved per one-way trip
            </p>
          </div>

          {/* Card 4: Additional Affordable Homes */}
          <div className="bg-white rounded-2xl p-5 border border-[#E2E8F0] shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs text-[#607080] font-semibold uppercase tracking-wider">
              <span>Affordable Homes</span>
              <Home className="w-4 h-4 text-[#1261D6]" />
            </div>
            <div className="text-3xl font-extrabold text-[#1261D6]">
              +{change.affordable_listings_added}
            </div>
            <p className="text-[11px] text-[#607080]">
              Units accessible within {commuteThreshold} min
            </p>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* E. BEFORE VS PROPOSED INTERVENTION (TWO COLUMNS)                    */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#F1F5F9] pb-3">
          <div>
            <h3 className="text-base font-bold text-[#102033]">
              Before vs Proposed Intervention
            </h3>
            <p className="text-xs text-[#607080]">
              Direct comparison of baseline accessibility versus simulated scenario impact
            </p>
          </div>
          <span className="text-[11px] font-semibold text-[#64748B] bg-[#F1F5F9] px-2.5 py-1 rounded-full">
            Illustrative scenario data — model simulation
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Column 1: CURRENT */}
          <div className="rounded-xl p-5 bg-[#F8FAFC] border border-[#E2E8F0] space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#CBD5E1]/60">
              <span className="text-xs font-bold uppercase tracking-wider text-[#607080]">
                Current Baseline
              </span>
              <span className="text-[10px] font-bold text-[#64748B] bg-white px-2 py-0.5 rounded border border-[#CBD5E1]">
                Baseline
              </span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#607080]">Workers within {commuteThreshold} min:</span>
                <span className="text-sm font-bold text-[#102033]">
                  {current.reachable_workers.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#607080]">Median commute:</span>
                <span className="text-sm font-bold text-[#102033]">
                  {current.median_commute_minutes} min
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#607080]">Affordable listings in catchment:</span>
                <span className="text-sm font-bold text-[#102033]">
                  {current.affordable_listings}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#607080]">Monthly transport cost:</span>
                <span className="text-sm font-bold text-[#102033]">
                  ₹{current.monthly_transport_cost.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Column 2: PROPOSED */}
          <div className="rounded-xl p-5 bg-[#EEF5FF] border border-[#CBD5E1] space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#CBD5E1]">
              <span className="text-xs font-bold uppercase tracking-wider text-[#1261D6]">
                Proposed Intervention
              </span>
              <span className="text-[10px] font-bold text-[#1261D6] bg-white px-2 py-0.5 rounded border border-[#CBD5E1]">
                Simulated
              </span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#102033] font-medium">Workers within {commuteThreshold} min:</span>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-bold text-[#102033]">
                    {proposed.reachable_workers.toLocaleString()}
                  </span>
                  <span className="text-[10px] font-bold text-[#059669] bg-[#ECFDF5] px-1.5 py-0.5 rounded border border-[#A7F3D0]">
                    +{change.workers_reached}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-[#102033] font-medium">Median commute:</span>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-bold text-[#102033]">
                    {proposed.median_commute_minutes} min
                  </span>
                  <span className="text-[10px] font-bold text-[#059669] bg-[#ECFDF5] px-1.5 py-0.5 rounded border border-[#A7F3D0]">
                    −{change.commute_minutes_saved_per_trip} min
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-[#102033] font-medium">Affordable listings in catchment:</span>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-bold text-[#102033]">
                    {proposed.affordable_listings}
                  </span>
                  <span className="text-[10px] font-bold text-[#1261D6] bg-white px-1.5 py-0.5 rounded border border-[#CBD5E1]">
                    +{change.affordable_listings_added}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-[#102033] font-medium">Monthly transport cost:</span>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-bold text-[#102033]">
                    ₹{proposed.monthly_transport_cost.toLocaleString()}
                  </span>
                  <span className="text-[10px] font-bold text-[#059669] bg-[#ECFDF5] px-1.5 py-0.5 rounded border border-[#A7F3D0]">
                    −₹{change.monthly_transport_savings}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* F & G. TIME AND MONEY SAVINGS & COMBINED HUMAN RESULT               */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Time Savings (6 cols) */}
        <div className="lg:col-span-6 bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-xs flex flex-col justify-between space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#102033] flex items-center space-x-1.5">
                <Clock className="w-4 h-4 text-[#06B6D4]" />
                <span>How Much Time Does a Worker Save?</span>
              </span>
              <span className="text-[10px] font-bold text-[#64748B] bg-[#F8FAFC] px-2 py-0.5 rounded border border-[#E2E8F0]">
                26 workdays/month
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 pt-2 text-center">
              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="text-[10px] text-[#607080]">CURRENT</div>
                <div className="text-base font-bold text-[#102033] mt-0.5">
                  {current.median_commute_minutes} min
                </div>
                <div className="text-[10px] text-[#64748B]">one way</div>
              </div>
              <div className="p-3 rounded-xl bg-[#EEF5FF] border border-[#CBD5E1]">
                <div className="text-[10px] text-[#1261D6]">PROPOSED</div>
                <div className="text-base font-bold text-[#1261D6] mt-0.5">
                  {proposed.median_commute_minutes} min
                </div>
                <div className="text-[10px] text-[#1261D6]">one way</div>
              </div>
              <div className="p-3 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0]">
                <div className="text-[10px] text-[#059669]">SAVED</div>
                <div className="text-base font-bold text-[#059669] mt-0.5">
                  {workerImpact.time_saved_per_trip_minutes} min
                </div>
                <div className="text-[10px] text-[#059669]">per trip</div>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-[#F0FDF4] border border-[#BBF7D0] flex items-center justify-between">
            <span className="text-xs font-bold text-[#166534]">
              ≈ {Math.round(workerImpact.annual_time_saved_hours)} hours returned to the worker every year
            </span>
            <span className="text-[11px] text-[#15803D] font-mono">
              ({workerImpact.monthly_time_saved_hours} hrs/mo)
            </span>
          </div>
        </div>

        {/* Money Savings (6 cols) */}
        <div className="lg:col-span-6 bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-xs flex flex-col justify-between space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#102033] flex items-center space-x-1.5">
                <Wallet className="w-4 h-4 text-[#059669]" />
                <span>How Much Money Could a Worker Save?</span>
              </span>
              <span className="text-[10px] font-bold text-[#64748B] bg-[#F8FAFC] px-2 py-0.5 rounded border border-[#E2E8F0]">
                Monthly pass model
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 pt-2 text-center">
              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="text-[10px] text-[#607080]">CURRENT</div>
                <div className="text-base font-bold text-[#102033] mt-0.5">
                  ₹{current.monthly_transport_cost.toLocaleString()}
                </div>
                <div className="text-[10px] text-[#64748B]">/ month</div>
              </div>
              <div className="p-3 rounded-xl bg-[#EEF5FF] border border-[#CBD5E1]">
                <div className="text-[10px] text-[#1261D6]">PROPOSED</div>
                <div className="text-base font-bold text-[#1261D6] mt-0.5">
                  ₹{proposed.monthly_transport_cost.toLocaleString()}
                </div>
                <div className="text-[10px] text-[#1261D6]">/ month</div>
              </div>
              <div className="p-3 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0]">
                <div className="text-[10px] text-[#059669]">SAVED</div>
                <div className="text-base font-bold text-[#059669] mt-0.5">
                  ₹{workerImpact.monthly_money_saved.toLocaleString()}
                </div>
                <div className="text-[10px] text-[#059669]">/ month</div>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] flex items-center justify-between">
            <span className="text-xs font-bold text-[#065F46]">
              ≈ ₹{workerImpact.annual_money_saved.toLocaleString()}/year lower transport cost
            </span>
            <span className="text-[11px] text-[#047857] font-mono">
              (₹{workerImpact.monthly_money_saved}/mo)
            </span>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* H. COMBINED HUMAN IMPACT BANNER ("WHAT CHANGES FOR ONE WORKER?")     */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="bg-[#0B1F3A] text-white rounded-2xl p-6 sm:p-7 border border-[#162B4E] shadow-sm">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-extrabold uppercase tracking-widest text-[#F7C948]">
              WHAT CHANGES FOR ONE WORKER?
            </span>
            <span className="text-[10px] font-mono text-slate-300">
              Target: {occupations.find((o) => o.occupation_key === selectedOccupation)?.occupation_label || 'Worker'}
            </span>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-2xl sm:text-3xl font-extrabold text-[#F7C948]">
                {workerImpact.annual_time_saved_hours} HOURS
              </div>
              <div className="text-xs text-slate-300 font-medium mt-1">
                saved every year
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-2xl sm:text-3xl font-extrabold text-[#38BDF8]">
                ₹{workerImpact.annual_money_saved.toLocaleString()}
              </div>
              <div className="text-xs text-slate-300 font-medium mt-1">
                transport savings / year
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-2xl sm:text-3xl font-extrabold text-white">
                {workerImpact.time_saved_per_trip_minutes} MIN
              </div>
              <div className="text-xs text-slate-300 font-medium mt-1">
                saved every single trip
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="text-2xl sm:text-3xl font-extrabold text-[#34D399]">
                {proposed.median_commute_minutes} MIN
              </div>
              <div className="text-xs text-slate-300 font-medium mt-1">
                new one-way median commute
              </div>
            </div>
          </div>

          <p className="text-xs sm:text-sm text-slate-300 pt-2 border-t border-white/10 italic">
            "That is time and money returned to the worker — not just a new station on a map."
          </p>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* I. SIMPLE PROFESSIONAL GRAPHS & HOUSING/TRANSIT CONNECTION          */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Graphs Container (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-xs space-y-6">
          <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#102033]">
              Scenario Metrics &amp; Bar Comparison
            </h3>
            <span className="text-[10px] text-[#607080] font-mono">
              Threshold: {commuteThreshold} min
            </span>
          </div>

          {/* Chart 1: Median Commute (Current vs Proposed) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-[#102033]">Median Commute (Minutes)</span>
              <span className="text-[#059669] font-bold">−{change.commute_minutes_saved_per_trip} min</span>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex items-center space-x-3">
                <span className="w-16 text-[#607080] shrink-0">Current</span>
                <div className="flex-1 bg-[#F1F5F9] h-6 rounded-md overflow-hidden flex items-center">
                  <div
                    className="bg-[#64748B] h-full flex items-center justify-end px-2 text-[11px] font-bold text-white transition-all duration-500"
                    style={{ width: `${Math.min(100, (current.median_commute_minutes / 60) * 100)}%` }}
                  >
                    {current.median_commute_minutes} min
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <span className="w-16 font-semibold text-[#1261D6] shrink-0">Proposed</span>
                <div className="flex-1 bg-[#F1F5F9] h-6 rounded-md overflow-hidden flex items-center">
                  <div
                    className="bg-[#1261D6] h-full flex items-center justify-end px-2 text-[11px] font-bold text-white transition-all duration-500"
                    style={{ width: `${Math.min(100, (proposed.median_commute_minutes / 60) * 100)}%` }}
                  >
                    {proposed.median_commute_minutes} min
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Chart 2: Monthly Transport Cost */}
          <div className="space-y-2 pt-2 border-t border-[#F8FAFC]">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-[#102033]">Monthly Transport Cost (₹)</span>
              <span className="text-[#059669] font-bold">−₹{change.monthly_transport_savings}/month</span>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex items-center space-x-3">
                <span className="w-16 text-[#607080] shrink-0">Current</span>
                <div className="flex-1 bg-[#F1F5F9] h-6 rounded-md overflow-hidden flex items-center">
                  <div
                    className="bg-[#64748B] h-full flex items-center justify-end px-2 text-[11px] font-bold text-white transition-all duration-500"
                    style={{ width: `${Math.min(100, (current.monthly_transport_cost / 3500) * 100)}%` }}
                  >
                    ₹{current.monthly_transport_cost.toLocaleString()}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <span className="w-16 font-semibold text-[#059669] shrink-0">Proposed</span>
                <div className="flex-1 bg-[#F1F5F9] h-6 rounded-md overflow-hidden flex items-center">
                  <div
                    className="bg-[#059669] h-full flex items-center justify-end px-2 text-[11px] font-bold text-white transition-all duration-500"
                    style={{ width: `${Math.min(100, (proposed.monthly_transport_cost / 3500) * 100)}%` }}
                  >
                    ₹{proposed.monthly_transport_cost.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Chart 3: Workers Gaining Access */}
          <div className="space-y-2 pt-2 border-t border-[#F8FAFC]">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-[#102033]">Workers Gaining Affordable Access</span>
              <span className="text-[#059669] font-bold">+{change.workers_reached.toLocaleString()} gained</span>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex items-center space-x-3">
                <span className="w-16 text-[#607080] shrink-0">Current</span>
                <div className="flex-1 bg-[#F1F5F9] h-6 rounded-md overflow-hidden flex items-center">
                  <div
                    className="bg-[#64748B] h-full flex items-center justify-end px-2 text-[11px] font-bold text-white transition-all duration-500"
                    style={{ width: `${Math.min(100, (current.reachable_workers / 5000) * 100)}%` }}
                  >
                    {current.reachable_workers.toLocaleString()}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <span className="w-16 font-semibold text-[#1261D6] shrink-0">Proposed</span>
                <div className="flex-1 bg-[#F1F5F9] h-6 rounded-md overflow-hidden flex items-center">
                  <div
                    className="bg-[#1261D6] h-full flex items-center justify-end px-2 text-[11px] font-bold text-white transition-all duration-500"
                    style={{ width: `${Math.min(100, (proposed.reachable_workers / 5000) * 100)}%` }}
                  >
                    {proposed.reachable_workers.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
            <p className="text-[11px] text-[#607080] pt-1">
              Workers counted within the selected {commuteThreshold}-minute commute threshold.
            </p>
          </div>
        </div>

        {/* Why Access Improves & Burden Breakdown (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Housing + Transit Connection: Why Access Improves */}
          <div className="bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-xs space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#102033] flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-[#059669]" />
              <span>Why Access Improves</span>
            </h3>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="text-[10px] font-bold text-[#607080]">HOUSING</div>
                <div className="text-xs font-extrabold text-[#102033] mt-1">
                  {current.affordable_listings} → {proposed.affordable_listings}
                </div>
                <div className="text-[10px] text-[#059669] font-semibold mt-0.5">
                  +{change.affordable_listings_added} homes
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="text-[10px] font-bold text-[#607080]">COMMUTE</div>
                <div className="text-xs font-extrabold text-[#102033] mt-1">
                  {current.median_commute_minutes} → {proposed.median_commute_minutes}m
                </div>
                <div className="text-[10px] text-[#059669] font-semibold mt-0.5">
                  −{change.commute_minutes_saved_per_trip} min
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="text-[10px] font-bold text-[#607080]">ACCESS</div>
                <div className="text-xs font-extrabold text-[#102033] mt-1">
                  {current.reachable_workers} → {proposed.reachable_workers}
                </div>
                <div className="text-[10px] text-[#059669] font-semibold mt-0.5">
                  +{change.workers_reached} reach
                </div>
              </div>
            </div>

            <p className="text-xs text-[#607080] leading-relaxed pt-1 border-t border-[#F1F5F9]">
              More suitable housing + better transit connectivity = more essential workers able to reach vital jobs without excessive commute tax.
            </p>
          </div>

          {/* Affordability Burden Percentages */}
          <div className="bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-xs space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#102033] flex items-center space-x-2">
              <Wallet className="w-4 h-4 text-[#1261D6]" />
              <span>Affordability Burden (% Income)</span>
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <div className="flex justify-between font-semibold mb-1">
                  <span className="text-[#607080]">Housing Burden (Rent / Income)</span>
                  <span className="text-[#102033]">
                    {current.housing_burden_pct}% → <span className="text-[#059669] font-bold">{proposed.housing_burden_pct}%</span>
                  </span>
                </div>
                <div className="w-full bg-[#F1F5F9] h-2 rounded-full overflow-hidden">
                  <div className="bg-[#1261D6] h-full" style={{ width: `${Math.min(100, proposed.housing_burden_pct * 2)}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between font-semibold mb-1">
                  <span className="text-[#607080]">Transport Burden (Cost / Income)</span>
                  <span className="text-[#102033]">
                    {current.transport_burden_pct}% → <span className="text-[#059669] font-bold">{proposed.transport_burden_pct}%</span>
                  </span>
                </div>
                <div className="w-full bg-[#F1F5F9] h-2 rounded-full overflow-hidden">
                  <div className="bg-[#06B6D4] h-full" style={{ width: `${Math.min(100, proposed.transport_burden_pct * 2)}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between font-semibold mb-1">
                  <span className="text-[#607080]">Combined Living Burden (Rent + Transport)</span>
                  <span className="text-[#102033]">
                    {current.cash_burden_pct}% → <span className="text-[#059669] font-bold">{proposed.cash_burden_pct}%</span>
                  </span>
                </div>
                <div className="w-full bg-[#F1F5F9] h-2 rounded-full overflow-hidden">
                  <div className="bg-[#059669] h-full" style={{ width: `${Math.min(100, proposed.cash_burden_pct * 1.5)}%` }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* J. DATA CONFIDENCE & COLLAPSIBLE METHODOLOGY                        */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      <div className="space-y-4">
        {/* Data Confidence Card */}
        <div className="bg-white rounded-2xl p-5 border border-[#E2E8F0] shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-[#059669]" />
              <span className="text-xs font-bold uppercase tracking-wider text-[#102033]">
                DATA CONFIDENCE: MEDIUM • ESTIMATED
              </span>
            </div>
            <p className="text-xs text-[#607080] leading-relaxed">
              Based on PLFS 2025 microdata income distribution, CMRL Phase-II Detailed Project Reports, CUMTA GTFS multi-modal network, and GCC 2025 ward demographics.
            </p>
          </div>

          <div className="shrink-0 bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl px-3 py-2 text-xs text-[#64748B] font-medium text-center">
            "Scenario results are estimates, not forecasts."
          </div>
        </div>

        {/* Collapsible Methodology Section */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-xs overflow-hidden">
          <button
            type="button"
            onClick={() => setShowMethodology(!showMethodology)}
            className="w-full p-4 flex items-center justify-between text-left text-xs font-bold uppercase tracking-wider text-[#102033] hover:bg-[#F8FAFC] transition-colors cursor-pointer"
          >
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-[#1261D6]" />
              <span>How RIVO Calculates Impact (Methodology &amp; Formulas)</span>
            </div>
            {showMethodology ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showMethodology && (
            <div className="p-5 pt-0 border-t border-[#F1F5F9] space-y-4 text-xs text-[#607080] animate-fadeIn">
              <ol className="list-decimal pl-5 space-y-2 leading-relaxed">
                <li>
                  <strong className="text-[#102033]">Identify Worker Income Group:</strong> Sampled from PLFS 2025 microdata (Tamil Nadu Urban) across P25, Median, and P75 percentile boundaries.
                </li>
                <li>
                  <strong className="text-[#102033]">Identify Employment Concentration:</strong> Geolocated healthcare clusters (SRMC, Kilpauk, Rajiv Gandhi GH), manufacturing corridors (Ambattur), and services hubs.
                </li>
                <li>
                  <strong className="text-[#102033]">Calculate Current Accessibility:</strong> Door-to-door transit time modeled using CUMTA GTFS baseline schedules with pedestrian access legs.
                </li>
                <li>
                  <strong className="text-[#102033]">Apply Proposed Intervention:</strong> CMRL Phase II rapid transit speeds (32 km/h commercial average vs 20 km/h street bus) with 800m standard pedestrian station catchments.
                </li>
                <li>
                  <strong className="text-[#102033]">Recalculate Reachable Workers:</strong> Grounded using GCC 2025 Ward Demographics (16,500 pop/km² CMA baseline × working age fraction × occupational labor share).
                </li>
                <li>
                  <strong className="text-[#102033]">Recalculate Commute Time:</strong> Speed differential applied over corridor distance to compute trip minute savings.
                </li>
                <li>
                  <strong className="text-[#102033]">Recalculate Transport Cost:</strong> Multi-modal transit pass consolidation savings evaluated against current mixed-mode travel.
                </li>
                <li>
                  <strong className="text-[#102033]">Compare Before vs After:</strong> Deterministic delta output for hours returned and money saved.
                </li>
              </ol>

              <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-1 font-mono text-[11px] text-[#475569]">
                <div>monthly_time_saved_hours = (current_commute - proposed_commute) × 2 × 26 / 60</div>
                <div>annual_time_saved_hours = monthly_time_saved_hours × 12</div>
                <div>monthly_transport_savings = current_transport_cost - proposed_transport_cost</div>
                <div>annual_transport_savings = monthly_transport_savings × 12</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
