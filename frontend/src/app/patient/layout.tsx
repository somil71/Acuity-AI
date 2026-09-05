'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import useSWR from 'swr';
import { fetcher } from '@/api';
import {
  Home,
  FileText,
  Pill,
  MessageSquare,
  CreditCard,
  Star,
  Bell,
  LogOut,
  HeartPulse,
  UserCircle,
  Menu,
  X,
} from 'lucide-react';

const NAV_LINKS = [
  { href: '/patient', label: 'Dashboard', icon: Home },
  { href: '/patient/records', label: 'Records', icon: FileText },
  { href: '/patient/medications', label: 'Medications', icon: Pill },
  { href: '/patient/messages', label: 'Messages', icon: MessageSquare },
  { href: '/patient/billing', label: 'Billing', icon: CreditCard },
  { href: '/patient/reviews', label: 'Reviews', icon: Star },
];

const PAGE_TITLES: Record<string, string> = {
  '/patient': 'Dashboard',
  '/patient/records': 'Health Records',
  '/patient/medications': 'Medications',
  '/patient/messages': 'Messages',
  '/patient/billing': 'Billing',
  '/patient/reviews': 'Reviews',
  '/patient/notifications': 'Notifications',
};

export default function PatientLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [userId, setUserId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setUserId(localStorage.getItem('userId'));
  }, []);

  const { data: unreadData } = useSWR('/notifications/unread-count', fetcher, {
    refreshInterval: 10000,
  });
  const unreadCount: number = unreadData?.unread_count ?? 0;

  const handleLogout = useCallback(() => {
    localStorage.clear();
    router.push('/');
  }, [router]);

  const pageTitle = PAGE_TITLES[pathname] ?? 'Patient Portal';

  const NavContent = ({ onClick }: { onClick?: () => void }) => (
    <nav className="flex-1 py-6 overflow-y-auto">
      <ul className="space-y-1 px-3">
        {NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <li key={href}>
              <Link
                href={href}
                onClick={onClick}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <Icon size={18} strokeWidth={isActive ? 2.5 : 2} />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-100 flex">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-60 bg-white border-r border-slate-200 fixed inset-y-0 left-0 z-40">
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-200 shrink-0">
          <div className="bg-blue-600 p-1.5 rounded-lg text-white">
            <HeartPulse size={20} strokeWidth={2.5} />
          </div>
          <span className="font-bold text-lg tracking-tight text-blue-700">PulsePredict</span>
        </div>

        <NavContent />

        <div className="border-t border-slate-200 p-4 shrink-0 space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-600 bg-slate-100 px-3 py-2 rounded-xl border border-slate-200">
            <UserCircle size={18} className="text-slate-400 shrink-0" />
            <span className="truncate">{userId ?? '...'}</span>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-red-600 hover:bg-red-50 px-3 py-2 rounded-xl transition-colors"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative z-10 flex flex-col w-72 bg-white h-full shadow-2xl">
            <div className="h-16 flex items-center justify-between px-5 border-b border-slate-200 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="bg-blue-600 p-1.5 rounded-lg text-white">
                  <HeartPulse size={20} strokeWidth={2.5} />
                </div>
                <span className="font-bold text-lg tracking-tight text-blue-700">PulsePredict</span>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>

            <NavContent onClick={() => setSidebarOpen(false)} />

            <div className="border-t border-slate-200 p-4 shrink-0 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-600 bg-slate-100 px-3 py-2 rounded-xl border border-slate-200">
                <UserCircle size={18} className="text-slate-400 shrink-0" />
                <span className="truncate">{userId ?? '...'}</span>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-red-600 hover:bg-red-50 px-3 py-2 rounded-xl transition-colors"
              >
                <LogOut size={16} />
                Logout
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Main content area */}
      <div className="flex-1 flex flex-col md:ml-60 min-h-screen">
        {/* Top Bar */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-30 h-16 flex items-center justify-between px-4 md:px-6 shadow-sm">
          <div className="flex items-center gap-3">
            <button
              className="md:hidden text-slate-500 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu size={22} />
            </button>
            <h1 className="text-lg font-bold tracking-tight text-slate-800">{pageTitle}</h1>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/patient/notifications"
              className="relative text-slate-500 hover:text-blue-600 p-2 rounded-full hover:bg-blue-50 transition-colors"
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1 leading-none">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </Link>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-8 pb-24 md:pb-8">{children}</main>
      </div>

      {/* Mobile Bottom Tab Bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t border-slate-200 flex items-stretch">
        {NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex-1 flex flex-col items-center justify-center py-2 gap-0.5 text-[10px] font-medium transition-colors ${
                isActive ? 'text-blue-600' : 'text-slate-400 hover:text-slate-600'
              }`}
            >
              <Icon size={20} strokeWidth={isActive ? 2.5 : 1.8} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

