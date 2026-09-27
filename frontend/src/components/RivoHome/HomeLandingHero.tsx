import React, { useState } from 'react';
import {
  Compass,
  ArrowRight,
  TrendingDown,
  Clock,
  HeartPulse,
  Building2,
  Users,
  Search,
  CheckCircle2,
  Sparkles,
  MapPin,
  Navigation,
  School,
  Pill,
  Train,
  Layers,
  Fuel,
  ShieldCheck,
  Plus,
  ArrowDown,
} from 'lucide-react';

interface HomeLandingHeroProps {
  onFocusSearch: () => void;
  onSelectQuickWorkplace: (wp: { label: string; lat: number; lon: number; area: string }) => void;
  onSwitchToCityTab?: () => void;
}

export const HomeLandingHero: React.FC<HomeLandingHeroProps> = ({
  onFocusSearch,
  onSelectQuickWorkplace,
  onSwitchToCityTab,
}) => {
  // Interactive Selector State: What Matters to You?
  const [activePillar, setActivePillar] = useState<'housing' | 'commute' | 'transport' | 'family'>('housing');

  return (
    <div className="space-y-20 sm:space-y-28 pt-6 pb-12 animate-fadeIn">
      {/* 04: WHY RIVO IS DIFFERENT (Horizontal Diagram - Understand in 5 seconds) */}
      <section className="space-y-8">
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#EEF5FF] text-[#1261D6] text-xs font-bold tracking-wide">
            <Sparkles className="w-3.5 h-3.5 text-[#F7C948]" />
            <span>THE RIVO FORMULA</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#102033]">
            Why RIVO Is Different
          </h2>
          <p className="text-base text-[#607080] leading-relaxed">
            Conventional property portals only show asking rent. RIVO computes your complete door-to-door living burden.
          </p>
        </div>

        {/* Visual Horizontal Equation Diagram */}
        <div className="bg-[#F4F8FC] rounded-2xl p-6 sm:p-10 border border-[#E2E8F0]">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 relative">
            {/* Component 1: Rent */}
            <div className="bg-white rounded-xl p-5 border border-[#E2E8F0] shadow-xs text-center space-y-2">
              <div className="w-10 h-10 rounded-xl bg-[#EEF5FF] text-[#1261D6] flex items-center justify-center mx-auto">
                <Building2 className="w-5 h-5" />
              </div>
              <div className="text-sm font-bold text-[#102033] uppercase tracking-wider">01. Rent</div>
              <p className="text-xs text-[#607080]">Monthly asking lease calibrated to income ceiling</p>
            </div>

            {/* Component 2: Transport */}
            <div className="bg-white rounded-xl p-5 border border-[#E2E8F0] shadow-xs text-center space-y-2">
              <div className="w-10 h-10 rounded-xl bg-[#EEF5FF] text-[#1261D6] flex items-center justify-center mx-auto">
                <Navigation className="w-5 h-5" />
              </div>
              <div className="text-sm font-bold text-[#102033] uppercase tracking-wider">02. Transport</div>
              <p className="text-xs text-[#607080]">MTC bus fares, CMRL metro passes, or two-wheeler fuel</p>
            </div>

            {/* Component 3: Commute Time */}
            <div className="bg-white rounded-xl p-5 border border-[#E2E8F0] shadow-xs text-center space-y-2">
              <div className="w-10 h-10 rounded-xl bg-[#EEF5FF] text-[#1261D6] flex items-center justify-center mx-auto">
                <Clock className="w-5 h-5" />
              </div>
              <div className="text-sm font-bold text-[#102033] uppercase tracking-wider">03. Time Tax</div>
              <p className="text-xs text-[#607080]">True door-to-door transit minutes and monthly hours lost</p>
            </div>

            {/* Component 4: Family */}
            <div className="bg-white rounded-xl p-5 border border-[#E2E8F0] shadow-xs text-center space-y-2">
              <div className="w-10 h-10 rounded-xl bg-[#EEF5FF] text-[#1261D6] flex items-center justify-center mx-auto">
                <HeartPulse className="w-5 h-5" />
              </div>
              <div className="text-sm font-bold text-[#102033] uppercase tracking-wider">04. Family Fit</div>
              <p className="text-xs text-[#607080]">Verified walking reach to UDISE+ schools and clinics</p>
            </div>
          </div>

          {/* Outcome Banner */}
          <div className="mt-6 pt-6 border-t border-[#CBD5E1] flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-lg bg-[#0B1F3A] text-white flex items-center justify-center shrink-0 font-bold">
                =
              </div>
              <div>
                <span className="text-base font-extrabold text-[#102033] block">
                  Real Door-to-Door Cost of Living
                </span>
                <span className="text-xs text-[#607080]">
                  One transparent, explainable decision benchmark — grounded in PLFS 2025 and CUMTA GTFS
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={onFocusSearch}
              className="px-5 py-2.5 rounded-xl bg-[#1261D6] hover:bg-[#0E4EB0] text-white text-xs font-bold transition-colors cursor-pointer shrink-0"
            >
              Test with your workplace →
            </button>
          </div>
        </div>
      </section>

      {/* 05: LARGE IMAGE + COST OF LIVING STORY (50/50 Split) */}
      <section className="bg-white rounded-2xl border border-[#E2E8F0] overflow-hidden shadow-xs">
        <div className="grid grid-cols-1 lg:grid-cols-12 items-stretch">
          {/* Left Column: High-Resolution Chennai Residential Imagery */}
          <div className="lg:col-span-6 relative min-h-[380px] lg:min-h-[480px] overflow-hidden bg-[#F4F8FC]">
            <img
              src="/properties/chennai_interior_1.jpg"
              alt="Chennai Residential Life"
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0B1F3A]/90 via-[#0B1F3A]/30 to-transparent" />
            <div className="absolute bottom-6 left-6 right-6 text-white space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-[#1261D6] text-white">
                Transit Catchment Tradeoff
              </span>
              <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                Anna Nagar, Porur &amp; Velachery Residential Corridors
              </h3>
              <p className="text-xs text-slate-200 leading-relaxed max-w-md">
                Moving 8 km further away to save ₹3,000 on rent often consumes ₹4,200 in monthly fuel and adds 40 hours of gridlock.
              </p>
            </div>
          </div>

          {/* Right Column: Transparent Cost Breakdown */}
          <div className="lg:col-span-6 p-6 sm:p-10 flex flex-col justify-between space-y-6 bg-[#F8FAFC]">
            <div className="space-y-3">
              <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded bg-white border border-[#E2E8F0] text-[#1261D6] text-xs font-bold uppercase tracking-wider">
                <span>REPRESENTATIVE EXAMPLE</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#102033] leading-snug">
                Rent is only part of the cost of living.
              </h2>
              <p className="text-sm text-[#607080] leading-relaxed">
                RIVO combines housing, daily transit, commute time, and neighborhood family access into one transparent decision so you never end up house-poor.
              </p>
            </div>

            {/* Scenario Breakdown Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-4 rounded-xl bg-white border border-[#E2E8F0] text-center shadow-xs">
                <div className="text-[10px] font-bold text-[#607080] uppercase">Housing</div>
                <div className="text-xl font-extrabold text-[#102033] mt-1">₹18,000</div>
                <div className="text-[10px] text-[#607080]">per month</div>
              </div>

              <div className="p-4 rounded-xl bg-white border border-[#E2E8F0] text-center shadow-xs">
                <div className="text-[10px] font-bold text-[#607080] uppercase">Transport</div>
                <div className="text-xl font-extrabold text-[#1261D6] mt-1">₹2,100</div>
                <div className="text-[10px] text-[#607080]">monthly travel</div>
              </div>

              <div className="p-4 rounded-xl bg-white border border-[#E2E8F0] text-center shadow-xs">
                <div className="text-[10px] font-bold text-[#607080] uppercase">Time Tax</div>
                <div className="text-xl font-extrabold text-[#0B1F3A] mt-1">24 hrs</div>
                <div className="text-[10px] text-[#607080]">transit / month</div>
              </div>

              <div className="p-4 rounded-xl bg-white border border-[#E2E8F0] text-center shadow-xs">
                <div className="text-[10px] font-bold text-[#607080] uppercase">Family Access</div>
                <div className="text-xl font-extrabold text-[#10B981] mt-1">≤ 15 min</div>
                <div className="text-[10px] text-[#607080]">school &amp; clinic</div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white border border-[#E2E8F0] flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2.5">
                <CheckCircle2 className="w-5 h-5 text-[#10B981] shrink-0" />
                <span className="text-[#102033] font-medium">
                  <b>PLFS Benchmark:</b> Defensible 32% Combined Cash Burden for Essential Workers
                </span>
              </div>
              <span className="text-[10px] font-bold bg-[#EEF5FF] text-[#1261D6] px-2 py-0.5 rounded border border-[#CBD5E1] shrink-0 hidden sm:inline-block">
                Representative Example
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 06: HOW RIVO WORKS (01–04 Wide Step Grid) */}
      <section className="space-y-8">
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#EEF5FF] text-[#1261D6] text-xs font-bold tracking-wide">
            <Compass className="w-3.5 h-3.5 text-[#1261D6]" />
            <span>HOW RIVO WORKS</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#102033]">
            A Real Search Engine for Chennai Living
          </h2>
          <p className="text-base text-[#607080] leading-relaxed">
            Four defensible pillars connecting your workplace, income profile, daily commute, and family needs.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[
            {
              step: '01',
              title: 'WHERE YOU WORK',
              desc: 'Select your exact workplace. RIVO anchors door-to-door transit modeling to your desk.',
              icon: Building2,
            },
            {
              step: '02',
              title: 'WHAT YOU CAN SPEND',
              desc: 'Select your salary or occupation. RIVO calibrates a defensible 30-35% rent ceiling using PLFS 2025.',
              icon: TrendingDown,
            },
            {
              step: '03',
              title: 'HOW YOU TRAVEL',
              desc: 'Set your commute target. RIVO models MTC buses, CMRL metro corridors, rail, and walking.',
              icon: Clock,
            },
            {
              step: '04',
              title: 'WHAT YOUR FAMILY NEEDS',
              desc: 'Ensure verified walking reach to UDISE+ state/aided schools and TN Health hospitals.',
              icon: HeartPulse,
            },
          ].map((item) => (
            <div
              key={item.step}
              className="bg-white rounded-xl p-6 border border-[#E2E8F0] shadow-xs relative overflow-hidden group hover:border-[#1261D6]/40 hover:shadow-md transition-all duration-200"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-3xl font-extrabold text-[#CBD5E1] group-hover:text-[#1261D6] transition-colors">
                  {item.step}
                </span>
                <div className="w-10 h-10 rounded-xl bg-[#F4F8FC] text-[#1261D6] flex items-center justify-center border border-[#E2E8F0]">
                  <item.icon className="w-5 h-5" />
                </div>
              </div>
              <h3 className="text-sm font-extrabold text-[#102033] tracking-wide mb-2 uppercase">
                {item.title}
              </h3>
              <p className="text-xs text-[#607080] leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 07: INTERACTIVE SELECTOR: WHAT MATTERS MOST TO YOU? */}
      <section className="bg-[#F4F8FC] rounded-2xl p-6 sm:p-10 border border-[#E2E8F0] space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white border border-[#E2E8F0] text-[#1261D6] text-xs font-bold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-[#F7C948]" />
            <span>Interactive Intelligence</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#102033]">
            What Matters Most to You?
          </h2>
          <p className="text-xs sm:text-sm text-[#607080]">
            Click any dimension to see how RIVO converts complex urban data into practical home-finding decisions.
          </p>
        </div>

        {/* Tab Buttons (Royal Blue Selected with Yellow Indicator) */}
        <div className="flex flex-wrap items-center justify-center gap-2 max-w-xl mx-auto">
          {[
            { id: 'housing', label: 'Housing Budget', icon: Building2 },
            { id: 'commute', label: 'Commute Duration', icon: Clock },
            { id: 'transport', label: 'Monthly Travel Cost', icon: Navigation },
            { id: 'family', label: 'Family Amenities', icon: HeartPulse },
          ].map((tab) => {
            const isSelected = activePillar === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActivePillar(tab.id as any)}
                className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center space-x-2 cursor-pointer ${
                  isSelected
                    ? 'bg-[#1261D6] text-white shadow-sm'
                    : 'bg-white text-[#607080] hover:text-[#102033] border border-[#CBD5E1]'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-[#F7C948]" />}
              </button>
            );
          })}
        </div>

        {/* Interactive Explanation Panel */}
        <div className="bg-white rounded-xl p-6 sm:p-8 border border-[#E2E8F0] shadow-xs max-w-4xl mx-auto transition-all duration-200">
          {activePillar === 'housing' && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-9 h-9 rounded-xl bg-[#EEF5FF] text-[#1261D6] flex items-center justify-center">
                    <Building2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-[#102033]">Defensible Rent-to-Income Benchmarks</h3>
                    <p className="text-xs text-[#607080]">MoSPI PLFS 2025 Labor Microdata Calibration</p>
                  </div>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-1 rounded bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]">
                  30-35% Housing Ceiling
                </span>
              </div>
              <p className="text-xs sm:text-sm text-[#607080] leading-relaxed">
                Conventional real estate websites push you toward the highest rent you can stretch to pay. RIVO calculates the 25th percentile, median, and 75th percentile wages for frontline workers (nurses, drivers, teachers, technicians) to prevent housing distress.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">Hard Ceiling:</span>
                  <span className="font-bold text-[#102033]">Rent ≤ 35% of Salary</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">Worker Profiles:</span>
                  <span className="font-bold text-[#102033]">12 Essential Chennai Occupations</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">ML Rent Gate:</span>
                  <span className="font-bold text-[#102033]">50+ Verified Data Observations</span>
                </div>
              </div>
            </div>
          )}

          {activePillar === 'commute' && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-9 h-9 rounded-xl bg-[#EEF5FF] text-[#1261D6] flex items-center justify-center">
                    <Clock className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-[#102033]">Door-to-Door Multimodal Transit</h3>
                    <p className="text-xs text-[#607080]">CUMTA GTFS Bus &amp; Metro Routing Engine</p>
                  </div>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-1 rounded bg-[#EEF5FF] text-[#1261D6] border border-[#CBD5E1]">
                  Realistic Peak Minutes
                </span>
              </div>
              <p className="text-xs sm:text-sm text-[#607080] leading-relaxed">
                As-the-crow-flies distance is meaningless in Chennai traffic. RIVO routes actual door-to-door transit combining MTC buses, CMRL metro corridors, suburban trains, and walking transfers, accounting for realistic peak headway delays.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">MTC Feeder Buses:</span>
                  <span className="font-bold text-[#102033]">Live Timetables &amp; Stops</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">CMRL Metro Lines:</span>
                  <span className="font-bold text-[#102033]">Phase I &amp; Phase II Stations</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">Travel Options:</span>
                  <span className="font-bold text-[#102033]">Transit, Two-Wheeler &amp; Walk</span>
                </div>
              </div>
            </div>
          )}

          {activePillar === 'transport' && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-9 h-9 rounded-xl bg-[#EEF5FF] text-[#1261D6] flex items-center justify-center">
                    <Fuel className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-[#102033]">Total Out-of-Pocket Mobility Outflow</h3>
                    <p className="text-xs text-[#607080]">Official MTC Stages &amp; Daily Fuel Benchmarks</p>
                  </div>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-1 rounded bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]">
                  Rent + Travel Passes
                </span>
              </div>
              <p className="text-xs sm:text-sm text-[#607080] leading-relaxed">
                A home that looks cheap on a portal often turns out expensive when you add ₹120/day in two-wheeler fuel or ₹1,500 in monthly suburban train and feeder bus fares. RIVO models true monthly cash outflow for 22 work days.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">MTC Bus Fares:</span>
                  <span className="font-bold text-[#102033]">Stage-by-Stage Tariffs</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">Petrol Two-Wheeler:</span>
                  <span className="font-bold text-[#102033]">₹2.80 / km calibrated</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">Total Cash Burden:</span>
                  <span className="font-bold text-[#102033]">Rent + Maintenance + Travel</span>
                </div>
              </div>
            </div>
          )}

          {activePillar === 'family' && (
            <div className="space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-9 h-9 rounded-xl bg-[#EEF5FF] text-[#1261D6] flex items-center justify-center">
                    <HeartPulse className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-[#102033]">Verified Social Infrastructure</h3>
                    <p className="text-xs text-[#607080]">UDISE+ Schools &amp; TN Health OGD Hospitals</p>
                  </div>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-1 rounded bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]">
                  10–25 Min Isochrones
                </span>
              </div>
              <p className="text-xs sm:text-sm text-[#607080] leading-relaxed">
                A rental property without a nearby school or emergency healthcare puts severe stress on working families. RIVO indexes all government and aided schools, public dispensaries, hospitals, and licensed pharmacies within walkable pedestrian buffers.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">Schools (UDISE+):</span>
                  <span className="font-bold text-[#102033]">≤ 20 min walk target</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">Hospitals &amp; Clinics:</span>
                  <span className="font-bold text-[#102033]">≤ 25 min transit target</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
                  <span className="text-[#607080] block text-[11px]">Pharmacies:</span>
                  <span className="font-bold text-[#102033]">≤ 10 min walk threshold</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 08: CHENNAI HOUSING DISCOVERY (3-Column Asymmetric Gallery) */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-3">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded bg-[#EEF5FF] text-[#1261D6] text-xs font-bold uppercase tracking-wider">
              <span>Editorial Housing Showcase</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#102033] mt-2">
              Homes That Fit Real Life Across Chennai
            </h2>
            <p className="text-xs sm:text-sm text-[#607080] mt-1">
              Curated neighborhood styles across primary transit corridors and employment nodes.
            </p>
          </div>
          <button
            type="button"
            onClick={onFocusSearch}
            className="text-xs font-bold text-[#1261D6] hover:text-[#0E4EB0] inline-flex items-center space-x-1 cursor-pointer"
          >
            <span>Search homes now</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Panel 1 */}
          <div className="group rounded-2xl overflow-hidden bg-white border border-[#E2E8F0] shadow-xs flex flex-col hover:shadow-lg transition-all duration-300">
            <div className="relative h-64 overflow-hidden bg-[#F4F8FC]">
              <img
                src="/properties/chennai_apartment_1.jpg"
                alt="Urban Chennai Apartments"
                className="w-full h-full object-cover group-hover:scale-103 transition-transform duration-500"
              />
              <div className="absolute top-3 left-3">
                <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-[#0B1F3A]/85 text-white backdrop-blur-xs">
                  Urban Transit Hubs
                </span>
              </div>
            </div>
            <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
              <div>
                <h3 className="text-base font-bold text-[#102033]">
                  Connected Urban Living
                </h3>
                <p className="text-xs text-[#607080] mt-1 leading-relaxed">
                  Apartments along Metro Corridor 1 &amp; 2 with fast 25-minute commutes into George Town, Mount Road, and Guindy.
                </p>
              </div>
              <div className="pt-3 border-t border-[#F1F5F9] flex items-center justify-between text-xs text-[#607080]">
                <span>Typical 2 BHK: ₹14,000–18,000</span>
                <span className="font-bold text-[#1261D6]">CMRL Anchored</span>
              </div>
            </div>
          </div>

          {/* Panel 2 */}
          <div className="group rounded-2xl overflow-hidden bg-white border border-[#E2E8F0] shadow-xs flex flex-col hover:shadow-lg transition-all duration-300">
            <div className="relative h-64 overflow-hidden bg-[#F4F8FC]">
              <img
                src="/properties/chennai_interior_1.jpg"
                alt="Family-Friendly Flats"
                className="w-full h-full object-cover group-hover:scale-103 transition-transform duration-500"
              />
              <div className="absolute top-3 left-3">
                <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-[#0B1F3A]/85 text-white backdrop-blur-xs">
                  Family Residential
                </span>
              </div>
            </div>
            <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
              <div>
                <h3 className="text-base font-bold text-[#102033]">
                  Family Flats with School Access
                </h3>
                <p className="text-xs text-[#607080] mt-1 leading-relaxed">
                  Spacious layouts in Anna Nagar, Porur, and Medavakkam with verified UDISE+ schools and health centers within walking distance.
                </p>
              </div>
              <div className="pt-3 border-t border-[#F1F5F9] flex items-center justify-between text-xs text-[#607080]">
                <span>Typical 2/3 BHK: ₹16,000–22,000</span>
                <span className="font-bold text-[#10B981]">High Family Fit</span>
              </div>
            </div>
          </div>

          {/* Panel 3 */}
          <div className="group rounded-2xl overflow-hidden bg-white border border-[#E2E8F0] shadow-xs flex flex-col hover:shadow-lg transition-all duration-300">
            <div className="relative h-64 overflow-hidden bg-[#F4F8FC]">
              <img
                src="/properties/chennai_complex_1.jpg"
                alt="Gated Communities and Suburbs"
                className="w-full h-full object-cover group-hover:scale-103 transition-transform duration-500"
              />
              <div className="absolute top-3 left-3">
                <span className="text-[10px] font-bold px-2.5 py-1 rounded bg-[#0B1F3A]/85 text-white backdrop-blur-xs">
                  Corridor Enclaves
                </span>
              </div>
            </div>
            <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
              <div>
                <h3 className="text-base font-bold text-[#102033]">
                  Industrial &amp; Tech Corridors
                </h3>
                <p className="text-xs text-[#607080] mt-1 leading-relaxed">
                  Balanced rental pockets in Ambattur, Avadi, and Sholinganallur offering lower cash burden and direct access to manufacturing SEZs.
                </p>
              </div>
              <div className="pt-3 border-t border-[#F1F5F9] flex items-center justify-between text-xs text-[#607080]">
                <span>Typical 1/2 BHK: ₹10,000–15,000</span>
                <span className="font-bold text-[#1261D6]">Lower Cash Outflow</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 09: RIVO CITY PLANNER (Full-Width Deep Navy #0B1F3A Section) */}
      <section className="bg-[#0B1F3A] text-white rounded-2xl p-6 sm:p-12 border border-[#162B4E] shadow-xl relative overflow-hidden">
        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-8 space-y-4">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/10 text-[#F7C948] text-xs font-bold tracking-wide">
              <Layers className="w-3.5 h-3.5 text-[#F7C948]" />
              <span>RIVO City • Policy &amp; Spatial Scenario Simulator</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
              Can the People Who Run the City Afford to Live In It?
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed max-w-2xl">
              For urban planners and mobility agencies: test proposed CMRL Phase II extensions, MTC feeder routes, and GCC municipal housing enclaves. Measure how infrastructure shifts 800m station catchments and worker access in real time.
            </p>
            <div className="flex flex-wrap items-center gap-3 pt-2 text-xs">
              <span className="bg-white/10 px-3 py-1 rounded-lg text-slate-200">
                • 45-Min Worker Catchment Shift
              </span>
              <span className="bg-white/10 px-3 py-1 rounded-lg text-slate-200">
                • GCC 2025 Ward GIS Mapping
              </span>
              <span className="bg-white/10 px-3 py-1 rounded-lg text-slate-200">
                • Defensible Before/After Deltas
              </span>
            </div>
          </div>

          <div className="lg:col-span-4 flex flex-col justify-center items-start lg:items-end">
            <button
              type="button"
              onClick={onSwitchToCityTab}
              className="py-3.5 px-6 rounded-xl bg-[#1261D6] hover:bg-[#0E4EB0] text-white text-sm font-bold shadow-lg transition-all flex items-center space-x-2 cursor-pointer"
            >
              <span>Launch City Scenario Engine</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <span className="text-[11px] text-slate-400 mt-2">
              Sustain-a-thon 2026 Policy Workbench
            </span>
          </div>
        </div>
      </section>

      {/* 10: FINAL BOTTOM SEARCH CONVERSION CTA */}
      <section className="bg-[#F4F8FC] rounded-2xl p-8 sm:p-14 border border-[#E2E8F0] text-center space-y-5 shadow-xs">
        <div className="max-w-2xl mx-auto space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white border border-[#E2E8F0] text-[#1261D6] text-xs font-bold uppercase tracking-wider">
            <Search className="w-3.5 h-3.5 text-[#F7C948]" />
            <span>Ready to Find Your Home?</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[#102033]">
            Start Your Chennai Home &amp; Commute Search
          </h2>
          <p className="text-sm text-[#607080] leading-relaxed">
            Enter your workplace, monthly budget ceiling, and family essentials to explore homes matched to your daily life.
          </p>
        </div>

        <div>
          <button
            type="button"
            onClick={onFocusSearch}
            className="py-3.5 px-8 rounded-xl bg-[#1261D6] hover:bg-[#0E4EB0] text-white text-sm font-bold shadow-md hover:shadow-lg transition-all inline-flex items-center space-x-2 cursor-pointer"
          >
            <Search className="w-4 h-4" />
            <span>Start Searching Now</span>
          </button>
        </div>
      </section>
    </div>
  );
};
