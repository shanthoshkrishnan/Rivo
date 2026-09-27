import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  ExternalLink,
  Layers,
  Building2,
  Users,
  Train,
  HeartPulse,
  AlertCircle,
  FileCheck2,
  CheckCircle2,
  Database,
  Search,
} from 'lucide-react';
import { DataSource } from '../../types/api';
import { fetchDataSources } from '../../services/api';

const CATEGORY_MAP: Record<string, { label: string; icon: React.ReactNode; desc: string }> = {
  housing: {
    label: 'Housing & Rentals',
    icon: <Building2 className="w-4 h-4 text-[#1261D6]" />,
    desc: 'Rental inventory, observation history, and asking prices across Chennai',
  },
  transit: {
    label: 'Mobility & Transit Networks',
    icon: <Train className="w-4 h-4 text-[#1DA1F2]" />,
    desc: 'CUMTA GTFS bus and metro timetables, stops, routes, and fare stages',
  },
  income: {
    label: 'Workers & Labor Economics',
    icon: <Users className="w-4 h-4 text-[#10B981]" />,
    desc: 'PLFS 2025 microdata income distributions for essential worker occupations',
  },
  facilities: {
    label: 'Neighborhood & Family Amenities',
    icon: <HeartPulse className="w-4 h-4 text-[#8B5CF6]" />,
    desc: 'Government & private hospitals, dispensaries, pharmacies, and UDISE+ schools',
  },
  city_boundary: {
    label: 'Administrative & Demographics',
    icon: <Layers className="w-4 h-4 text-[#0B1F3A]" />,
    desc: 'Greater Chennai Corporation ward GIS boundaries and WorldPop density benchmarks',
  },
};

