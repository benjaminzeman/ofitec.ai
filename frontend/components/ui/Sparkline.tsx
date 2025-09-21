'use client';

import React from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fill?: string;
}

export default function Sparkline({
  data,
  width = 120,
  height = 36,
  color = '#65a30d',
  fill = 'none',
}: SparklineProps) {
  if (!data || data.length === 0) return <div className="h-9" />;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const points = data
    .map((d, i) => {
      const x = i * step;
      const y = height - ((d - min) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline
        fill={fill}
        stroke={color}
        strokeWidth="2"
        points={points}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
