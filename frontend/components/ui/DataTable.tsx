import React from 'react';

export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  render?: (value: any, row: any) => React.ReactNode;
}

export interface TableProps {
  columns: TableColumn[];
  data: any[];
  onSort?: (key: string, direction: 'asc' | 'desc') => void;
  sortKey?: string;
  sortDirection?: 'asc' | 'desc';
  loading?: boolean;
  emptyMessage?: string;
  className?: string;
  onRowClick?: (row: any) => void;
  rowClassName?: (row: any) => string;
  // Optional expandable rows support
  isRowExpanded?: (row: any) => boolean;
  renderExpandedRow?: (row: any) => React.ReactNode;
}

export default function DataTable({
  columns,
  data,
  onSort,
  sortKey,
  sortDirection,
  loading = false,
  emptyMessage = 'No hay datos disponibles',
  className = '',
  onRowClick,
  rowClassName,
  isRowExpanded,
  renderExpandedRow,
}: TableProps) {
  const handleSort = (key: string) => {
    if (!onSort) return;
    const newDirection: 'asc' | 'desc' =
      sortKey === key && sortDirection === 'asc' ? 'desc' : 'asc';
    onSort(key, newDirection);
  };

  const getSortIcon = (key: string) => {
    if (sortKey !== key) return '↕️';
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  if (loading) {
    return (
      <div
        className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden ${className}`}
      >
        <div className="p-6">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-slate-200 dark:bg-slate-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden ${className}`}
    >
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-900">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={`px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider ${
                    column.sortable
                      ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors'
                      : ''
                  }`}
                  style={column.width ? { width: column.width } : {}}
                  onClick={() => column.sortable && handleSort(column.key)}
                >
                  <div className="flex items-center gap-2">
                    {column.label}
                    {column.sortable && (
                      <span className="text-slate-400">{getSortIcon(column.key)}</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {data.length > 0 ? (
              data.map((row, index) => {
                const extraRowCls = rowClassName ? rowClassName(row) : '';
                const expanded = Boolean(renderExpandedRow && isRowExpanded && isRowExpanded(row));
                return (
                  <React.Fragment key={index}>
                    <tr
                      className={`hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors ${onRowClick ? 'cursor-pointer' : ''} ${extraRowCls}`}
                      onClick={() => onRowClick && onRowClick(row)}
                    >
                      {columns.map((column) => (
                        <td key={column.key} className="px-6 py-4">
                          {column.render ? column.render(row[column.key], row) : row[column.key]}
                        </td>
                      ))}
                    </tr>
                    {expanded && (
                      <tr className="bg-slate-50/40 dark:bg-slate-900/40">
                        <td colSpan={columns.length} className="px-6 py-4">
                          {renderExpandedRow && renderExpandedRow(row)}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-6 py-12 text-center">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <div className="w-12 h-12 bg-slate-100 dark:bg-slate-700 rounded-xl flex items-center justify-center">
                      <span className="text-slate-400 text-xl">📋</span>
                    </div>
                    <p className="text-slate-500 dark:text-slate-400">{emptyMessage}</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
