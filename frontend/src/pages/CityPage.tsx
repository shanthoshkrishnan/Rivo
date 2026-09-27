import React, { useState, useEffect } from 'react';
import { CityPlanner } from '../components/RivoCity/CityPlanner';
import { WorkerOccupation } from '../types/api';
import { fetchOccupations } from '../services/api';

export const CityPage: React.FC = () => {
  const [occupations, setOccupations] = useState<WorkerOccupation[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchOccupations()
      .then((occs) => setOccupations(occs))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 pb-24 animate-fadeIn">
      {isLoading ? (
        <div className="p-20 text-center text-xs text-[#607080]">
          <span className="w-6 h-6 border-2 border-[#0878D1]/30 border-t-[#0878D1] rounded-full animate-spin inline-block mr-2" />
          Loading Chennai urban planning scenario engine...
        </div>
      ) : (
        <CityPlanner occupations={occupations} />
      )}
    </div>
  );
};
