import React from 'react';
import { DataSourcesView } from '../components/DataSources/DataSourcesView';

export const DataSourcesPage: React.FC = () => {
  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 pb-24 animate-fadeIn">
      <DataSourcesView />
    </div>
  );
};
