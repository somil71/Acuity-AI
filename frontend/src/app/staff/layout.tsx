'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  LayoutDashboard,
  BarChart3,
  LogOut,
  Stethoscope,
  UserCircle,
  Menu,
  X,
} from 'lucide-react';

const NAV_LINKS = [
  { href: '/staff', label: 'Operations Dashboard', icon: LayoutDashboard },
  { href: '/staff/analytics', label: 'Analytics', icon: BarChart3 },
];

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [userId, setUserId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setUserId(localStorage.getItem('userId'));
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.clear();
    router.push('/');
  }, [router]);

  const NavContent = ({ onClick }: { onClick?: () => void }) => (
    <nav className="flex-1 py-6 overflow-y-auto">
      <ul className="space-y-1 px-3">
        {NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || (href !== '/staff' && pathname?.startsWith(href));
          return (
            <li key={href}>
              <Link
                href={href}
                onClick={onClick}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-slate-900 text-white shadow-sm'
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
    <div className="min-h-screen bg-slate-50 flex">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-60 bg-white border-r border-slate-200 fixed inset-y-0 left-0 z-40">
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-200 shrink-0 bg-slate-900 text-white">
          <div className="p-1.5 rounded-lg text-white">
            <Stethoscope size={20} strokeWidth={2.5} />
          </div>
          <span className="font-bold text-lg tracking-tight">Staff Portal</span>
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
            <div className="h-16 flex items-center justify-between px-5 border-b border-slate-200 shrink-0 bg-slate-900 text-white">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg">
                  <Stethoscope size={20} strokeWidth={2.5} />
                </div>
                <span className="font-bold text-lg tracking-tight">Staff Portal</span>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="text-slate-300 hover:text-white p-1 rounded-lg"
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
        <header className="bg-white border-b border-slate-200 sticky top-0 z-30 h-16 flex items-center px-4 md:px-6 shadow-sm md:hidden">
          <button
            className="text-slate-500 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 mr-3"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={22} />
          </button>
          <h1 className="text-lg font-bold tracking-tight text-slate-800">Staff Portal</h1>
        </header>

        <main className="flex-1 p-4 md:p-6 pb-24 md:pb-8">{children}</main>
      </div>
    </div>
  );
}
