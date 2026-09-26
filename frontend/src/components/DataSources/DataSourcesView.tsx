import React, { useEffect, useState } from 'react';
import { Database, ShieldCheck, ExternalLink, RefreshCw } from 'lucide-react';
import { DataSource } from '../../types/api';
import { fetchDataSources } from '../../services/api';

export const DataSourcesView: React.FC = () => {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchDataSources()
      .then((data) => setSources(data))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Intro Banner */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-[#EBE4DC] shadow-sm">
        <div className="max-w-3xl">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#FAF5F0] border border-[#F0DFD5] text-[#C25E38] text-xs font-semibold mb-3">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Transparency &amp; Data Provenance</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#2C2523]">
            Data Sources &amp; Licensing Registry
          </h2>
          <p className="text-xs sm:text-sm text-[#6B615B] mt-2 leading-relaxed">
            RIVO strictly adheres to data transparency principles: every statistic, spatial boundary, transit timetable, and facility location is attributable to its authoritative source, clearly marked with update frequency and license terms.
          </p>
        </div>
      </div>

      {/* Sources Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[#8C7E75]">
          <span className="w-4 h-4 border-2 border-[#C25E38]/30 border-t-[#C25E38] rounded-full animate-spin inline-block mr-2" />
          Loading authoritative data registry...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sources.map((src) => (
            <div
              key={src.id || src.source_name}
              className="bg-white rounded-2xl p-5 border border-[#EBE4DC] shadow-xs hover:border-[#D6CBC0] transition-colors flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-sm font-bold text-[#2C2523]">{src.source_name}</h3>
                    <span className="text-[11px] font-medium text-[#C25E38] bg-[#FAF5F0] px-2 py-0.5 rounded-md border border-[#F3DFD5]">
                      {src.layer || 'Core'}
                    </span>
                  </div>
                  <span className="text-[10px] uppercase font-bold text-[#8C7E75] bg-[#FAF8F5] px-2 py-1 rounded border border-[#EDE4DB]">
                    {src.data_freshness || 'PERIODIC'}
                  </span>
                </div>

                <div className="text-xs text-[#6B615B] space-y-1 mt-3">
                  <div>
                    <span className="text-[#8C7E75]">Attribution: </span>
                    <span className="font-medium text-[#2C2523]">{src.attribution || 'Authoritative Provider'}</span>
                  </div>
                  <div>
                    <span className="text-[#8C7E75]">License / Terms: </span>
                    <span className="font-mono text-[11px] text-[#4A3E39]">{src.license || 'Public / Open License'}</span>
                  </div>
                  <div>
                    <span className="text-[#8C7E75]">Update Frequency: </span>
                    <span className="capitalize">{src.update_frequency || 'Periodic'}</span>
                  </div>
                </div>
              </div>

              {src.source_url && (
                <div className="mt-4 pt-3 border-t border-[#F3EDE6] flex justify-end">
                  <a
                    href={src.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-1 text-xs text-[#C25E38] hover:text-[#943F20] font-medium"
                  >
                    <span>View Public Source</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
