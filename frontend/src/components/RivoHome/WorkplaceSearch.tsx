import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  MapPin,
  Building2,
  CheckCircle2,
  X,
  HeartPulse,
  Train,
  Factory,
} from 'lucide-react';
import { searchWorkplaces, WorkplaceResult } from '../../services/api';

export interface SelectedWorkplace {
  lat: number;
  lon: number;
  label: string;
  area?: string;
  category?: string;
}

interface WorkplaceSearchProps {
  selectedWorkplace: SelectedWorkplace | null;
  onSelectWorkplace: (wp: SelectedWorkplace | null) => void;
  disabled?: boolean;
}

const POPULAR_SEARCH_SHORTCUTS: SelectedWorkplace[] = [
  { label: 'Tidel Park', area: 'Taramani, OMR', lat: 12.9892, lon: 80.2494, category: 'IT & Tech' },
  { label: 'Chennai Central', area: 'Park Town', lat: 13.0827, lon: 80.2707, category: 'Central Hub' },
  { label: 'Guindy SIDCO', area: 'Guindy Estate', lat: 13.0067, lon: 80.2023, category: 'Industrial' },
  { label: 'Sriperumbudur', area: 'Automotive Belt', lat: 12.9675, lon: 79.9442, category: 'Manufacturing' },
  { label: 'Ambattur Estate', area: 'Ambattur', lat: 13.1143, lon: 80.1548, category: 'Manufacturing' },
];

function getCategoryIcon(category?: string) {
  const cat = (category || '').toLowerCase();
  if (cat.includes('hospital') || cat.includes('health') || cat.includes('medical')) {
    return <HeartPulse className="w-4 h-4 text-[#EF4444]" />;
  }
  if (cat.includes('transit') || cat.includes('station') || cat.includes('central')) {
    return <Train className="w-4 h-4 text-[#0878D1]" />;
  }
  if (cat.includes('industrial') || cat.includes('manufacturing')) {
    return <Factory className="w-4 h-4 text-[#F5C542]" />;
  }
  return <Building2 className="w-4 h-4 text-[#0878D1]" />;
}

