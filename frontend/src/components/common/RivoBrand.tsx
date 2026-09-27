import React from 'react';
import { RivoLogo, RivoLogoProps } from '../brand/RivoLogo';

export interface RivoBrandProps {
  theme?: 'light' | 'dark';
  size?: 'sm' | 'md' | 'lg';
  showTagline?: boolean;
  onClick?: () => void;
  className?: string;
}

export const RivoBrand: React.FC<RivoBrandProps> = ({
  theme = 'light',
  size = 'md',
  showTagline = true,
  onClick,
  className = '',
}) => {
  return (
    <div
      onClick={onClick}
      className={`inline-block ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      <RivoLogo
        variant={showTagline ? 'full' : 'compact'}
        theme={theme}
        size={size}
      />
    </div>
  );
};
