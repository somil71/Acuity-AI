'use client';
import React, { useEffect, useState } from 'react';
import useSWR, { mutate as globalMutate } from 'swr';
import { fetcher } from '@/api';
import { 
  Activity, 
  AlertTriangle, 
  ArrowDown, 
  ArrowRight, 
  ArrowUp, 
  CheckCircle, 
  Clock, 
  Minus, 
  RefreshCw, 
  Syringe, 
  Users, 
  Sparkles,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

interface DeptHealth {
  department: string;
  score: number;
  state: 'HEALTHY' | 'MODERATE' | 'BUSY' | 'CRITICAL';
  active_count: number;
  arrivals_60m: number;
  components: { census_pressure: number; arrival_velocity: number; acuity_load: number };
  dominant_factor: string;
  computed_at: string;
}

interface CongestionForecast {
  department: string;
  current_state: string;
  horizons: {
    '30m': { tier: string; confidence: number; color: string; label: string };
    '60m': { tier: string; confidence: number; color: string; label: string };
    '120m': { tier: string; confidence: number; color: string; label: string };
  };
  model_source: string;
}

export default function StaffDashboard() {
  const [userId, setUserId] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  
  useEffect(() => {
    setUserId(localStorage.getItem('userId'));
  }, []);

  const refreshInterval = 15000;

  const { data: queueHealth, isValidating: loadingHealth } = useSWR<DeptHealth[]>('/queue-health', fetcher, { refreshInterval });
  const { data: congestion, isValidating: loadingCongestion } = useSWR<CongestionForecast[]>('/congestion/live', fetcher, { refreshInterval });
  const { data: bottlenecks, isValidating: loadingBottlenecks } = useSWR<any>('/bottleneck/now', fetcher, { refreshInterval });
  const { data: queue, isValidating: loadingQueue, mutate: mutateQueue } = useSWR<any[]>(
    userId ? `/appointments/doctor/${userId}/queue` : null, 
    fetcher, 
    { refreshInterval }
  );

  const isRefreshing = loadingHealth || loadingCongestion || loadingBottlenecks || loadingQueue;

  const handleManualRefresh = () => {
    globalMutate(() => true, undefined, { revalidate: true });
    setLastRefresh(new Date());
  };

  const injectEmergency = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!userId) return;
    const formData = new FormData(e.currentTarget);
    const department = formData.get('department') as string;
    const duration = parseInt(formData.get('duration') as string);
    const token = localStorage.getItem('token');
    
    await fetch('http://localhost:8000/api/appointments/emergency', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ doctor_id: userId, department, estimated_duration: duration })
    });
    handleManualRefresh();
    (e.target as HTMLFormElement).reset();
  };

  const checkout = async (id: string) => {
    const token = localStorage.getItem('token');
    await fetch(`http://localhost:8000/api/appointments/${id}/checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    });
    mutateQueue();
  };

  const getStateColors = (state: string) => {
    switch (state) {
      case 'HEALTHY': return 'bg-green-100 text-green-700 border-green-200';
      case 'MODERATE': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'BUSY': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'CRITICAL': return 'bg-red-100 text-red-700 border-red-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getBarColor = (state: string) => {
    switch (state) {
      case 'HEALTHY': return 'bg-green-500';
      case 'MODERATE': return 'bg-yellow-500';
      case 'BUSY': return 'bg-orange-500';
      case 'CRITICAL': return 'bg-red-500';
      default: return 'bg-slate-500';
    }
  };

  if (!userId) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm sticky top-0 z-20">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Operations Dashboard</h1>
          <p className="text-sm text-slate-500 flex items-center gap-2">
            <Clock size={14} /> Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <button 
          onClick={handleManualRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
          {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
        </button>
      </div>

      {/* Section A: Queue Health Gauges */}
      <section>
        <h2 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
          <Activity size={18} className="text-blue-600" /> Queue Health
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {queueHealth ? queueHealth.map((qh) => (
            <div key={qh.department} className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-slate-700">{qh.department}</h3>
                <span className={`px-2 py-1 text-xs font-bold rounded-md border uppercase ${getStateColors(qh.state)}`}>
                  {qh.state}
                </span>
              </div>
              <div className="flex items-end gap-2 mb-4">
                <span className="text-4xl font-extrabold text-slate-900">{qh.score}</span>
                <span className="text-sm text-slate-500 mb-1">/100</span>
              </div>
              <div className="space-y-2 mt-auto">
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-24 text-slate-500">Pressure</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full ${getBarColor(qh.state)}`} style={{ width: `${Math.min(100, qh.components.census_pressure * 100)}%` }} />
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-24 text-slate-500">Velocity</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full ${getBarColor(qh.state)}`} style={{ width: `${Math.min(100, qh.components.arrival_velocity * 100)}%` }} />
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-24 text-slate-500">Acuity</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full ${getBarColor(qh.state)}`} style={{ width: `${Math.min(100, qh.components.acuity_load * 100)}%` }} />
                  </div>
                </div>
              </div>
            </div>
          )) : (
            Array(4).fill(0).map((_, i) => <div key={i} className="bg-white rounded-2xl h-48 border border-slate-200 animate-pulse" />)
          )}
        </div>
      </section>

      {/* Section B: Congestion Forecast */}
      <section>
        <h2 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
          <Clock size={18} className="text-blue-600" /> Congestion Forecast
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {congestion ? congestion.map((cf) => {
            const tiers = ['HEALTHY', 'MODERATE', 'BUSY', 'CRITICAL'];
            const getArrow = (current: string, future: string) => {
              const curIdx = tiers.indexOf(current);
              const futIdx = tiers.indexOf(future);
              if (futIdx > curIdx) return <ArrowUp size={14} className="text-red-500" />;
              if (futIdx < curIdx) return <ArrowDown size={14} className="text-green-500" />;
              return <Minus size={14} className="text-slate-400" />;
            };
            return (
              <div key={cf.department} className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
                <h3 className="font-semibold text-slate-700 mb-3">{cf.department}</h3>
                <div className="space-y-3">
                  {['30m', '60m', '120m'].map((horizon) => {
                    const hData = cf.horizons[horizon as keyof typeof cf.horizons];
                    return (
                      <div key={horizon} className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-500 w-12">{horizon}</span>
                        <div className="flex items-center gap-2">
                          {getArrow(cf.current_state, hData.tier)}
                          <div className={`px-2 py-1 text-xs font-bold rounded border uppercase min-w-[80px] text-center ${getStateColors(hData.tier)}`}>
                            {hData.tier}
                          </div>
                          <span className="text-xs text-slate-400 w-8 text-right">{Math.round(hData.confidence * 100)}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          }) : (
            Array(4).fill(0).map((_, i) => <div key={i} className="bg-white rounded-2xl h-40 border border-slate-200 animate-pulse" />)
          )}
        </div>
      </section>

      {/* Section C: Bottleneck Alerts */}
      <section>
        {bottlenecks && Object.keys(bottlenecks).length > 0 ? (
          <div className="bg-orange-50 rounded-2xl border border-orange-200 overflow-hidden shadow-sm">
            <div className="bg-orange-100 px-5 py-3 border-b border-orange-200 flex items-center gap-2 text-orange-800 font-semibold">
              <AlertTriangle size={18} /> {Object.keys(bottlenecks).length} active bottleneck(s) detected
            </div>
            <div className="p-0">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-orange-50">
                  <tr>
                    <th className="px-5 py-3 font-medium text-orange-800">Doctor / Dept</th>
                    <th className="px-5 py-3 font-medium text-orange-800">Overrun</th>
                    <th className="px-5 py-3 font-medium text-orange-800">Queue Behind</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-orange-100 bg-white">
                  {Object.entries(bottlenecks).map(([docId, data]: [string, any]) => (
                    <tr key={docId}>
                      <td className="px-5 py-3 font-medium text-slate-800">{docId}</td>
                      <td className="px-5 py-3 text-red-600 font-semibold">{data.overrun_ratio?.toFixed(1) || 'N/A'}x</td>
                      <td className="px-5 py-3 text-slate-600">{data.queue_behind || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-green-50 border border-green-200 rounded-2xl p-4 flex items-center gap-2 text-green-700 shadow-sm">
            <CheckCircle size={18} /> All queues flowing normally. No bottlenecks detected.
          </div>
        )}
      </section>

      {/* Section D & E: Queue and Emergency */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <Users size={18} className="text-blue-600" /> Live Patient Queue
          </h2>
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-medium text-slate-500 uppercase tracking-wider text-xs">Patient</th>
                  <th className="px-4 py-3 font-medium text-slate-500 uppercase tracking-wider text-xs">Scheduled</th>
                  <th className="px-4 py-3 font-medium text-slate-500 uppercase tracking-wider text-xs">Status</th>
                  <th className="px-4 py-3 font-medium text-slate-500 uppercase tracking-wider text-xs text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {queue?.map((q: any) => {
                  const schedTime = new Date(q.scheduled_time);
                  const isPastDue = schedTime < new Date() && !q.actual_start_time;
                  const waitMins = isPastDue ? Math.floor((new Date().getTime() - schedTime.getTime()) / 60000) : 0;
                  
                  return (
                    <React.Fragment key={q.appointment_id}>
                      <tr 
                        className="hover:bg-slate-50 transition-colors cursor-pointer"
                        onClick={() => setExpandedRow(expandedRow === q.appointment_id ? null : q.appointment_id)}
                      >
                        <td className="px-4 py-4 font-medium text-slate-900 flex items-center gap-2">
                          {expandedRow === q.appointment_id ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronRight size={16} className="text-slate-400" />}
                          {q.patient_id}
                        </td>
                        <td className="px-4 py-4 text-slate-600">
                          {schedTime.toLocaleTimeString([], {timeStyle: 'short'})}
                          {waitMins > 0 && <span className="ml-2 text-xs text-red-500 font-medium">({waitMins}m late)</span>}
                        </td>
                        <td className="px-4 py-4">
                          {!q.actual_start_time ? (
                            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Scheduled
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> In Progress
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-4 text-right">
                          <button 
                            onClick={(e) => { e.stopPropagation(); checkout(q.appointment_id); }}
                            className="text-blue-600 hover:text-blue-800 font-medium px-3 py-1.5 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
                          >
                            Checkout
                          </button>
                        </td>
                      </tr>
                      {expandedRow === q.appointment_id && q.shap_explanation && (
                        <tr className="bg-slate-50 border-b border-slate-100">
                          <td colSpan={4} className="px-4 py-3">
                            <div className="pl-6 space-y-2">
                              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 mb-2">
                                <Sparkles size={14} className="text-purple-500" /> Wait Time Factors
                              </div>
                              {q.shap_explanation.factors?.map((f: any, i: number) => (
                                <div key={i} className="flex items-center justify-between max-w-sm text-sm">
                                  <span className="text-slate-600">{f.feature}</span>
                                  <span className={`font-medium ${f.direction === 'increases_wait' ? 'text-red-600' : 'text-green-600'}`}>
                                    {f.direction === 'increases_wait' ? '+' : ''}{f.impact_minutes}m
                                  </span>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
                {(!queue || queue.length === 0) && !loadingQueue && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                      No appointments in queue
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <Syringe size={18} className="text-red-600" /> Emergency Injection
          </h2>
          <form onSubmit={injectEmergency} className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Department</label>
              <select name="department" className="w-full bg-slate-50 border border-slate-200 text-slate-700 py-2 px-3 rounded-lg text-sm font-medium focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none">
                <option value="Cardiology">Cardiology</option>
                <option value="General Physician">General Physician</option>
                <option value="Orthopedics">Orthopedics</option>
                <option value="Pediatrics">Pediatrics</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Est. Duration (mins)</label>
              <input 
                type="number" 
                name="duration" 
                defaultValue={30}
                className="w-full bg-slate-50 border border-slate-200 text-slate-700 py-2 px-3 rounded-lg text-sm font-medium focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
              />
            </div>
            <button type="submit" className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors shadow-sm shadow-red-600/20">
              Inject Emergency
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
