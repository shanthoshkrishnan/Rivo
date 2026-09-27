import React from 'react';
import { Link } from 'react-router-dom';
import { RivoLogo } from './brand/RivoLogo';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto bg-[#06243A] text-[#E2E8F0] pt-16 pb-12 border-t border-[#0878D1]/20">
      <div className="max-w-[1440px] w-full mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10 pb-12 border-b border-white/10">
          {/* Col 1: Official Brand Lockup */}
          <div className="lg:col-span-2 space-y-4">
            <RivoLogo variant="full" theme="dark" size="lg" />
            <p className="text-xs text-slate-300 leading-relaxed max-w-sm pt-2">
              Built for <b>Sustain-a-thon 2026</b> by <b>Team CLAIRES (ST1010)</b> targeting Problem Statement <b>PS-11-S3</b>: <em>Can the People Who Run the City Afford to Live In It?</em>
            </p>
            <div className="flex items-center space-x-2 text-[11px] text-[#F5C542] font-bold">
              <span className="w-2 h-2 rounded-full bg-[#F5C542] animate-pulse" />
              <span>Zero Hallucinations • Defensible PLFS &amp; GTFS Calibration</span>
            </div>
          </div>

          {/* Col 2: Navigation Links */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#13A8E8]">Platform Exploration</h4>
            <ul className="space-y-2 text-xs text-slate-300 font-medium">
              <li>
                <Link to="/" className="hover:text-[#F5C542] transition-colors">
                  Product Overview
                </Link>
              </li>
              <li>
                <Link to="/find" className="hover:text-[#F5C542] transition-colors">
                  Find a Home (Rental Search)
                </Link>
              </li>
              <li>
                <Link to="/city" className="hover:text-[#F5C542] transition-colors">
                  City Planner (Scenario Engine)
                </Link>
              </li>
              <li>
                <Link to="/data-sources" className="hover:text-[#F5C542] transition-colors">
                  Data Sources Trust Center
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Data Provenance */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#13A8E8]">Authoritative Sources</h4>
            <ul className="space-y-2 text-xs text-slate-400">
              <li><span className="text-slate-200">CUMTA:</span> GTFS Transit Feeds</li>
              <li><span className="text-slate-200">MoSPI:</span> PLFS 2025 Labor Microdata</li>
              <li><span className="text-slate-200">GCC:</span> Ward Boundary GIS 2025</li>
              <li><span className="text-slate-200">UDISE+:</span> School Accessibility Layer</li>
              <li><span className="text-slate-200">TN Health OGD:</span> Hospital Facilities</li>
            </ul>
          </div>

          {/* Col 4: Platform Integrity */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#13A8E8]">Model Governance</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              Rent ML model strictly gated (<code className="text-[#F5C542] font-mono text-[10px]">INSUFFICIENT_DATA</code>) until 50+ genuine verified Chennai market observations are collected.
            </p>
            <div className="text-[11px] text-[#13A8E8] font-semibold">
              Google Maps &amp; Routes Integration Enabled
            </div>
          </div>
        </div>

        {/* Bottom Copyright & Attribution Bar */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-4">
          <div>
            © 2026 Team CLAIRES (ST1010) • Chennai Sustainable Mobility &amp; Housing Initiative
          </div>
          <div className="flex items-center space-x-4">
            <span>Sustain-a-thon 2026</span>
            <span>•</span>
            <span>OpenStreetMap ODbL</span>
            <span>•</span>
            <span>Google Maps Platform</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
