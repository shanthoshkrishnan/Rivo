import React from 'react';
import { Home, Compass, Database, Activity, MapPin } from 'lucide-react';

interface HeaderProps {
  currentTab: 'home' | 'city' | 'sources';
  onSelectTab: (tab: 'home' | 'city' | 'sources') => void;
  backendOnline: boolean | null;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onSelectTab,
  backendOnline,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-[#FAF8F5]/90 backdrop-blur-md border-b border-[#EBE4DC]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onSelectTab('home')}>
            <div className="w-10 h-10 rounded-xl bg-[#F5EFEB] border border-[#E4DBD0] flex items-center justify-center text-[#C25E38] shadow-sm">
              <span className="font-bold text-xl tracking-tight text-[#C25E38]">R</span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-[#2C2523]">RIVO</span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#F5EFEB] text-[#8C7E75] font-medium border border-[#E8E0D5]">
                  Chennai • PS-11
                </span>
              </div>
              <p className="text-[11px] text-[#7A6F68] font-normal leading-none hidden sm:block">
                Worker Housing &amp; Mobility Intelligence
              </p>
            </div>
          </div>

          {/* Navigation Modes */}
          <nav className="flex items-center space-x-1 sm:space-x-2 bg-[#F3ECE4] p-1 rounded-xl border border-[#E5DDD2]">
            <button
              onClick={() => onSelectTab('home')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                currentTab === 'home'
                  ? 'bg-white text-[#2C2523] shadow-sm font-semibold'
                  : 'text-[#6E645E] hover:text-[#2C2523]'
              }`}
            >
              <Home className={`w-3.5 h-3.5 ${currentTab === 'home' ? 'text-[#C25E38]' : 'text-[#8C7E75]'}`} />
              <span>Find a Home</span>
            </button>

            <button
              onClick={() => onSelectTab('city')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                currentTab === 'city'
                  ? 'bg-white text-[#2C2523] shadow-sm font-semibold'
                  : 'text-[#6E645E] hover:text-[#2C2523]'
              }`}
            >
              <Compass className={`w-3.5 h-3.5 ${currentTab === 'city' ? 'text-[#C25E38]' : 'text-[#8C7E75]'}`} />
              <span>City Planner</span>
            </button>

            <button
              onClick={() => onSelectTab('sources')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                currentTab === 'sources'
                  ? 'bg-white text-[#2C2523] shadow-sm font-semibold'
                  : 'text-[#6E645E] hover:text-[#2C2523]'
              }`}
            >
              <Database className={`w-3.5 h-3.5 ${currentTab === 'sources' ? 'text-[#C25E38]' : 'text-[#8C7E75]'}`} />
              <span className="hidden md:inline">Data Sources</span>
            </button>
          </nav>

          {/* Status Indicator */}
          <div className="flex items-center space-x-2">
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                backendOnline
                  ? 'bg-[#F2F7F3] text-[#356345] border-[#D4E5D9]'
                  : 'bg-[#FAF1EC] text-[#A64522] border-[#F1DDD4]'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  backendOnline ? 'bg-[#356345] animate-pulse' : 'bg-[#A64522]'
                }`}
              />
              <span className="hidden sm:inline">
                {backendOnline ? 'API Connected' : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
