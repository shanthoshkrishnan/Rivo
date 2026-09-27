import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Train,
  Clock,
  HeartPulse,
  Building,
  CheckCircle2,
  TrendingDown,
  Navigation,
  School,
  Activity,
  Layers,
  MapPin,
} from 'lucide-react';
import { ScrollReveal } from '../components/common/ScrollReveal';

export const HomePage: React.FC = () => {
  return (
    <div className="space-y-24 sm:space-y-32 pb-24">
      {/* ============================================================ */}
      {/* 1. FULL-BLEED HERO (100vw, 650–750px tall, Dark Navy overlay) */}
      {/* ============================================================ */}
      <section className="relative w-full h-[660px] sm:h-[720px] overflow-hidden -mt-6">
        {/* Full-width Chennai Residential Architecture Background Image */}
        <div
          className="absolute inset-0 w-full h-full bg-cover bg-center"
          style={{
            backgroundImage: "url('/properties/chennai_apartment_1.jpg')",
          }}
        />

        {/* High-Contrast Dark Navy Overlay (#06243A) */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#06243A]/95 via-[#06243A]/85 to-[#06243A]/50" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#06243A] via-transparent to-transparent opacity-80" />

        {/* Hero Content Container */}
        <div className="relative z-10 max-w-[1440px] h-full mx-auto px-4 sm:px-6 lg:px-8 flex flex-col justify-center">
          <div className="max-w-3xl space-y-6">
            {/* Sustain-a-thon 2026 Tag */}
            <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-white text-xs font-bold tracking-wide">
              <Sparkles className="w-3.5 h-3.5 text-[#F5C542]" />
              <span>Sustain-a-thon 2026 • PS-11-S3 Worker Housing &amp; Mobility</span>
            </div>

            {/* Hero Headline (56-72px desktop) */}
            <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white leading-[1.08]">
              Find a home that works for your life. <br />
              <span className="text-[#13A8E8] relative inline-block">
                Not just your budget.
                <span className="absolute -bottom-1 left-0 w-full h-1.5 bg-[#F5C542] rounded-full" />
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg sm:text-xl text-slate-200 leading-relaxed max-w-2xl font-normal">
              Chennai housing and door-to-door transit intelligence. We calculate real commute times, true travel fares, and verified family essentials for the people who keep the city running.
            </p>

            {/* Hero Actions */}
            <div className="pt-4 flex flex-wrap items-center gap-4">
              <Link
                to="/find"
                className="inline-flex items-center space-x-3 px-8 py-4 rounded-xl bg-[#0878D1] hover:bg-[#0764B0] text-white font-bold text-base transition-all duration-200 shadow-lg shadow-[#0878D1]/30 hover:shadow-[#0878D1]/50 hover:-translate-y-0.5 cursor-pointer"
              >
                <span>Find a Suitable Home</span>
                <ArrowRight className="w-5 h-5 text-[#F5C542]" />
              </Link>

              <Link
                to="/city"
                className="inline-flex items-center space-x-2 px-6 py-4 rounded-xl bg-white/10 hover:bg-white/15 text-white font-bold text-base border border-white/20 transition-colors backdrop-blur-sm cursor-pointer"
              >
                <span>Explore City Planner</span>
              </Link>
            </div>

            {/* Data Provenance Badge */}
            <div className="pt-4 flex items-center space-x-6 text-xs text-slate-300 font-medium">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                <span>Zero Hallucinations</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-[#13A8E8]" />
                <span>CUMTA Multimodal GTFS</span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-[#F5C542]" />
                <span>MoSPI PLFS 2025 Labor Microdata</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* 2. HOW RIVO WORKS (Single-line heading + Scroll Animation)   */}
      {/* ============================================================ */}
      <ScrollReveal className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
        <section>
          <div className="text-center max-w-4xl mx-auto space-y-3 mb-16">
            <span className="text-xs font-bold uppercase tracking-wider text-[#0878D1] bg-[#F3F8FC] px-3.5 py-1 rounded-full border border-[#BFDBFE]">
              Decision Intelligence Pipeline
            </span>
            {/* Kept strictly on a SINGLE LINE as explicitly requested */}
            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-extrabold text-[#06243A] tracking-tight whitespace-nowrap overflow-x-auto">
              How RIVO Finds Your Optimal Home
            </h2>
            <p className="text-base text-[#607080] leading-relaxed max-w-2xl mx-auto">
              Standard portals stop at listing rent. RIVO evaluates your full door-to-door day.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              {
                step: '01',
                title: 'Workplace & Family Anchor',
                desc: 'Enter your workplace, hospital, factory, or school. Set your household size and dependent age bands.',
                icon: <MapPin className="w-6 h-6 text-[#0878D1]" />,
              },
              {
                step: '02',
                title: 'Door-to-Door Multimodal Routing',
                desc: 'We calculate exact transit itineraries across MTC buses, CMRL metro, MRTS suburban rail, and walking transfers.',
                icon: <Train className="w-6 h-6 text-[#13A8E8]" />,
              },
              {
                step: '03',
                title: 'Combined Cost Calculation',
                desc: 'Monthly rent is combined with real monthly travel fares and time tax, evaluated against occupation wage percentiles.',
                icon: <Clock className="w-6 h-6 text-[#F5C542]" />,
              },
              {
                step: '04',
                title: 'Defensible Decision Ranking',
                desc: 'Every recommendation is ranked with transparent breakdown cards and verified local amenities.',
                icon: <CheckCircle2 className="w-6 h-6 text-[#10B981]" />,
              },
            ].map((item, idx) => (
              <div
                key={item.step}
                className="bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-sm hover:shadow-md transition-all duration-300 relative overflow-hidden group hover:-translate-y-1"
              >
                <div className="text-4xl font-extrabold text-[#0878D1]/10 group-hover:text-[#0878D1]/20 transition-colors absolute top-4 right-4">
                  {item.step}
                </div>
                <div className="w-12 h-12 rounded-xl bg-[#F3F8FC] border border-[#BFDBFE] flex items-center justify-center mb-5">
                  {item.icon}
                </div>
                <h3 className="text-lg font-bold text-[#06243A] mb-2">{item.title}</h3>
                <p className="text-sm text-[#607080] leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ============================================================ */}
      {/* 3. EDITORIAL HOUSING SHOWCASE (Scroll Reveal Animation)       */}
      {/* ============================================================ */}
      <ScrollReveal className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
        <section>
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-[#0878D1] bg-[#F3F8FC] px-3.5 py-1 rounded-full border border-[#BFDBFE]">
                Chennai Neighborhood Profiles
              </span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-[#06243A] tracking-tight mt-3">
                Homes That Fit Real Life Across Chennai
              </h2>
              <p className="text-base text-[#607080] mt-2 max-w-xl">
                From transit-connected urban pockets to family enclaves near hospitals and schools.
              </p>
            </div>
            <Link
              to="/find"
              className="inline-flex items-center space-x-2 text-sm font-bold text-[#0878D1] hover:text-[#06243A] transition-colors"
            >
              <span>Explore all search areas</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                title: 'Connected Urban Living',
                area: 'Guindy, Saidapet & Central Corridors',
                image: '/properties/chennai_apartment_1.jpg',
                desc: 'High-frequency MTC bus junctions and CMRL Blue Line stations for healthcare and commercial workers.',
                rent: '₹14,000 – ₹18,000 / mo',
                commute: '~24 min average to central hubs',
              },
              {
                title: 'Family-First Neighborhoods',
                area: 'Anna Nagar, Mogappair & Porur',
                image: '/properties/chennai_complex_1.jpg',
                desc: 'Peaceful residential enclaves with UDISE+ recognized schools and multi-specialty clinics within a 15-minute walk.',
                rent: '₹12,000 – ₹16,500 / mo',
                commute: 'Quiet streets + CMRL feeder buses',
              },
              {
                title: 'Industrial & Tech Corridors',
                area: 'Taramani, Velachery & Sriperumbudur',
                image: '/properties/chennai_interior_1.jpg',
                desc: 'Strategic locations along OMR and GST Road with direct commuter access to SIPCOT tech parks and manufacturing belts.',
                rent: '₹11,000 – ₹15,000 / mo',
                commute: 'Direct MRTS & highway connectivity',
              },
            ].map((card, idx) => (
              <div
                key={idx}
                className="bg-white rounded-3xl overflow-hidden border border-[#E2E8F0] shadow-sm hover:shadow-xl transition-all duration-300 group flex flex-col justify-between hover:-translate-y-1.5"
              >
                <div>
                  <div className="relative h-64 overflow-hidden">
                    <img
                      src={card.image}
                      alt={card.title}
                      className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#06243A]/80 via-transparent to-transparent" />
                    <div className="absolute bottom-4 left-4 right-4 text-white">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-[#F5C542]">
                        {card.area}
                      </span>
                      <h3 className="text-xl font-extrabold text-white mt-0.5">{card.title}</h3>
                    </div>
                  </div>

                  <div className="p-6 space-y-4">
                    <p className="text-sm text-[#607080] leading-relaxed">{card.desc}</p>

                    <div className="space-y-1.5 pt-3 border-t border-[#E2E8F0] text-xs">
                      <div className="flex justify-between">
                        <span className="text-[#607080]">Typical Asking Rent:</span>
                        <span className="font-bold text-[#06243A]">{card.rent}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#607080]">Transit Access:</span>
                        <span className="font-semibold text-[#0878D1]">{card.commute}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-6 pt-0">
                  <Link
                    to="/find"
                    className="w-full py-3 rounded-xl bg-[#F3F8FC] hover:bg-[#0878D1] text-[#0878D1] hover:text-white font-bold text-xs flex items-center justify-center space-x-2 transition-all cursor-pointer border border-[#BFDBFE]"
                  >
                    <span>Search in This Corridor</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      </ScrollReveal>

      {/* ============================================================ */}
      {/* 4. WHY COMMUTE MATTERS: HORIZONTAL COST EQUATION & STORY     */}
      {/* ============================================================ */}
      <ScrollReveal className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
        <section className="bg-[#06243A] rounded-3xl p-8 sm:p-12 text-white relative overflow-hidden shadow-2xl border border-white/10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-[#0878D1]/20 rounded-full blur-3xl pointer-events-none" />

          {/* Heading */}
          <div className="text-center max-w-3xl mx-auto space-y-3 mb-12">
            <span className="text-xs font-bold uppercase tracking-wider text-[#F5C542]">
              Why RIVO is Radically Different
            </span>
            <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white">
              The Real Cost of Living Equation
            </h2>
            <p className="text-sm sm:text-base text-slate-300">
              A cheaper house 20 km away with three bus transfers often costs more money and 40 extra hours a month than a home near your station.
            </p>
          </div>

          {/* Horizontal Equation Representation */}
          <div className="max-w-4xl mx-auto bg-white/5 border border-white/10 rounded-2xl p-6 sm:p-8 backdrop-blur-md mb-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
              <div className="space-y-1">
                <div className="text-2xl sm:text-3xl font-extrabold text-white">RENT</div>
                <div className="text-xs text-slate-400">Monthly Asking</div>
              </div>
              <div className="space-y-1">
                <div className="text-2xl sm:text-3xl font-extrabold text-[#13A8E8]">+ TRANSIT</div>
                <div className="text-xs text-slate-400">MTC + CMRL Fares</div>
              </div>
              <div className="space-y-1">
                <div className="text-2xl sm:text-3xl font-extrabold text-[#F5C542]">+ TIME TAX</div>
                <div className="text-xs text-slate-400">Hours in Commute</div>
              </div>
              <div className="space-y-1">
                <div className="text-2xl sm:text-3xl font-extrabold text-[#10B981]">+ FAMILY</div>
                <div className="text-xs text-slate-400">Schools &amp; Clinics</div>
              </div>
            </div>

            <div className="my-6 border-t border-white/10" />

            <div className="text-center space-y-1">
              <div className="text-xs font-bold text-[#F5C542] uppercase tracking-widest">Equals</div>
              <div className="text-2xl sm:text-4xl font-extrabold text-white">
                REAL COST OF LIVING &amp; ACCESSIBILITY
              </div>
            </div>
          </div>

          {/* 50/50 Split Living Cost Story */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center pt-4">
            <div className="space-y-4">
              <div className="inline-block px-3 py-1 rounded-md bg-white/10 border border-white/20 text-[#13A8E8] text-xs font-bold">
                REPRESENTATIVE EXAMPLE • CHENNAI HEALTHCARE WORKER
              </div>
              <h3 className="text-2xl sm:text-3xl font-bold text-white">
                ₹14,000 rent in Saidapet vs ₹11,000 in Peripheral Outskirts
              </h3>
              <p className="text-sm text-slate-300 leading-relaxed">
                A nurse working at Rajiv Gandhi Government General Hospital (Central) saves ₹3,000 on peripheral rent, but loses ₹2,400 on daily multimodal fares and endures 52 hours per month on overcrowded buses.
              </p>
              <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Outskirts Total Monthly Impact:</span>
                  <span className="font-bold text-rose-400">₹13,400 cash + 52 commute hrs</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Saidapet Transit-Adjacent Home:</span>
                  <span className="font-bold text-emerald-400">₹14,800 cash + 18 commute hrs</span>
                </div>
              </div>
            </div>

            <div className="relative rounded-2xl overflow-hidden border border-white/10 h-72">
              <img
                src="/properties/chennai_interior_1.jpg"
                alt="Chennai Living Room"
                className="w-full h-full object-cover object-center"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#06243A]/80 via-transparent to-transparent" />
              <div className="absolute bottom-4 left-4 right-4">
                <div className="text-xs font-bold text-[#F5C542]">Transparent Affordability Benchmarks</div>
                <div className="text-sm text-white font-medium">PLFS 2025 verified nurse wage percentiles applied.</div>
              </div>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* ============================================================ */}
      {/* 5. CITY PLANNING SCENARIO CAPABILITY SECTION (Scroll Reveal) */}
      {/* ============================================================ */}
      <ScrollReveal className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
        <section className="bg-[#F3F8FC] rounded-3xl p-8 sm:p-12 border border-[#BFDBFE] flex flex-col lg:flex-row items-center justify-between gap-8">
          <div className="space-y-4 max-w-xl">
            <span className="text-xs font-bold uppercase tracking-wider text-[#0878D1] bg-white px-3 py-1 rounded-full border border-[#BFDBFE]">
              RIVO City • Urban Governance
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-[#06243A] tracking-tight">
              Can the People Who Run the City Afford to Live In It?
            </h2>
            <p className="text-sm text-[#607080] leading-relaxed">
              For planners at GCC, CMDA, and CUMTA: simulate transit fare reforms, CMRL Phase 2 corridor extensions, and municipal housing supply quotas to measure workforce accessibility gains.
            </p>
            <div className="pt-2 flex flex-wrap gap-4 text-xs font-semibold text-[#06243A]">
              <div className="flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#0878D1]" />
                <span>PLFS Occupation Wage Bounds</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#0878D1]" />
                <span>45-Min Accessibility Isochrones</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#0878D1]" />
                <span>Real-Time Policy Interventions</span>
              </div>
            </div>
          </div>

          <div className="shrink-0 w-full lg:w-auto">
            <Link
              to="/city"
              className="inline-flex items-center justify-center space-x-2 w-full lg:w-auto px-8 py-4 rounded-xl bg-[#06243A] hover:bg-[#0B1F3A] text-white font-bold text-sm transition-all shadow-md cursor-pointer"
            >
              <span>Open Scenario Engine</span>
              <ArrowRight className="w-4 h-4 text-[#F5C542]" />
            </Link>
          </div>
        </section>
      </ScrollReveal>

      {/* ============================================================ */}
      {/* 6. FINAL CALL TO ACTION (Find a Home - Scroll Reveal)        */}
      {/* ============================================================ */}
      <ScrollReveal className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
        <section className="bg-gradient-to-r from-[#0878D1] to-[#13A8E8] rounded-3xl p-8 sm:p-14 text-white text-center space-y-6 shadow-xl relative overflow-hidden">
          <div className="max-w-2xl mx-auto space-y-3">
            <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight">
              Ready to find a home that fits your real commute?
            </h2>
            <p className="text-sm sm:text-base text-white/90 leading-relaxed">
              Search by your workplace, office, or hospital to discover verified homes with door-to-door transit itineraries.
            </p>
          </div>

          <div>
            <Link
              to="/find"
              className="inline-flex items-center space-x-3 px-8 py-4 rounded-xl bg-white text-[#0878D1] hover:bg-[#F3F8FC] font-extrabold text-base transition-all shadow-lg hover:scale-102 cursor-pointer"
            >
              <span>Start Your Rental Search</span>
              <ArrowRight className="w-5 h-5 text-[#F5C542]" />
            </Link>
          </div>
        </section>
      </ScrollReveal>
    </div>
  );
};