export const WorkplaceSearch: React.FC<WorkplaceSearchProps> = ({
  selectedWorkplace,
  onSelectWorkplace,
  disabled = false,
}) => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [results, setResults] = useState<WorkplaceResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [isEditing, setIsEditing] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounced search against real backend API (Google Places + PostGIS verified fallback)
  useEffect(() => {
    if (!isOpen) return;

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await searchWorkplaces(query);
        setResults(res);
        setHighlightedIndex(-1);
      } catch (err) {
        console.warn('Place search error', err);
      } finally {
        setIsLoading(false);
      }
    }, 180);

    return () => clearTimeout(timer);
  }, [query, isOpen]);

  // Handle outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setIsEditing(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const handleSelect = (item: WorkplaceResult | SelectedWorkplace) => {
    const lat = 'latitude' in item ? item.latitude : item.lat;
    const lon = 'longitude' in item ? item.longitude : item.lon;
    const label = 'name' in item ? item.name : item.label;
    const wp: SelectedWorkplace = {
      lat,
      lon,
      label,
      area: item.area,
      category: item.category,
    };
    onSelectWorkplace(wp);
    setQuery('');
    setIsOpen(false);
    setIsEditing(false);
  };

  const handleClear = () => {
    onSelectWorkplace(null);
    setQuery('');
    setIsEditing(true);
    setIsOpen(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter' && highlightedIndex >= 0 && results[highlightedIndex]) {
      e.preventDefault();
      handleSelect(results[highlightedIndex]);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
      setIsEditing(false);
    }
  };

  return (
    <div ref={containerRef} className="relative w-full">
      {/* State 1: When a workplace is confirmed and not currently in edit mode */}
      {!isEditing && selectedWorkplace?.label ? (
        <div className="bg-[#F3F8FC] rounded-2xl p-4 border border-[#BFDBFE] transition-colors flex items-center justify-between gap-3">
          <div className="flex items-center space-x-3.5 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-white border border-[#BFDBFE] flex items-center justify-center shrink-0 shadow-xs">
              <MapPin className="w-5 h-5 text-[#0878D1]" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-2">
                <span className="text-base font-extrabold text-[#06243A] tracking-tight truncate">
                  {selectedWorkplace.label}
                </span>
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-[#ECFDF5] text-[#059669] text-[10px] font-bold border border-[#A7F3D0] shrink-0">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Workplace confirmed</span>
                </span>
              </div>
              <div className="text-xs text-[#607080] truncate mt-0.5">
                {selectedWorkplace.area || 'Chennai Metropolitan Area'}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <button
              type="button"
              onClick={() => {
                setIsEditing(true);
                setIsOpen(true);
                setTimeout(() => inputRef.current?.focus(), 50);
              }}
              className="text-xs font-bold px-3 py-1.5 rounded-xl bg-white hover:bg-[#EEF5FF] text-[#0878D1] border border-[#BFDBFE] transition-colors cursor-pointer shadow-xs"
            >
              Change
            </button>
            <button
              type="button"
              onClick={handleClear}
              className="p-1.5 rounded-xl text-slate-400 hover:text-rose-500 hover:bg-white transition-colors cursor-pointer"
              title="Clear workplace"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      ) : (
        /* State 2: Active Search Input (Empty or Editing) */
        <div className="space-y-2">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
              <Search className="w-5 h-5 text-slate-400" />
            </div>

            <input
              ref={inputRef}
              type="text"
              value={query}
              disabled={disabled}
              onChange={(e) => {
                setQuery(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              onKeyDown={handleKeyDown}
              placeholder="Search your workplace, office, hospital, factory, school..."
              className="w-full pl-11 pr-10 py-3.5 bg-white border border-[#CBD5E1] rounded-2xl text-sm font-medium text-[#06243A] placeholder:text-slate-400 focus:outline-none focus:border-[#0878D1] focus:ring-3 focus:ring-[#0878D1]/15 transition-all shadow-xs"
            />

            {isLoading && (
              <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none">
                <span className="w-4 h-4 border-2 border-[#0878D1]/30 border-t-[#0878D1] rounded-full animate-spin" />
              </div>
            )}
          </div>

          {/* Autocomplete Dropdown */}
          {isOpen && (
            <div className="absolute z-50 left-0 right-0 mt-1 bg-white rounded-2xl border border-[#E2E8F0] shadow-2xl overflow-hidden max-h-72 overflow-y-auto animate-fadeIn">
              {results.length > 0 ? (
                <div className="py-2 divide-y divide-slate-100">
                  {results.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setHighlightedIndex(idx)}
                      className={`w-full px-4 py-3 flex items-start space-x-3 text-left transition-colors cursor-pointer ${
                        highlightedIndex === idx ? 'bg-[#F3F8FC]' : 'hover:bg-slate-50'
                      }`}
                    >
                      <div className="p-2 rounded-xl bg-slate-100 text-[#0878D1] shrink-0 mt-0.5">
                        {getCategoryIcon(item.category)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-bold text-sm text-[#06243A] truncate">{item.name}</div>
                        <div className="text-xs text-[#607080] truncate mt-0.5">
                          {item.area} <span className="text-slate-300">•</span> {item.category}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              ) : query.trim().length > 1 && !isLoading ? (
                <div className="p-4 text-center text-xs text-[#607080]">
                  No matching Chennai locations found. Try searching by neighborhood or landmark.
                </div>
              ) : (
                <div className="p-3 text-xs text-slate-400">
                  Type 2+ letters to search workplaces across Chennai via Google Places &amp; local registries.
                </div>
              )}
            </div>
          )}

          {/* Subtle Popular Search Shortcuts (Populate Search Only) */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs text-slate-500">
            <span className="text-[11px] font-semibold text-slate-400 mr-1">Popular searches:</span>
            {POPULAR_SEARCH_SHORTCUTS.map((sc, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelect(sc)}
                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-[#EEF5FF] hover:text-[#0878D1] text-[#06243A] text-xs font-semibold transition-colors cursor-pointer"
              >
                {sc.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
