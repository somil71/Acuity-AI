'use client';
import { useState } from 'react';
import useSWR from 'swr';
import { fetcher } from '@/api';
import { ChevronRight, FileText, AlertCircle } from 'lucide-react';

interface LabResult {
  test_name: string;
  value: string;
  unit: string;
  status: string;
}

interface HealthRecord {
  record_id: string;
  visit_date: string;
  department: string;
  doctor_id: string;
  diagnosis: string;
  doctor_notes: string;
  lab_results?: LabResult[];
}

const DEPT_COLORS: Record<string, string> = {
  Cardiology: 'border-blue-500',
  'General Physician': 'border-green-500',
  Orthopedics: 'border-orange-500',
  Pediatrics: 'border-purple-500',
};

const LAB_STATUS_STYLES: Record<string, string> = {
  normal: 'bg-green-50 text-green-700 border-green-200',
  critical: 'bg-red-50 text-red-700 border-red-200',
  high: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-amber-50 text-amber-700 border-amber-200',
};

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse">
      <div className="flex gap-4">
        <div className="w-1 rounded-full bg-slate-200 self-stretch" />
        <div className="flex-1 space-y-3">
          <div className="h-4 bg-slate-200 rounded w-1/3" />
          <div className="h-3 bg-slate-200 rounded w-1/4" />
          <div className="h-3 bg-slate-200 rounded w-2/3" />
          <div className="h-3 bg-slate-200 rounded w-full" />
        </div>
      </div>
    </div>
  );
}

function RecordCard({ record }: { record: HealthRecord }) {
  const [expanded, setExpanded] = useState(false);
  const borderColor = DEPT_COLORS[record.department] ?? 'border-slate-400';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      <div className="flex">
        <div className={`w-1.5 shrink-0 ${borderColor}`} />
        <div className="flex-1 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {new Date(record.visit_date).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </span>
                <span className="text-slate-300">·</span>
                <span className="text-xs font-medium text-slate-500">{record.department}</span>
              </div>
              <h3 className="mt-1 text-base font-bold text-slate-800">
                {record.diagnosis || 'No diagnosis recorded'}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Dr. {record.doctor_id}</p>
            </div>
            {record.lab_results && record.lab_results.length > 0 && (
              <button
                onClick={() => setExpanded((v) => !v)}
                className="shrink-0 flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-colors"
              >
                {expanded ? 'Hide' : 'Lab Results'}
                <ChevronRight
                  size={14}
                  className={`transition-transform ${expanded ? 'rotate-90' : ''}`}
                />
              </button>
            )}
          </div>

          {record.doctor_notes && (
            <p className="mt-3 text-sm text-slate-600 bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 leading-relaxed">
              {record.doctor_notes}
            </p>
          )}

          {expanded && record.lab_results && record.lab_results.length > 0 && (
            <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    {['Test', 'Value', 'Unit', 'Status'].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {record.lab_results.map((lr, i) => (
                    <tr key={i} className="hover:bg-slate-50/60">
                      <td className="px-4 py-3 font-medium text-slate-800">{lr.test_name}</td>
                      <td className="px-4 py-3 text-slate-700">{lr.value}</td>
                      <td className="px-4 py-3 text-slate-500">{lr.unit}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                            LAB_STATUS_STYLES[lr.status?.toLowerCase()] ??
                            'bg-slate-50 text-slate-600 border-slate-200'
                          }`}
                        >
                          {lr.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RecordsPage() {
  const { data: records, error, isLoading } = useSWR<HealthRecord[]>('/records/', fetcher, {
    refreshInterval: 30000,
  });

  if (isLoading)
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        {[...Array(3)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );

  if (error)
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-6 flex items-center gap-3">
          <AlertCircle size={20} className="shrink-0" />
          <p className="text-sm font-medium">Failed to load health records. Please try again.</p>
        </div>
      </div>
    );

  if (!records || records.length === 0)
    return (
      <div className="max-w-3xl mx-auto flex flex-col items-center justify-center py-24 gap-4 text-center">
        <div className="bg-slate-100 rounded-full p-6">
          <FileText size={40} className="text-slate-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-700">No health records yet</h2>
        <p className="text-slate-500 text-sm max-w-xs">
          Your visit history and clinical notes will appear here after your first appointment.
        </p>
      </div>
    );

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold tracking-tight text-slate-900">Health Records</h2>
        <p className="text-slate-500 text-sm mt-1">
          {records.length} {records.length === 1 ? 'record' : 'records'} found
        </p>
      </div>

      {/* Timeline */}
      <div className="relative space-y-4 before:absolute before:left-[11px] before:top-0 before:bottom-0 before:w-0.5 before:bg-slate-200 pl-8">
        {records.map((record) => (
          <div key={record.record_id} className="relative">
            {/* Timeline dot */}
            <div className="absolute -left-8 top-6 w-3 h-3 rounded-full bg-blue-500 border-2 border-white shadow-sm ring-2 ring-blue-100" />
            <RecordCard record={record} />
          </div>
        ))}
      </div>
    </div>
  );
}