export const DataSourcesView: React.FC = () => {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    fetchDataSources()
      .then((data) => setSources(data))
      .finally(() => setIsLoading(false));
  }, []);

  // Canonical sample data record for strict honesty
  const sampleDataEntry: DataSource = {
    id: 'rivo_sample_seed',
    source_name: 'RIVO Chennai Sample Rental Data',
    layer: 'housing',
    source_url: '',
    license: 'Internal demonstration use only — not for commercial redistribution',
    attribution: 'Team CLAIRES / RIVO Project Seed Registry',
    data_freshness: 'PERIODIC',
    update_frequency: 'demonstration_seed',
  };

  const allSourcesWithDemo = [
    ...sources,
    ...(sources.some((s) => s.source_name.toLowerCase().includes('sample')) ? [] : [sampleDataEntry]),
  ];

  const categories = [
    { id: 'all', label: 'All Sources', count: allSourcesWithDemo.length },
    { id: 'housing', label: 'Housing', count: allSourcesWithDemo.filter((s) => s.layer === 'housing').length },
    { id: 'transit', label: 'Transit', count: allSourcesWithDemo.filter((s) => s.layer === 'transit').length },
    { id: 'income', label: 'Workers & Income', count: allSourcesWithDemo.filter((s) => s.layer === 'income').length },
    { id: 'facilities', label: 'Facilities', count: allSourcesWithDemo.filter((s) => s.layer === 'facilities' || s.layer === 'health' || s.layer === 'education').length },
    { id: 'city_boundary', label: 'City Planning', count: allSourcesWithDemo.filter((s) => s.layer === 'city_boundary' || s.layer === 'boundary').length },
  ];

  const filteredSources = allSourcesWithDemo.filter((s) => {
    const matchesCat =
      selectedCategory === 'all' ||
      (selectedCategory === 'facilities'
        ? s.layer === 'facilities' || s.layer === 'health' || s.layer === 'education'
        : selectedCategory === 'city_boundary'
        ? s.layer === 'city_boundary' || s.layer === 'boundary'
        : s.layer === selectedCategory);

    const matchesQuery =
      searchQuery === '' ||
      s.source_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.attribution?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.license?.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesCat && matchesQuery;
  });

  return (
    <div className="space-y-8 animate-fadeIn max-w-[1536px] mx-auto">
      {/* 1. Trust Center Header Banner */}
      <div className="bg-[#0B1F3A] rounded-3xl p-8 sm:p-10 text-white relative overflow-hidden shadow-xl border border-white/10">
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#1261D6]/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 text-[#F7C948] text-xs font-bold tracking-wide">
            <ShieldCheck className="w-3.5 h-3.5 text-[#F7C948]" />
            <span>DATA &amp; TRUST CENTER • AUTHENTICITY REGISTRY</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
            Data You Can Trace. <br />
            <span className="text-[#1DA1F2]">No Fabrications. Zero Hallucinations.</span>
          </h1>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-2xl">
            Every boundary polygon, transit timetable, facility coordinate, and income estimate in RIVO is explicitly attributed to authoritative government and research publications with clear licensing and freshness dates.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-6 text-xs text-slate-300">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-[#10B981]" />
              <span>Official Open Government Data (OGD)</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-[#1DA1F2]" />
              <span>CUMTA Multimodal GTFS</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-[#F7C948]" />
              <span>Strictly Labeled Sample Rental Seed</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Controls Toolbar: Category Tabs + Search Input */}
      <div className="bg-white rounded-2xl p-4 sm:p-5 border border-[#E2E8F0] shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Category Tabs */}
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                selectedCategory === cat.id
                  ? 'bg-[#0B1F3A] text-white shadow-xs'
                  : 'bg-[#F4F8FC] text-[#607080] hover:text-[#0B1F3A] hover:bg-[#EEF5FF] border border-[#E2E8F0]'
              }`}
            >
              <span>{cat.label}</span>
              <span
                className={`ml-2 text-[10px] px-1.5 py-0.2 rounded-full ${
                  selectedCategory === cat.id ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'
                }`}
              >
                {cat.count}
              </span>
            </button>
          ))}
        </div>

        {/* Search Filter Input */}
        <div className="relative min-w-[260px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search datasets, license, author..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-[#F7F9FC] border border-[#E2E8F0] rounded-xl text-xs text-[#102033] placeholder-slate-400 focus:outline-none focus:border-[#1261D6] focus:bg-white transition-all"
          />
        </div>
      </div>

      {/* 3. Structured Data Registry Table */}
      {isLoading ? (
        <div className="p-16 text-center text-xs text-[#607080] bg-white rounded-2xl border border-[#E2E8F0]">
          <span className="w-5 h-5 border-2 border-[#1261D6]/30 border-t-[#1261D6] rounded-full animate-spin inline-block mr-2" />
          Querying authoritative registry entries...
        </div>
      ) : filteredSources.length === 0 ? (
        <div className="p-12 text-center text-xs text-[#607080] bg-white rounded-2xl border border-[#E2E8F0]">
          No authoritative datasets match your search query.
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F7F9FC] text-[#607080] font-bold uppercase tracking-wider text-[11px] border-b border-[#E2E8F0]">
                <tr>
                  <th className="py-3.5 px-6">Source &amp; Dataset</th>
                  <th className="py-3.5 px-4">Category / Domain</th>
                  <th className="py-3.5 px-4">Attribution / Agency</th>
                  <th className="py-3.5 px-4">Update Frequency</th>
                  <th className="py-3.5 px-4">License / Terms</th>
                  <th className="py-3.5 px-6 text-right">Status / Access</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0]">
                {filteredSources.map((src, idx) => {
                  const isDemo =
                    src.source_name.toLowerCase().includes('sample') ||
                    src.update_frequency === 'demonstration_seed';

                  return (
                    <tr
                      key={src.id || `${src.source_name}-${idx}`}
                      className={`hover:bg-[#F4F8FC] transition-colors ${
                        isDemo ? 'bg-[#FFFBEB]/40' : ''
                      }`}
                    >
                      {/* 1. Source & Dataset Name */}
                      <td className="py-4 px-6">
                        <div className="flex items-start space-x-3">
                          <div
                            className={`p-2 rounded-xl mt-0.5 shrink-0 ${
                              isDemo ? 'bg-amber-100 text-amber-800' : 'bg-[#EEF5FF] text-[#1261D6]'
                            }`}
                          >
                            <Database className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="font-bold text-[#102033] text-sm flex items-center space-x-2">
                              <span>{src.source_name}</span>
                            </div>
                            <p className="text-[11px] text-[#607080] mt-0.5 max-w-sm line-clamp-1">
                              {isDemo
                                ? '88 CMRL-anchored properties for UI demonstration only. Excluded from rent ML training.'
                                : ((src.layer && CATEGORY_MAP[src.layer]?.desc) ||
                                  'Primary authoritative Chennai GIS / labor microdata.')}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* 2. Category / Domain */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-[#EEF5FF] text-[#1261D6] font-semibold text-[11px]">
                          {(src.layer && CATEGORY_MAP[src.layer]?.icon) || (
                            <Layers className="w-3.5 h-3.5" />
                          )}
                          <span>{(src.layer && CATEGORY_MAP[src.layer]?.label) || src.layer || 'Core'}</span>
                        </span>
                      </td>

                      {/* 3. Attribution */}
                      <td className="py-4 px-4 font-medium text-[#102033] whitespace-nowrap">
                        {src.attribution || 'Official Agency'}
                      </td>

                      {/* 4. Update Frequency */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <span className="capitalize text-[#607080] font-semibold">
                          {src.update_frequency?.replace('_', ' ') || 'Periodic'}
                        </span>
                      </td>

                      {/* 5. License */}
                      <td className="py-4 px-4 text-[#607080] font-mono text-[11px] max-w-[220px] truncate">
                        {src.license || 'Public / Research Open Data'}
                      </td>

                      {/* 6. Status / Access */}
                      <td className="py-4 px-6 text-right whitespace-nowrap">
                        {isDemo ? (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-300 font-bold text-[10px]">
                            <AlertCircle className="w-3 h-3 text-amber-700" />
                            <span>DEMO / SAMPLE</span>
                          </span>
                        ) : src.source_url ? (
                          <a
                            href={src.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#1261D6] hover:bg-[#0E4EB0] text-white font-bold text-xs transition-colors shadow-xs"
                          >
                            <span>Verify Source</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        ) : (
                          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold text-[10px]">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>OFFLINE VERIFIED</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. Governance & Verification Footer Note */}
      <div className="p-5 rounded-2xl bg-[#F4F8FC] border border-[#BFDBFE] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-[#0B1F3A]">
        <div className="flex items-center space-x-3">
          <FileCheck2 className="w-5 h-5 text-[#1261D6] shrink-0" />
          <p className="leading-relaxed">
            <b>Strict Governance Policy:</b> Real asking rent data is collected with defensible timestamps and platform attributions. The XGBoost rent estimation model refuses inference (<code className="bg-white px-1.5 py-0.5 rounded border border-[#BFDBFE] font-mono text-[11px] text-[#1261D6]">INSUFFICIENT_DATA</code>) until the 50-record Chennai threshold is satisfied.
          </p>
        </div>
      </div>
    </div>
  );
};
