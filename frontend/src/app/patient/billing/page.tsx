'use client';
import { useState } from 'react';
import useSWR from 'swr';
import { fetcher, getHeaders } from '@/api';
import { CreditCard, AlertCircle, Loader2, CheckCircle, Calendar, ShieldCheck } from 'lucide-react';

interface Invoice {
  invoice_id: string;
  appointment_id: string | null;
  amount_total: number;
  amount_paid: number;
  insurance_adjustment: number;
  status: string;      // pending, paid, overdue, waived
  due_date: string | null;
  created_at: string;
  paid_at: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700 border-amber-200',
  paid: 'bg-green-50 text-green-700 border-green-200',
  overdue: 'bg-red-50 text-red-700 border-red-200',
  waived: 'bg-slate-100 text-slate-500 border-slate-200',
};

function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {[...Array(6)].map((_, i) => (
        <td key={i} className="px-4 py-4">
          <div className="h-3 bg-slate-200 rounded w-full" />
        </td>
      ))}
    </tr>
  );
}

export default function BillingPage() {
  const { data: invoices, error, isLoading, mutate } = useSWR<Invoice[]>('/billing/', fetcher);
  const [payingId, setPayingId] = useState<string | null>(null);

  const handlePay = async (id: string) => {
    setPayingId(id);
    try {
      const res = await fetch(`http://localhost:8000/api/billing/${id}/pay`, {
        method: 'POST',
        headers: getHeaders(),
      });
      if (res.ok) {
        await mutate();
      }
    } finally {
      setPayingId(null);
    }
  };

  const fmt = (n: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

  // You pay = total - insurance (what's actually owed by patient)
  const youPay = (inv: Invoice) => Math.max(0, inv.amount_total - inv.insurance_adjustment);

  const totalOutstanding =
    invoices
      ?.filter((inv) => inv.status === 'pending' || inv.status === 'overdue')
      .reduce((sum, inv) => sum + youPay(inv), 0) ?? 0;

  const totalPaid =
    invoices
      ?.filter((inv) => inv.status === 'paid')
      .reduce((sum, inv) => sum + inv.amount_paid, 0) ?? 0;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Billing</h1>
        <p className="text-slate-500 text-sm mt-1">View invoices and make payments</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white rounded-2xl border border-amber-200 p-6 flex items-center gap-4 shadow-sm">
          <div className="bg-amber-50 p-3 rounded-xl">
            <CreditCard size={24} className="text-amber-600" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Outstanding</p>
            <p className="text-2xl font-extrabold text-amber-700 mt-0.5">{fmt(totalOutstanding)}</p>
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-green-200 p-6 flex items-center gap-4 shadow-sm">
          <div className="bg-green-50 p-3 rounded-xl">
            <CheckCircle size={24} className="text-green-600" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Paid</p>
            <p className="text-2xl font-extrabold text-green-700 mt-0.5">{fmt(totalPaid)}</p>
          </div>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <table className="min-w-full">
            <tbody>
              {[...Array(3)].map((_, i) => <SkeletonRow key={i} />)}
            </tbody>
          </table>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-6 flex items-center gap-3">
          <AlertCircle size={20} className="shrink-0" />
          <p className="text-sm font-medium">Failed to load billing records. Please try again.</p>
        </div>
      ) : !invoices || invoices.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4 text-center bg-white rounded-2xl border border-slate-200">
          <div className="bg-slate-100 rounded-full p-6">
            <CreditCard size={40} className="text-slate-400" />
          </div>
          <h2 className="text-xl font-bold text-slate-700">No billing history</h2>
          <p className="text-slate-500 text-sm max-w-xs">Your invoices will appear here after a visit.</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  {['Invoice Date', 'Total Amount', 'Insurance Covers', 'You Pay', 'Due Date', 'Status', 'Action'].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <tr key={inv.invoice_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3.5 text-slate-700 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <Calendar size={13} className="text-slate-400" />
                        {new Date(inv.created_at).toLocaleDateString(undefined, {
                          year: 'numeric', month: 'short', day: 'numeric',
                        })}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-slate-700 whitespace-nowrap font-medium">
                      {fmt(inv.amount_total)}
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <div className="flex items-center gap-1 text-green-700">
                        <ShieldCheck size={13} />
                        <span>{fmt(inv.insurance_adjustment)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 font-bold text-slate-900 whitespace-nowrap">
                      {fmt(youPay(inv))}
                    </td>
                    <td className="px-4 py-3.5 text-slate-500 text-xs whitespace-nowrap">
                      {inv.due_date
                        ? new Date(inv.due_date).toLocaleDateString(undefined, {
                            month: 'short', day: 'numeric',
                          })
                        : '—'}
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                          STATUS_STYLES[inv.status] ?? STATUS_STYLES.waived
                        }`}
                      >
                        {inv.status.charAt(0).toUpperCase() + inv.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      {(inv.status === 'pending' || inv.status === 'overdue') ? (
                        <button
                          onClick={() => handlePay(inv.invoice_id)}
                          disabled={payingId === inv.invoice_id}
                          className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
                        >
                          {payingId === inv.invoice_id ? (
                            <Loader2 size={12} className="animate-spin" />
                          ) : null}
                          Pay Now
                        </button>
                      ) : inv.status === 'paid' ? (
                        <div className="flex items-center gap-1 text-green-600 text-xs font-medium">
                          <CheckCircle size={12} />
                          Paid {inv.paid_at ? new Date(inv.paid_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''}
                        </div>
                      ) : (
                        <span className="text-slate-300 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

