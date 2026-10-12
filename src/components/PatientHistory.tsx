'use client';

import { useState, useMemo } from 'react';
import { format, parseISO } from 'date-fns';
import {
  History, Search, Download, AlertCircle, Clock, Trash2, Loader2, Eye,
} from 'lucide-react';
import clsx from 'clsx';
import type { PredictionHistory as PredictionHistoryType } from '@/types';
import { exportCsv } from '@/lib/api';

interface PatientHistoryProps {
  predictions: PredictionHistoryType[];
  loading: boolean;
  onDelete?: (id: string) => Promise<void> | void;
  onSelect?: (pred: PredictionHistoryType) => void;
  selectedId?: string | null;
  filter?: 'all' | 'easy' | 'moderate' | 'difficult';
  onFilterChange?: (filter: 'all' | 'easy' | 'moderate' | 'difficult') => void;
}

export default function PatientHistory({
  predictions, loading, onDelete, onSelect, selectedId,
  filter = 'all', onFilterChange,
}: PatientHistoryProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState('');

  const handleDelete = async (id: string, patientId: string) => {
    if (!onDelete) return;
    if (!window.confirm(`Delete record for ${patientId}? This cannot be undone.`)) return;
    setActionError('');
    setDeletingId(id);
    try { await onDelete(id); }
    catch (err) { setActionError(err instanceof Error ? err.message : 'Failed to delete record'); }
    finally { setDeletingId(null); }
  };

  const filtered = useMemo(() => {
    let result = predictions;
    if (filter !== 'all') {
      result = result.filter(p => p.prediction.toLowerCase() === filter);
    }
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      result = result.filter((p) => p.patient_id.toLowerCase().includes(term));
    }
    return result;
  }, [predictions, searchTerm, filter]);

  const handleExport = async () => {
    setExporting(true);
    setExportError('');
    try {
      const blob = await exportCsv();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `airway_predictions_${format(new Date(), 'yyyy-MM-dd')}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Failed to export CSV');
    } finally { setExporting(false); }
  };

  const badge = (prediction: string) => {
    const lower = prediction.toLowerCase();
    if (lower === 'easy') return { bg: 'bg-success-50 dark:bg-success-900/20', text: 'text-success-700 dark:text-success-400', dot: 'bg-success-500' };
    if (lower === 'moderate') return { bg: 'bg-warning-50 dark:bg-warning-900/20', text: 'text-warning-700 dark:text-warning-400', dot: 'bg-warning-500' };
    return { bg: 'bg-danger-50 dark:bg-danger-900/20', text: 'text-danger-700 dark:text-danger-400', dot: 'bg-danger-500' };
  };

  const formatDate = (dateStr: string) => {
    try { return format(parseISO(dateStr), 'MMM dd, yyyy HH:mm'); }
    catch { return dateStr; }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card p-5">
        <div className="skeleton h-6 w-48 mb-4" />
        <div className="skeleton h-10 w-full mb-4" />
        {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton h-12 w-full mb-2" />)}
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card animate-fade-in">
      {/* Header */}
      <div className="px-5 py-4 border-b-2 border-black dark:border-neutral-600 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-[4px] bg-brand-50 dark:bg-brand-950/30 flex items-center justify-center">
            <History className="h-4 w-4 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-50">Patient History</h2>
            <p className="text-xs text-neutral-400 dark:text-neutral-400">{filtered.length} record{filtered.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <button onClick={handleExport} disabled={exporting || predictions.length === 0}
          className={clsx('flex items-center gap-2 px-3 py-1.5 text-sm font-bold rounded-[4px] transition-smooth border-2 border-black dark:border-neutral-600',
            exporting || predictions.length === 0
              ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 cursor-not-allowed'
              : 'bg-brand-500 text-black shadow-[2px_2px_0_#111111] hover:bg-brand-400 hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none')}>
          <Download className="h-4 w-4" />
          {exporting ? 'Exporting...' : 'Export CSV'}
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="mx-5 mb-4 flex gap-1 p-1 bg-neutral-100 dark:bg-neutral-800 rounded-[4px] border-2 border-black dark:border-neutral-600">
        {[
          { value: 'all', label: 'All', count: predictions.length },
          { value: 'easy', label: 'Easy', count: predictions.filter(p => p.prediction.toLowerCase() === 'easy').length },
          { value: 'moderate', label: 'Moderate', count: predictions.filter(p => p.prediction.toLowerCase() === 'moderate').length },
          { value: 'difficult', label: 'Difficult', count: predictions.filter(p => p.prediction.toLowerCase() === 'difficult').length },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => onFilterChange?.(tab.value as 'all' | 'easy' | 'moderate' | 'difficult')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold rounded-[3px] transition-smooth',
              filter === tab.value
                ? 'bg-brand-500 text-black shadow-[2px_2px_0_#111111]'
                : 'text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200/70 dark:hover:bg-neutral-700'
            )}
            disabled={tab.count === 0 && tab.value !== 'all'}
          >
            <span>{tab.label}</span>
            <span className={clsx(
              'px-1.5 py-0.5 text-[10px] font-semibold rounded-sm',
              filter === tab.value
                ? 'bg-white text-black'
                : 'bg-transparent text-neutral-500 dark:text-neutral-400'
            )}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {exportError || actionError ? (
        <div className="mx-5 mt-3 p-2.5 bg-danger-50 dark:bg-danger-900/20 border-2 border-black dark:border-neutral-600 rounded-[4px] flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-danger-500 flex-shrink-0" />
          <p className="text-xs text-danger-600 dark:text-danger-400">{exportError || actionError}</p>
        </div>
      ) : null}

      <div className="p-5">
{/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input type="text" placeholder="Search by Patient ID..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border-2 border-black dark:border-neutral-600 rounded-[4px] focus:outline-none focus:ring-2 focus:ring-brand-300 dark:focus:ring-brand-800 focus:border-brand-400 bg-white dark:bg-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-500 transition-smooth shadow-[5px_5px_0_#111111] dark:shadow-[5px_5px_0_#3F3F46]" />
        </div>

        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <Clock className="h-10 w-10 text-neutral-300 dark:text-neutral-500 mb-3" />
            <p className="text-sm text-neutral-400 dark:text-neutral-400 font-medium">
              {searchTerm ? 'No records match your search' : 'No assessment history yet'}
            </p>
            <p className="text-xs text-neutral-400 dark:text-neutral-400 mt-1">
              {searchTerm ? 'Try a different patient ID' : 'Run an assessment to see results'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-black dark:border-neutral-600">
                  <th className="text-left text-xs font-bold text-neutral-600 dark:text-neutral-300 uppercase tracking-wider pb-3 pr-3">Patient ID</th>
                  <th className="text-left text-xs font-bold text-neutral-600 dark:text-neutral-300 uppercase tracking-wider pb-3 pr-3">Date</th>
                  <th className="text-left text-xs font-bold text-neutral-600 dark:text-neutral-300 uppercase tracking-wider pb-3 pr-3">Result</th>
                  <th className="text-left text-xs font-bold text-neutral-600 dark:text-neutral-300 uppercase tracking-wider pb-3 pr-3">Confidence</th>
                  <th className="text-left text-xs font-bold text-neutral-600 dark:text-neutral-300 uppercase tracking-wider pb-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y-2 divide-black/15 dark:divide-neutral-700">
                {filtered.map((pred) => {
                  const b = badge(pred.prediction);
                  return (
                    <tr key={pred.id}
                      onClick={() => onSelect?.(pred)}
                      className={clsx('transition-smooth cursor-pointer',
                        selectedId === pred.id
                           ? 'bg-brand-100 dark:bg-brand-950/40'
                          : 'hover:bg-neutral-100 dark:hover:bg-neutral-800')}>
                      <td className="py-3 pr-3"><span className="text-sm font-medium text-neutral-800 dark:text-neutral-50">{pred.patient_id}</span></td>
                      <td className="py-3 pr-3"><span className="text-sm text-neutral-500 dark:text-neutral-300">{formatDate(pred.created_at)}</span></td>
                      <td className="py-3 pr-3">
                        <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-[3px] border-2 border-black text-xs font-semibold', b.bg, b.text)}>
                          <span className={clsx('h-1.5 w-1.5 rounded-sm', b.dot)} />
                          {pred.prediction}
                        </span>
                      </td>
                      <td className="py-3 pr-3"><span className="text-sm font-medium text-neutral-700 dark:text-neutral-200 tabular-nums">{(pred.confidence * 100).toFixed(1)}%</span></td>
                      <td className="py-3">
                        <div className="flex items-center gap-1">
                          <button className="h-7 w-7 rounded-[3px] border-2 border-black text-neutral-500 hover:text-black hover:bg-brand-500 transition-smooth flex items-center justify-center" title="View"><Eye className="h-3.5 w-3.5" /></button>
                          {onDelete && (
                            <button onClick={(e) => { e.stopPropagation(); handleDelete(pred.id, pred.patient_id); }} disabled={deletingId === pred.id}
                              className="h-7 w-7 rounded-[3px] border-2 border-black text-neutral-500 hover:text-danger-700 hover:bg-danger-100 transition-smooth flex items-center justify-center disabled:opacity-50" title="Delete">
                              {deletingId === pred.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
