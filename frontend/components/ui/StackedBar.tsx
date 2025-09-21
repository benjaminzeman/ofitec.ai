'use client';

import React from 'react';

interface Segment {
  label: string;
  value: number;
  color: string;
}

interface StackedBarProps {
  segments: Segment[];
  height?: number;
  showLegend?: boolean;
}

export default function StackedBar({ segments, height = 16, showLegend = true }: StackedBarProps) {
  const total = segments.reduce((s, seg) => s + seg.value, 0) || 1;

  return (
    <div>
      <div
        className="w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden"
        style={{ height }}
      >
        <div className="flex w-full h-full">
          {segments.map((seg) => (
            <div
              key={seg.label}
              className="h-full"
              style={{ width: `${(seg.value / total) * 100}%`, backgroundColor: seg.color }}
              title={`${seg.label}: ${Math.round((seg.value / total) * 100)}%`}
            />
          ))}
        </div>
      </div>
      {showLegend && (
        <div className="flex flex-wrap gap-3 mt-2">
          {segments.map((seg) => (
            <div
              key={seg.label}
              className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400"
            >
              <span
                className="inline-block w-3 h-3 rounded-sm"
                style={{ backgroundColor: seg.color }}
              />
              <span>{seg.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
