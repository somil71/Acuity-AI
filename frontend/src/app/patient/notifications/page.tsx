'use client';
import useSWR from 'swr';
import { fetcher, getHeaders } from '@/api';
import {
  Bell,
  Clock,
  FlaskConical,
  Pill,
  MessageSquare,
  AlertCircle,
  CheckCheck,
} from 'lucide-react';

interface Notification {
  notification_id: string;
  type: string;
  title: string;
  body: string;
  created_at: string;
  is_read: boolean;
  appointment_id: string | null;
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  eta_update: <Clock size={18} className="text-blue-500" />,
  appointment_reminder: <Bell size={18} className="text-indigo-500" />,
  lab_ready: <FlaskConical size={18} className="text-purple-500" />,
  refill_approved: <Pill size={18} className="text-teal-500" />,
  message_received: <MessageSquare size={18} className="text-green-500" />,
};

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 animate-pulse flex gap-4">
      <div className="w-9 h-9 bg-slate-200 rounded-xl shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3 bg-slate-200 rounded w-3/4" />
        <div className="h-3 bg-slate-200 rounded w-1/2" />
        <div className="h-3 bg-slate-200 rounded w-1/3" />
      </div>
    </div>
  );
}

export default function NotificationsPage() {
  const { data: notifications, error, isLoading, mutate } = useSWR<Notification[]>(
    '/notifications/',
    fetcher,
    { refreshInterval: 5000 }
  );

  const markRead = async (id: string) => {
    // Optimistic
    await mutate(
      notifications?.map((n) => (n.notification_id === id ? { ...n, is_read: true } : n)),
      false
    );
    await fetch(`http://localhost:8000/api/notifications/${id}/read`, {
      method: 'PATCH',
      headers: getHeaders(),
    });
    await mutate();
  };

  const markAllRead = async () => {
    await mutate(
      notifications?.map((n) => ({ ...n, is_read: true })),
      false
    );
    await fetch('http://localhost:8000/api/notifications/read-all', {
      method: 'DELETE',
      headers: getHeaders(),
    });
    await mutate();
  };

  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Notifications</h1>
          <p className="text-slate-500 text-sm mt-1">
            {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAllRead}
            className="flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-4 py-2 rounded-xl transition-colors"
          >
            <CheckCheck size={16} />
            Mark all read
          </button>
        )}
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-2xl p-6 flex items-center gap-3">
          <AlertCircle size={20} className="shrink-0" />
          <p className="text-sm font-medium">Failed to load notifications. Please try again.</p>
        </div>
      )}

      {!isLoading && !error && (!notifications || notifications.length === 0) && (
        <div className="flex flex-col items-center justify-center py-24 gap-4 text-center bg-white rounded-2xl border border-slate-200">
          <div className="bg-slate-100 rounded-full p-6">
            <Bell size={40} className="text-slate-400" />
          </div>
          <h2 className="text-xl font-bold text-slate-700">No notifications yet</h2>
          <p className="text-slate-500 text-sm max-w-xs">
            We'll notify you about appointments, lab results, and messages.
          </p>
        </div>
      )}

      {!isLoading && notifications && notifications.length > 0 && (
        <div className="space-y-3">
          {notifications.map((notif) => (
            <button
              key={notif.notification_id}
              onClick={() => !notif.is_read && markRead(notif.notification_id)}
              className={`w-full text-left rounded-2xl border p-4 flex gap-4 transition-all ${
                notif.is_read
                  ? 'bg-white border-slate-200 hover:border-slate-300 cursor-default'
                  : 'bg-blue-50/60 border-blue-200 border-l-4 border-l-blue-500 hover:bg-blue-50 cursor-pointer'
              }`}
            >
              <div
                className={`shrink-0 w-9 h-9 rounded-xl flex items-center justify-center ${
                  notif.is_read ? 'bg-slate-100' : 'bg-white shadow-sm'
                }`}
              >
                {TYPE_ICONS[notif.type] ?? <Bell size={18} className="text-slate-400" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-semibold ${notif.is_read ? 'text-slate-600' : 'text-slate-900'}`}>
                  {notif.title}
                </p>
                <p className={`text-sm mt-0.5 leading-snug ${notif.is_read ? 'text-slate-400' : 'text-slate-600'}`}>
                  {notif.body}
                </p>
                <p className="text-xs text-slate-400 mt-1.5">
                  {new Date(notif.created_at).toLocaleString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
              {!notif.is_read && (
                <div className="shrink-0 w-2 h-2 rounded-full bg-blue-500 mt-2" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

