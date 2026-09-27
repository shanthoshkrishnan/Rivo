import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  SlidersHorizontal,
  Clock,
  School,
  HeartPulse,
  Pill,
  Users,
  Briefcase,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { RecommendationRequest, WorkerOccupation } from '../../types/api';
import { WorkplaceSearch, SelectedWorkplace } from './WorkplaceSearch';

interface HomeSearchFormProps {
  occupations: WorkerOccupation[];
  onSearch: (request: RecommendationRequest) => void;
  isLoading: boolean;
  initialWorkplace?: SelectedWorkplace | null;
}

const BHK_OPTIONS = [
  { label: 'Any', value: undefined },
  { label: '1 BHK', value: 1 },
  { label: '2 BHK', value: 2 },
  { label: '3 BHK', value: 3 },
  { label: '4+ BHK', value: 4 },
];

const RENT_RANGE_PRESETS = [
  { label: '₹8k – ₹15k', min: 8000, max: 15000 },
  { label: '₹12k – ₹20k', min: 12000, max: 20000 },
  { label: '₹15k – ₹28k', min: 15000, max: 28000 },
  { label: '₹25k – ₹50k', min: 25000, max: 50000 },
];

export const HomeSearchForm: React.FC<HomeSearchFormProps> = ({
  occupations,
  onSearch,
  isLoading,
  initialWorkplace = null,
}) => {
  // ── Core Inputs (Start UNSELECTED / EMPTY) ─────────────────────────────────
  const [selectedWorkplace, setSelectedWorkplace] = useState<SelectedWorkplace | null>(initialWorkplace);
  const [minRentStr, setMinRentStr] = useState<string>('');
  const [maxRentStr, setMaxRentStr] = useState<string>('');
  const [bhk, setBhk] = useState<number | undefined>(undefined);
  const [maxCommuteMin, setMaxCommuteMin] = useState<number>(45);

  // Validation error state
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ── Secondary Expandable Panel (Family & Optional Income) ─────────────────
  const [isFamilyOpen, setIsFamilyOpen] = useState<boolean>(false);
  const [adults, setAdults] = useState<number>(1);
  const [children, setChildren] = useState<number>(0);
  const [childAgeBands, setChildAgeBands] = useState<string[]>([]);
  const [schoolMaxMin, setSchoolMaxMin] = useState<number | undefined>(undefined);
  const [hospitalMaxMin, setHospitalMaxMin] = useState<number | undefined>(undefined);
  const [pharmacyMaxMin, setPharmacyMaxMin] = useState<number | undefined>(undefined);

  // Optional Affordability (Only sent if user specifies)
  const [occupationKey, setOccupationKey] = useState<string>('');
  const [incomeMonthlyStr, setIncomeMonthlyStr] = useState<string>('');

  const toggleAgeBand = (band: string) => {
    setChildAgeBands((prev) =>
      prev.includes(band) ? prev.filter((b) => b !== band) : [...prev, band]
    );
  };

  const handlePresetRent = (min: number, max: number) => {
    setMinRentStr(min.toString());
    setMaxRentStr(max.toString());
    setErrorMsg(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    // 1. Validate Workplace
    if (!selectedWorkplace || !selectedWorkplace.label) {
      setErrorMsg('Please search and select your workplace destination.');
      return;
    }

    // 2. Validate Rent
    const maxRent = Number(maxRentStr.trim());
    if (!maxRentStr || isNaN(maxRent) || maxRent <= 0) {
      setErrorMsg('Please specify your maximum monthly rent budget.');
      return;
    }

    const minRent = minRentStr.trim() ? Number(minRentStr.trim()) : undefined;
    if (minRent !== undefined && minRent > maxRent) {
      setErrorMsg('Minimum rent cannot exceed maximum rent.');
      return;
    }

    // 3. Compile Request Payload
    const req: RecommendationRequest = {
      workplace_lat: selectedWorkplace.lat,
      workplace_lon: selectedWorkplace.lon,
      workplace_label: selectedWorkplace.label,
      min_rent_monthly: minRent,
      max_rent_monthly: maxRent,
      bhk: bhk,
      max_commute_minutes: maxCommuteMin,
      // Note: Travel modes are evaluated in Results/Map view, default to all primary modes
      preferred_modes: ['TRANSIT', 'TWO_WHEELER', 'DRIVE', 'WALK'],
      search_radius_km: 20.0,
      page: 1,
      page_size: 25,
    };

    // Family layer (only include if configured)
    if (children > 0 || schoolMaxMin || hospitalMaxMin || pharmacyMaxMin || adults > 1) {
      req.family = {
        adults,
        children,
        child_age_bands: children > 0 ? childAgeBands : [],
        school_max_minutes: schoolMaxMin,
        hospital_max_minutes: hospitalMaxMin,
        pharmacy_max_minutes: pharmacyMaxMin,
      };
    }

    // Optional Worker/Income context
    const incomeNum = incomeMonthlyStr.trim() ? Number(incomeMonthlyStr.trim()) : undefined;
    if (occupationKey || (incomeNum && !isNaN(incomeNum) && incomeNum > 0)) {
      req.worker = {
        occupation_key: occupationKey || undefined,
        household_income_monthly: incomeNum && !isNaN(incomeNum) ? incomeNum : undefined,
      };
    }

    onSearch(req);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* ── ERROR ALERT BANNER ───────────────────────────────────────────── */}
      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center space-x-2.5 text-xs text-rose-700 animate-fadeIn">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ── 1. WHERE DO YOU WORK? (Real Location Search) ─────────────────── */}
      <div className="space-y-1.5">
        <label className="block text-xs font-bold uppercase tracking-wider text-[#06243A]">
          1. Where do you work?
        </label>
        <WorkplaceSearch
          selectedWorkplace={selectedWorkplace}
          onSelectWorkplace={(wp) => {
            setSelectedWorkplace(wp);
            setErrorMsg(null);
          }}
          disabled={isLoading}
        />
      </div>

      {/* ── 2. MONTHLY RENT RANGE [ Min ] — [ Max ] ───────────────────────── */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="block text-xs font-bold uppercase tracking-wider text-[#06243A]">
            2. Monthly rent budget
          </label>
          <div className="hidden sm:flex items-center space-x-1.5 text-xs">
            <span className="text-slate-400 text-[11px]">Quick ranges:</span>
            {RENT_RANGE_PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handlePresetRent(p.min, p.max)}
                className="px-2 py-0.5 rounded-md bg-slate-100 hover:bg-[#EEF5FF] hover:text-[#0878D1] text-[11px] font-semibold text-slate-700 transition-colors cursor-pointer"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-sm font-bold text-slate-400">
              ₹
            </span>
            <input
              type="number"
              min="0"
              step="1000"
              placeholder="Minimum (e.g. 8,000)"
              value={minRentStr}
              onChange={(e) => setMinRentStr(e.target.value)}
              className="w-full pl-8 pr-3 py-3 bg-white border border-[#CBD5E1] rounded-xl text-sm font-semibold text-[#06243A] placeholder:text-slate-400 focus:outline-none focus:border-[#0878D1] focus:ring-2 focus:ring-[#0878D1]/15 transition-all shadow-xs"
            />
          </div>

          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-sm font-bold text-slate-400">
              ₹
            </span>
            <input
              type="number"
              min="1000"
              step="1000"
              placeholder="Maximum (e.g. 18,000)"
              value={maxRentStr}
              onChange={(e) => {
                setMaxRentStr(e.target.value);
                setErrorMsg(null);
              }}
              className="w-full pl-8 pr-3 py-3 bg-white border border-[#CBD5E1] rounded-xl text-sm font-semibold text-[#06243A] placeholder:text-slate-400 focus:outline-none focus:border-[#0878D1] focus:ring-2 focus:ring-[#0878D1]/15 transition-all shadow-xs"
            />
          </div>
        </div>
      </div>

      {/* ── 3. BEDROOMS & 4. MAX COMMUTE (Clean 2-Column Split) ──────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-1">
        {/* Bedrooms Segmented Control */}
        <div className="space-y-1.5">
          <label className="block text-xs font-bold uppercase tracking-wider text-[#06243A]">
            3. Bedrooms (BHK)
          </label>
          <div className="flex rounded-xl bg-slate-100 p-1 border border-slate-200">
            {BHK_OPTIONS.map((opt) => (
              <button
                key={opt.label}
                type="button"
                onClick={() => setBhk(opt.value)}
                className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  bhk === opt.value
                    ? 'bg-white text-[#0878D1] shadow-xs'
                    : 'text-[#607080] hover:text-[#06243A]'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Max Commute Slider */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-bold uppercase tracking-wider text-[#06243A]">
              4. Max commute limit
            </label>
            <span className="text-xs font-bold text-[#0878D1] bg-[#F3F8FC] px-2.5 py-0.5 rounded-full border border-[#BFDBFE]">
              ≤ {maxCommuteMin} minutes
            </span>
          </div>
          <div className="pt-2">
            <input
              type="range"
              min="20"
              max="90"
              step="5"
              value={maxCommuteMin}
              onChange={(e) => setMaxCommuteMin(Number(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0878D1]"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-semibold">
              <span>20 min</span>
              <span>45 min</span>
              <span>60 min</span>
              <span>90 min</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── 5. OPTIONAL SECONDARY PANEL: + Family & Home Preferences ────── */}
      <div className="pt-2 border-t border-slate-100">
        <button
          type="button"
          onClick={() => setIsFamilyOpen(!isFamilyOpen)}
          className="w-full flex items-center justify-between py-2 text-xs font-bold text-[#0878D1] hover:text-[#06243A] transition-colors cursor-pointer"
        >
          <div className="flex items-center space-x-2">
            <Users className="w-4 h-4" />
            <span>
              {isFamilyOpen ? 'Hide Family & Affordability Options' : '+ Family & Home Preferences (Optional)'}
            </span>
          </div>
          {isFamilyOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {isFamilyOpen && (
          <div className="mt-3 p-5 rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-5 animate-fadeIn">
            {/* Household Members */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-[11px] font-bold text-slate-600 uppercase">Adults in Household</label>
                <div className="flex rounded-lg bg-white p-1 border border-slate-200">
                  {[1, 2, 3].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setAdults(n)}
                      className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer ${
                        adults === n ? 'bg-[#0878D1] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {n === 3 ? '3+' : n}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[11px] font-bold text-slate-600 uppercase">Children</label>
                <div className="flex rounded-lg bg-white p-1 border border-slate-200">
                  {[0, 1, 2, 3].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setChildren(n)}
                      className={`flex-1 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer ${
                        children === n ? 'bg-[#0878D1] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {n === 3 ? '3+' : n}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Child Age Bands (Only displayed if children > 0) */}
            {children > 0 && (
              <div className="space-y-1.5 animate-fadeIn">
                <label className="block text-[11px] font-bold text-slate-600 uppercase">Child Age Bands</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: '0-5', label: '0–5 yrs (Pre-school)' },
                    { id: '6-12', label: '6–12 yrs (Primary School)' },
                    { id: '13-18', label: '13–18 yrs (Secondary / High)' },
                  ].map((band) => (
                    <button
                      key={band.id}
                      type="button"
                      onClick={() => toggleAgeBand(band.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                        childAgeBands.includes(band.id)
                          ? 'bg-[#0878D1] text-white shadow-xs'
                          : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      {band.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Nearby Essentials Thresholds */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-slate-200">
              <div className="space-y-1">
                <div className="flex items-center space-x-1.5 text-[11px] font-bold text-slate-600 uppercase">
                  <School className="w-3.5 h-3.5 text-[#0878D1]" />
                  <span>School Proximity</span>
                </div>
                <select
                  value={schoolMaxMin ?? ''}
                  onChange={(e) => setSchoolMaxMin(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-[#06243A] focus:outline-none focus:border-[#0878D1]"
                >
                  <option value="">Any distance</option>
                  <option value="10">≤ 10 min</option>
                  <option value="15">≤ 15 min</option>
                  <option value="20">≤ 20 min</option>
                </select>
              </div>

              <div className="space-y-1">
                <div className="flex items-center space-x-1.5 text-[11px] font-bold text-slate-600 uppercase">
                  <HeartPulse className="w-3.5 h-3.5 text-[#EF4444]" />
                  <span>Hospital Proximity</span>
                </div>
                <select
                  value={hospitalMaxMin ?? ''}
                  onChange={(e) => setHospitalMaxMin(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-[#06243A] focus:outline-none focus:border-[#0878D1]"
                >
                  <option value="">Any distance</option>
                  <option value="10">≤ 10 min</option>
                  <option value="15">≤ 15 min</option>
                  <option value="20">≤ 20 min</option>
                </select>
              </div>

              <div className="space-y-1">
                <div className="flex items-center space-x-1.5 text-[11px] font-bold text-slate-600 uppercase">
                  <Pill className="w-3.5 h-3.5 text-[#8B5CF6]" />
                  <span>Pharmacy</span>
                </div>
                <select
                  value={pharmacyMaxMin ?? ''}
                  onChange={(e) => setPharmacyMaxMin(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-[#06243A] focus:outline-none focus:border-[#0878D1]"
                >
                  <option value="">Any distance</option>
                  <option value="5">≤ 5 min</option>
                  <option value="10">≤ 10 min</option>
                  <option value="15">≤ 15 min</option>
                </select>
              </div>
            </div>

            {/* Optional Worker Affordability (No forced defaults) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-200">
              <div className="space-y-1">
                <label className="block text-[11px] font-bold text-slate-600 uppercase">
                  Occupation (Optional PLFS Wage Benchmark)
                </label>
                <select
                  value={occupationKey}
                  onChange={(e) => setOccupationKey(e.target.value)}
                  className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs font-medium text-[#06243A] focus:outline-none focus:border-[#0878D1]"
                >
                  <option value="">None (Search by rent only)</option>
                  {occupations.map((occ) => (
                    <option key={occ.occupation_key} value={occ.occupation_key}>
                      {occ.occupation_label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-[11px] font-bold text-slate-600 uppercase">
                  Monthly Household Income (Optional)
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-xs text-slate-400 font-bold">
                    ₹
                  </span>
                  <input
                    type="number"
                    min="1000"
                    step="1000"
                    placeholder="e.g. 30,000"
                    value={incomeMonthlyStr}
                    onChange={(e) => setIncomeMonthlyStr(e.target.value)}
                    className="w-full pl-6 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium text-[#06243A] placeholder:text-slate-400 focus:outline-none focus:border-[#0878D1]"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── 6. SUBMIT BUTTON (Large Primary Action) ───────────────────────── */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-4 rounded-xl bg-[#0878D1] hover:bg-[#0764B0] text-white font-extrabold text-base flex items-center justify-center space-x-2 transition-all duration-200 shadow-lg shadow-[#0878D1]/25 hover:shadow-[#0878D1]/40 hover:-translate-y-0.5 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <div className="flex items-center space-x-2">
              <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Calculating Optimal Homes...</span>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <span>Find Suitable Homes</span>
              <ArrowRight className="w-5 h-5 text-[#F5C542]" />
            </div>
          )}
        </button>
      </div>

      {/* Trust & Guarantee footnote */}
      <div className="text-center text-[11px] text-slate-400 font-medium">
        RIVO compares rent, door-to-door transit time, monthly travel fares, and nearby family essentials.
      </div>
    </form>
  );
};
