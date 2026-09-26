import React, { useState, useEffect } from 'react';
import {
  MapPin,
  Briefcase,
  Users,
  Search,
  Sparkles,
  ChevronRight,
  ShieldCheck,
  Check,
  Building,
  School,
  HeartPulse,
  Pill,
} from 'lucide-react';
import { RecommendationRequest, WorkerOccupation } from '../../types/api';
import { fetchIncomeProfile } from '../../services/api';

const CHENNAI_WORKPLACES = [
  { label: 'Chennai Central / George Town', lat: 13.0827, lon: 80.2707 },
  { label: 'Tidel Park / OMR IT Corridor', lat: 12.9892, lon: 80.2494 },
  { label: 'Guindy Industrial Estate / SIDCO', lat: 13.0067, lon: 80.2023 },
  { label: 'Ambattur OT / Industrial Estate', lat: 13.1143, lon: 80.1548 },
  { label: 'Rajiv Gandhi Govt General Hospital', lat: 13.0815, lon: 80.2785 },
  { label: 'Sriperumbudur Manufacturing Hub', lat: 12.9675, lon: 79.9442 },
];

interface HomeSearchFormProps {
  occupations: WorkerOccupation[];
  onSearch: (request: RecommendationRequest) => void;
  isLoading: boolean;
}

