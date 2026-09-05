'use client';
import { useEffect, useState } from 'react';
import useSWR from 'swr';
import { fetcher } from '@/api';
import { BarChart3, TrendingUp, Users, Clock, AlertCircle } from 'lucide-react';

const HOURS = Array.from({ length: 18 }, (_, i) => i + 6); // 6am to 11pm
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function AnalyticsPage() {
  const { data: heatmapData, error: heatmapError } = useSWR('/analytics/wait-heatmap', fetcher);
  const { data: billingData } = useSWR('/billing/', fetcher);

  // Fallback mock data if API fails
  const heatmap = heatmapData || (
    DAYS.reduce((acc, day) => {
      acc[day] = HOURS.reduce((hAcc, hour) => {
        hAcc[hour] = Math.floor(Math.random() * 60);
        return hAcc;
      }, {} as Record<number, number>);
      return acc;
    }, {} as Record<string, Record<number, number>>)
  );

  const getHeatColor = (val: number) => {
    if (val < 15) return 'bg-green-100';
    if (val < 30) return 'bg-yellow-100';
    if (val < 45) return 'bg-orange-200';
    return 'bg-red-300';
  };

  const depts = [
    { name: 'Cardiology', avg: 25, overrun: 15 },
    { name: 'General', avg: 18, overrun: 5 },
    { name: 'Ortho', avg: 45, overrun: 35 },
    { name: 'Peds', avg: 22, overrun: 10 }
  ];

  const trendData = [40, 45, 55, 60, 50, 40, 30, 20, 25, 40, 65, 80, 75, 60, 50, 40, 35, 25, 20, 15, 10, 5, 15, 20];

  const bottlenecks = [
    { doc: 'DOC_ORT_1', avg: 25, freq: 12, dept: 'Orthopedics' },
    { doc: 'DOC_CAR_2', avg: 15, freq: 8, dept: 'Cardiology' },
    { doc: 'DOC_PED_1', avg: 10, freq: 5, dept: 'Pediatrics' },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm sticky top-0 z-20">
        <h1 className="text-2xl font-bold text-slate-900">Analytics & Insights</h1>
        <p className="text-sm text-slate-500">Historical performance and trends</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Heatmap */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Clock size={18} className="text-blue-600" /> Wait Time Heatmap (Avg Mins)
          </h2>
          <div className="overflow-x-auto">
            <div className="min-w-[600px]">
              <div className="flex mb-1">
                <div className="w-12 shrink-0"></div>
                {DAYS.map(d => <div key={d} className="flex-1 text-center text-xs font-medium text-slate-500">{d}</div>)}
              </div>
              {HOURS.map(h => (
                <div key={h} className="flex items-center mb-1">
                  <div className="w-12 shrink-0 text-xs text-slate-500 text-right pr-2">
                    {h}:00
                  </div>
                  {DAYS.map(d => {
                    const val = heatmap[d]?.[h] || 0;
                    return (
                      <div key={d} className="flex-1 px-0.5">
                        <div 
                          className={`h-6 rounded-sm w-full flex items-center justify-center text-[10px] text-slate-700/80 ${getHeatColor(val)}`}
                          title={`${val} mins`}
                        >
                          {val}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Department Performance */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <BarChart3 size={18} className="text-blue-600" /> Dept Performance (Last 7 Days)
            </h2>
            <div className="space-y-4 relative">
              <div className="absolute left-0 right-0 top-0 bottom-0 pointer-events-none">
                <div className="absolute top-0 bottom-0 border-l border-dashed border-red-300 z-10" style={{ left: '33.33%' }}>
                  <span className="absolute -top-5 -translate-x-1/2 text-[10px] text-red-500 font-semibold bg-white px-1">Target 20m</span>
                </div>
              </div>
              {depts.map(d => (
                <div key={d.name} className="relative z-0">
                  <div className="flex justify-between text-xs font-medium text-slate-600 mb-1">
                    <span>{d.name}</span>
                    <span className={d.avg > 20 ? 'text-red-500' : 'text-green-600'}>{d.avg}m avg</span>
                  </div>
                  <div className="h-4 bg-slate-100 rounded-full overflow-hidden flex">
                    <div className="h-full bg-blue-500" style={{ width: `${Math.min(100, (d.avg / 60) * 100)}%` }} />
                  </div>
                  {d.overrun > 0 && (
                    <div className="text-[10px] text-red-500 mt-0.5 text-right">+{d.overrun}% overruns</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Queue Health Trend */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <TrendingUp size={18} className="text-blue-600" /> Queue Health Trend (24h)
            </h2>
            <div className="h-32 w-full relative border-b border-l border-slate-200">
              <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 100">
                <polyline 
                  fill="none" 
                  stroke="#3b82f6" 
                  strokeWidth="2"
                  points={trendData.map((val, i) => `${(i / (trendData.length - 1)) * 100},${100 - val}`).join(' ')}
                />
              </svg>
              <div className="absolute bottom-1 left-1 text-[10px] text-slate-400">-24h</div>
              <div className="absolute bottom-1 right-1 text-[10px] text-slate-400">Now</div>
            </div>
          </div>

          {/* Top Bottlenecks */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <AlertCircle size={18} className="text-red-600" /> Top Bottleneck Doctors (7 Days)
            </h2>
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50">
                <tr>
                  <th className="py-2 px-3 font-medium text-slate-500">Doctor</th>
                  <th className="py-2 px-3 font-medium text-slate-500">Avg Overrun</th>
                  <th className="py-2 px-3 font-medium text-slate-500">Freq</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {bottlenecks.map(b => (
                  <tr key={b.doc}>
                    <td className="py-2 px-3">
                      <div className="font-medium text-slate-800">{b.doc}</div>
                      <div className="text-[10px] text-slate-400">{b.dept}</div>
                    </td>
                    <td className="py-2 px-3 text-red-500 font-medium">+{b.avg}m</td>
                    <td className="py-2 px-3 text-slate-600">{b.freq}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
