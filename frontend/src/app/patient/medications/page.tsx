'use client';
import { useState } from 'react';
import useSWR from 'swr';
import { fetcher, getHeaders } from '@/api';
import { Pill, AlertCircle, Loader2, RefreshCw, Clock } from 'lucide-react';

interface Prescription {
  prescription_id: string;
  drug_name: string;
  dosage: string;
  frequency: string;
  prescribed_by: string;
  valid_until: string;
  refill_status?: string;
}

const REFILL_STATUS_STYLES: Record<string, string> = {
  none: 'bg-slate-100 text-slate-600 border-slate-200',
  requested: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  approved: 'bg-green-50 text-green-700 border-green-200',
  dispensed: 'bg-teal-50 text-teal-700 border-teal-200',
};

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse space-y-3">
      <div className="h-5 bg-slate-200 rounded w-1/3" />
      <div className="h-3 bg-slate-200 rounded w-1/4" />
      <div className="h-3 bg-slate-200 rounded w-1/2" />
    </div>
  );
}

function PrescriptionCard({
  rx,
  onRefill,
}: {
  rx: Prescription;
  onRefill: (id: string) => void;
}) {
  const [loading, setLoading] = useState(false);
  const status = rx.refill_status ?? 'none';

  const handleRefill = async () => {
    setLoading(true);
    await onRefill(rx.prescription_id);
    setLoading(false);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-extrabold text-slate-900 tracking-tight">{rx.drug_name}</h3>
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
            <span className="text-sm text-slate-600 font-medium">{rx.dosage}</span>
            <span className="text-slate-300">Â·</span>
            <span className="text-sm text-slate-500">{rx.frequency}</span>
          </div>
        </div>
        <span
          className={`shrink-0 px-2.5 py-1 rounded-full text-xs font-semibold border ${
            REFILL_STATUS_STYLES[status] ?? REFILL_STATUS_STYLES.none
          }`}
        >
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-3">
        <span>Prescribed by <span className="font-medium text-slate-700">{rx.prescribed_by}</span></span>
        <span className="flex items-center gap-1">
          <Clock size={12} />
          Valid until {new Date(rx.valid_until).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
        </span>
      </div>

      <button
        onClick={handleRefill}
        disabled={loading || status === 'requested' || status === 'dispensed'}
        className="flex items-center justify-center gap-2 w-full py-2 rounded-xl text-sm font-semibold border border-blue-200 text-blue-600 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <RefreshCw size={14} />
        )}
        {loading ? 'Requesting...' : 'Request Refill'}
      </button>
    </div>
  );
}

export default function MedicationsPage() {
  const { data: prescriptions, error, isLoading, mutate } = useSWR<Prescription[]>(
    '/prescriptions/',
    fetcher
  );

  const handleRefill = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/prescriptions/${id}/refill`, {
        method: 'POST',
        headers: getHeaders(),
      });
      if (res.ok) {
        await mutate(
          prescriptions?.map((rx) =>
            rx.prescription_id === id ? { ...rx, refill_status: 'requested' } : rx
          ),
          false
        );
      }
    } catch {
      // silent — button re-enables
    }
  };

  if (isLoading)
    return (
      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );

  if (error)
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-6 flex items-center gap-3">
          <AlertCircle size={20} className="shrink-0" />
          <p className="text-sm font-medium">Failed to load prescriptions. Please try again.</p>
        </div>
      </div>
    );

  if (!prescriptions || prescriptions.length === 0)
    return (
      <div className="max-w-4xl mx-auto flex flex-col items-center justify-center py-24 gap-4 text-center">
        <div className="bg-slate-100 rounded-full p-6">
          <Pill size={40} className="text-slate-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-700">No active prescriptions</h2>
        <p className="text-slate-500 text-sm max-w-xs">
          Prescriptions from your doctor will appear here.
        </p>
      </div>
    );

  const now = new Date();
  const active = prescriptions.filter((rx) => new Date(rx.valid_until) >= now);
  const expired = prescriptions.filter((rx) => new Date(rx.valid_until) < now);

  const Section = ({ title, items }: { title: string; items: Prescription[] }) =>
    items.length === 0 ? null : (
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-700 flex items-center gap-2">
          <Pill size={18} className="text-slate-400" />
          {title}
          <span className="text-sm font-medium text-slate-400">({items.length})</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map((rx) => (
            <PrescriptionCard key={rx.prescription_id} rx={rx} onRefill={handleRefill} />
          ))}
        </div>
      </div>
    );

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Medications</h1>
        <p className="text-slate-500 text-sm mt-1">Manage your prescriptions and refill requests</p>
      </div>
      <Section title="Active" items={active} />
      {expired.length > 0 && (
        <div className="opacity-60">
          <Section title="Expired" items={expired} />
        </div>
      )}
    </div>
  );
}