export const HomeSearchForm: React.FC<HomeSearchFormProps> = ({
  occupations,
  onSearch,
  isLoading,
}) => {
  // Current active step/section to prevent congestion
  const [activeStep, setActiveStep] = useState<'workplace' | 'worker' | 'family'>('workplace');

  // Form State
  const [selectedWorkplace, setSelectedWorkplace] = useState(CHENNAI_WORKPLACES[0]);
  const [selectedOccupationKey, setSelectedOccupationKey] = useState<string>('nurse');
  const [incomeMonthly, setIncomeMonthly] = useState<number>(24000);
  const [maxRent, setMaxRent] = useState<number>(14000);
  const [bhk, setBhk] = useState<number | undefined>(2);
  const [maxCommuteMin, setMaxCommuteMin] = useState<number>(50);
  const [preferredModes, setPreferredModes] = useState<string[]>(['TRANSIT', 'TWO_WHEELER', 'WALK']);

  // Family Context State
  const [adults, setAdults] = useState<number>(2);
  const [children, setChildren] = useState<number>(1);
  const [childAgeBand, setChildAgeBand] = useState<string>('6-12');
  const [schoolMaxMin, setSchoolMaxMin] = useState<number>(20);
  const [hospitalMaxMin, setHospitalMaxMin] = useState<number>(25);
  const [pharmacyMaxMin, setPharmacyMaxMin] = useState<number>(10);
  const [requireFacilityThreshold, setRequireFacilityThreshold] = useState<boolean>(false);

  // Auto-fill income when occupation changes
  useEffect(() => {
    if (!selectedOccupationKey) return;
    fetchIncomeProfile(selectedOccupationKey).then((prof) => {
      if (prof?.income_median) {
        setIncomeMonthly(prof.income_median);
        // Standard affordability heuristic: 30% of income for rent
        const recommendedRent = Math.round(prof.income_median * 0.35 / 500) * 500;
        setMaxRent(recommendedRent);
      }
    });
  }, [selectedOccupationKey]);

  const toggleMode = (mode: string) => {
    if (preferredModes.includes(mode)) {
      if (preferredModes.length > 1) {
        setPreferredModes(preferredModes.filter((m) => m !== mode));
      }
    } else {
      setPreferredModes([...preferredModes, mode]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const req: RecommendationRequest = {
      max_rent_monthly: maxRent,
      bhk: bhk,
      workplace_lat: selectedWorkplace.lat,
      workplace_lon: selectedWorkplace.lon,
      workplace_label: selectedWorkplace.label,
      max_commute_minutes: maxCommuteMin,
      preferred_modes: preferredModes,
      worker: {
        occupation_key: selectedOccupationKey,
        household_income_monthly: incomeMonthly,
      },
      family: {
        adults,
        children,
        child_age_bands: children > 0 ? [childAgeBand] : [],
        school_max_minutes: schoolMaxMin,
        hospital_max_minutes: hospitalMaxMin,
        pharmacy_max_minutes: pharmacyMaxMin,
        require_within_threshold: requireFacilityThreshold,
      },
      search_radius_km: 18.0,
      work_days_per_month: 22,
      page: 1,
      page_size: 20,
    };
    onSearch(req);
  };

  return (
    <div className="bg-white rounded-2xl border border-[#EBE4DC] shadow-sm overflow-hidden">
      {/* Stepped Tab Header */}
      <div className="flex border-b border-[#EBE4DC] bg-[#FAF8F5]/60 text-xs font-medium">
        <button
          type="button"
          onClick={() => setActiveStep('workplace')}
          className={`flex-1 py-3 px-4 text-center transition-colors flex items-center justify-center space-x-2 border-b-2 ${
            activeStep === 'workplace'
              ? 'border-[#C25E38] text-[#C25E38] font-semibold bg-white'
              : 'border-transparent text-[#7A6F68] hover:text-[#2C2523]'
          }`}
        >
          <MapPin className="w-3.5 h-3.5" />
          <span>1. Workplace &amp; Travel</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveStep('worker')}
          className={`flex-1 py-3 px-4 text-center transition-colors flex items-center justify-center space-x-2 border-b-2 ${
            activeStep === 'worker'
              ? 'border-[#C25E38] text-[#C25E38] font-semibold bg-white'
              : 'border-transparent text-[#7A6F68] hover:text-[#2C2523]'
          }`}
        >
          <Briefcase className="w-3.5 h-3.5" />
          <span>2. Worker &amp; Budget</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveStep('family')}
          className={`flex-1 py-3 px-4 text-center transition-colors flex items-center justify-center space-x-2 border-b-2 ${
            activeStep === 'family'
              ? 'border-[#C25E38] text-[#C25E38] font-semibold bg-white'
              : 'border-transparent text-[#7A6F68] hover:text-[#2C2523]'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>3. Family Layer</span>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* STEP 1: Workplace & Commute */}
        {activeStep === 'workplace' && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <label className="block text-xs font-semibold text-[#5A504B] uppercase tracking-wider mb-2">
                Workplace Destination in Chennai
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {CHENNAI_WORKPLACES.map((wp) => {
                  const isSelected = selectedWorkplace.label === wp.label;
                  return (
                    <button
                      key={wp.label}
                      type="button"
                      onClick={() => setSelectedWorkplace(wp)}
                      className={`text-left p-3 rounded-xl border text-xs transition-all ${
                        isSelected
                          ? 'border-[#C25E38] bg-[#FDF7F4] text-[#2C2523] shadow-sm font-medium'
                          : 'border-[#EBE4DC] hover:border-[#D6CBC0] text-[#554C47]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="truncate">{wp.label}</span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-[#C25E38] shrink-0 ml-1" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-2">
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-semibold text-[#5A504B] uppercase tracking-wider">
                    Max Commute Time
                  </label>
                  <span className="text-xs font-bold text-[#C25E38] bg-[#FDF7F4] px-2 py-0.5 rounded-full border border-[#F3DFD5]">
                    {maxCommuteMin} mins
                  </span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="90"
                  step="5"
                  value={maxCommuteMin}
                  onChange={(e) => setMaxCommuteMin(Number(e.target.value))}
                  className="w-full accent-[#C25E38] cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-[#9E938D] mt-1">
                  <span>20m (close)</span>
                  <span>45m (standard)</span>
                  <span>90m (edge)</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#5A504B] uppercase tracking-wider mb-2">
                  Preferred Commute Modes
                </label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: 'TRANSIT', label: 'Metro / Bus' },
                    { id: 'TWO_WHEELER', label: '2-Wheeler' },
                    { id: 'WALK', label: 'Walk' },
                    { id: 'DRIVE', label: 'Car / Auto' },
                  ].map((mode) => {
                    const active = preferredModes.includes(mode.id);
                    return (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() => toggleMode(mode.id)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                          active
                            ? 'bg-[#2C2523] text-white border-[#2C2523]'
                            : 'bg-white text-[#6E645E] border-[#EBE4DC] hover:border-[#D6CBC0]'
                        }`}
                      >
                        {mode.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setActiveStep('worker')}
                className="flex items-center space-x-1.5 text-xs font-semibold text-[#C25E38] hover:text-[#943F20] px-4 py-2 rounded-lg bg-[#FAF5F0] border border-[#F0DFD5]"
              >
                <span>Next: Worker &amp; Budget</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Worker & Budget */}
        {activeStep === 'worker' && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <label className="block text-xs font-semibold text-[#5A504B] uppercase tracking-wider mb-2">
                Worker Occupation (PLFS 2025 Baseline)
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {occupations.map((occ) => {
                  const isSelected = selectedOccupationKey === occ.occupation_key;
                  return (
                    <button
                      key={occ.occupation_key}
                      type="button"
                      onClick={() => setSelectedOccupationKey(occ.occupation_key)}
                      className={`text-left p-3 rounded-xl border text-xs transition-all ${
                        isSelected
                          ? 'border-[#C25E38] bg-[#FDF7F4] text-[#2C2523] shadow-sm font-medium'
                          : 'border-[#EBE4DC] hover:border-[#D6CBC0] text-[#554C47]'
                      }`}
                    >
                      <div className="font-semibold truncate">{occ.occupation_label}</div>
                      <div className="text-[10px] text-[#8C7E75] truncate">{occ.nic_code}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-2">
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-semibold text-[#5A504B] uppercase tracking-wider">
                    Monthly Household Income
                  </label>
                  <span className="text-xs font-bold text-[#2C2523]">
                    ₹{incomeMonthly.toLocaleString()}
                  </span>
                </div>
                <input
                  type="range"
                  min="10000"
                  max="70000"
                  step="1000"
                  value={incomeMonthly}
                  onChange={(e) => setIncomeMonthly(Number(e.target.value))}
                  className="w-full accent-[#2C2523] cursor-pointer"
                />
                <span className="text-[10px] text-[#9E938D]">
                  Survey median for selected occupation in TN Urban
                </span>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="text-xs font-semibold text-[#5A504B] uppercase tracking-wider">
                    Hard Maximum Rent Budget
                  </label>
                  <span className="text-xs font-bold text-[#C25E38] bg-[#FDF7F4] px-2 py-0.5 rounded-full border border-[#F3DFD5]">
                    ₹{maxRent.toLocaleString()}/mo
                  </span>
                </div>
                <input
                  type="range"
                  min="5000"
                  max="35000"
                  step="500"
                  value={maxRent}
                  onChange={(e) => setMaxRent(Number(e.target.value))}
                  className="w-full accent-[#C25E38] cursor-pointer"
                />
                <span className="text-[10px] text-[#9E938D]">
                  Suggested: ~30-35% of income (₹{Math.round(incomeMonthly * 0.3).toLocaleString()})
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#5A504B] uppercase tracking-wider mb-2">
                Bedrooms (BHK)
              </label>
              <div className="flex space-x-2">
                {[
                  { val: undefined, label: 'Any BHK' },
                  { val: 1, label: '1 BHK' },
                  { val: 2, label: '2 BHK' },
                  { val: 3, label: '3 BHK' },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => setBhk(item.val)}
                    className={`px-4 py-2 rounded-xl text-xs font-medium border transition-colors ${
                      bhk === item.val
                        ? 'border-[#C25E38] bg-[#FDF7F4] text-[#C25E38] font-bold'
                        : 'border-[#EBE4DC] bg-white text-[#6E645E]'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-between pt-2">
              <button
                type="button"
                onClick={() => setActiveStep('workplace')}
                className="text-xs text-[#7A6F68] hover:text-[#2C2523]"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => setActiveStep('family')}
                className="flex items-center space-x-1.5 text-xs font-semibold text-[#C25E38] hover:text-[#943F20] px-4 py-2 rounded-lg bg-[#FAF5F0] border border-[#F0DFD5]"
              >
                <span>Next: Family Context</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: Family Accessibility Layer */}
        {activeStep === 'family' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#EDE4DB] text-xs text-[#6B615B] leading-relaxed">
              <span className="font-semibold text-[#2C2523]">Family Layer Context:</span>{' '}
              Evaluates proximity to schools (UDISE+), hospitals (Chennai Health OGD), and pharmacies so low rent doesn't mean an unlivable home for your household.
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-[#5A504B] uppercase tracking-wider mb-1.5">
                  Adults
                </label>
                <select
                  value={adults}
                  onChange={(e) => setAdults(Number(e.target.value))}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#EBE4DC] bg-white"
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>{n} adult{n > 1 ? 's' : ''}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#5A504B] uppercase tracking-wider mb-1.5">
                  Children
                </label>
                <select
                  value={children}
                  onChange={(e) => setChildren(Number(e.target.value))}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#EBE4DC] bg-white"
                >
                  {[0, 1, 2, 3, 4].map((n) => (
                    <option key={n} value={n}>{n} {n === 1 ? 'child' : 'children'}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#5A504B] uppercase tracking-wider mb-1.5">
                  Child Age Band
                </label>
                <select
                  value={childAgeBand}
                  disabled={children === 0}
                  onChange={(e) => setChildAgeBand(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#EBE4DC] bg-white disabled:opacity-50"
                >
                  <option value="0-5">0 - 5 yrs (Nursery / Anganwadi)</option>
                  <option value="6-12">6 - 12 yrs (Primary School)</option>
                  <option value="13-17">13 - 17 yrs (High School)</option>
                </select>
              </div>
            </div>

            {/* Facility Travel Time Limits */}
            <div className="space-y-4 pt-2">
              <h4 className="text-xs font-semibold text-[#5A504B] uppercase tracking-wider">
                Max Walking / Transit Time to Facilities
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-3 rounded-xl border border-[#EBE4DC] bg-[#FAF8F5]/50">
                  <div className="flex items-center space-x-1.5 text-xs font-medium text-[#2C2523] mb-1">
                    <School className="w-3.5 h-3.5 text-[#C25E38]" />
                    <span>School (UDISE+)</span>
                  </div>
                  <div className="text-xs font-bold text-[#C25E38] mb-1">{schoolMaxMin} mins</div>
                  <input
                    type="range"
                    min="5"
                    max="45"
                    step="5"
                    value={schoolMaxMin}
                    onChange={(e) => setSchoolMaxMin(Number(e.target.value))}
                    className="w-full accent-[#C25E38]"
                  />
                </div>

                <div className="p-3 rounded-xl border border-[#EBE4DC] bg-[#FAF8F5]/50">
                  <div className="flex items-center space-x-1.5 text-xs font-medium text-[#2C2523] mb-1">
                    <HeartPulse className="w-3.5 h-3.5 text-[#C25E38]" />
                    <span>Hospital (OGD)</span>
                  </div>
                  <div className="text-xs font-bold text-[#C25E38] mb-1">{hospitalMaxMin} mins</div>
                  <input
                    type="range"
                    min="5"
                    max="45"
                    step="5"
                    value={hospitalMaxMin}
                    onChange={(e) => setHospitalMaxMin(Number(e.target.value))}
                    className="w-full accent-[#C25E38]"
                  />
                </div>

                <div className="p-3 rounded-xl border border-[#EBE4DC] bg-[#FAF8F5]/50">
                  <div className="flex items-center space-x-1.5 text-xs font-medium text-[#2C2523] mb-1">
                    <Pill className="w-3.5 h-3.5 text-[#C25E38]" />
                    <span>Pharmacy (OSM)</span>
                  </div>
                  <div className="text-xs font-bold text-[#C25E38] mb-1">{pharmacyMaxMin} mins</div>
                  <input
                    type="range"
                    min="5"
                    max="30"
                    step="5"
                    value={pharmacyMaxMin}
                    onChange={(e) => setPharmacyMaxMin(Number(e.target.value))}
                    className="w-full accent-[#C25E38]"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2 pt-1">
              <input
                type="checkbox"
                id="strict_facilities"
                checked={requireFacilityThreshold}
                onChange={(e) => setRequireFacilityThreshold(e.target.checked)}
                className="w-4 h-4 accent-[#C25E38] rounded cursor-pointer"
              />
              <label htmlFor="strict_facilities" className="text-xs text-[#6B615B] cursor-pointer">
                Strict facility limit (reject homes exceeding facility limits instead of soft scoring)
              </label>
            </div>
          </div>
        )}

        {/* Global CTA button */}
        <div className="pt-4 border-t border-[#EBE4DC] flex items-center justify-between">
          <div className="text-xs text-[#8C7E75] hidden sm:block">
            Routes door-to-door against real Chennai transport data
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-[#C25E38] hover:bg-[#AB4E2A] text-white text-xs font-semibold shadow-sm transition-all flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
          >
            {isLoading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Running Spatial &amp; Route Pipeline...</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>Find Suitable Homes</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
