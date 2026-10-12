'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  History,
  FileText,
  Settings,
  User,
  LogOut,
  Menu,
  X,
  Stethoscope,
  ChevronLeft,
} from 'lucide-react';
import clsx from 'clsx';
import { getUser, logout } from '@/lib/api';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/history', label: 'Patient Records', icon: History },
  { href: '/reports', label: 'Reports', icon: FileText },
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/about', label: 'About', icon: User },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const user = getUser();

  useEffect(() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const isActive = (href: string) => {
    if (href.startsWith('/dashboard')) return pathname === '/dashboard';
    if (href.startsWith('/settings')) return pathname === '/settings';
    if (href.startsWith('/reports')) return pathname === '/reports';
    return pathname === href;
  };

  const sidebarContent = (
    <div className="flex h-full flex-col bg-white dark:bg-neutral-900">
      {/* Brand */}
      <div className="flex items-center justify-between px-4 py-5 border-b-2 border-black dark:border-neutral-600">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-[4px] bg-black flex items-center justify-center shadow-[3px_3px_0_#111111]">
            <Stethoscope className="h-5 w-5 text-white" />
          </div>
          {!collapsed && (
            <div>
                <h1 className="text-lg font-bold text-gray-800 dark:text-neutral-50 leading-tight">
                Airway MD
              </h1>
                <p className="text-[10px] text-gray-400 dark:text-neutral-400 font-medium tracking-wide uppercase">
                Clinical Assessment
              </p>
            </div>
          )}
        </div>
        {!collapsed && (
          <button
            onClick={() => setCollapsed(true)}
            className="hidden lg:flex h-6 w-6 items-center justify-center rounded-[4px] bg-white dark:bg-neutral-800 border-2 border-black dark:border-neutral-600 shadow-[2px_2px_0_#000000] dark:shadow-[2px_2px_0_#3F3F46] text-gray-400 hover:text-gray-600 dark:hover:text-neutral-200 hover:bg-gray-100 dark:hover:bg-neutral-700 transition-smooth"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={clsx(
                'relative flex items-center gap-3 px-3 py-2.5 rounded-[4px] text-sm font-semibold transition-smooth border-2',
                active
                  ? 'bg-brand-500 text-black border-black dark:border-neutral-600 shadow-[4px_4px_0_#000000] dark:shadow-[4px_4px_0_#3F3F46]'
                  : 'bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 border-black dark:border-neutral-600 shadow-[3px_3px_0_#000000] dark:shadow-[3px_3px_0_#3F3F46] hover:bg-neutral-100 dark:hover:bg-neutral-700'
              )}
            >
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-1 rounded-[1px] bg-black" />
              )}
              <Icon className={clsx('h-5 w-5 flex-shrink-0', active ? 'text-black' : 'text-neutral-400 dark:text-neutral-400')} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      {!collapsed && (
        <div className="border-t-2 border-black dark:border-neutral-600 px-4 py-4 space-y-2">
          {user && (
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="h-8 w-8 rounded-[3px] bg-black flex items-center justify-center text-white text-sm font-semibold shadow-[2px_2px_0_#111111]">
                {user.email.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-700 dark:text-neutral-100 truncate">{user.email}</p>
                <p className="text-xs text-gray-400 dark:text-neutral-400 capitalize">{user.role}</p>
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 text-sm font-semibold text-neutral-700 dark:text-neutral-200 hover:text-danger-700 dark:hover:text-danger-400 hover:bg-danger-50 dark:hover:bg-danger-900/20 rounded-[4px] bg-white dark:bg-neutral-800 border-2 border-black dark:border-neutral-600 shadow-[3px_3px_0_#111111] dark:shadow-[3px_3px_0_#3F3F46] transition-smooth"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden h-10 w-10 rounded-[4px] bg-white dark:bg-neutral-800 shadow-[4px_4px_0_#111111] dark:shadow-[4px_4px_0_#3F3F46] border-2 border-black dark:border-neutral-600 flex items-center justify-center text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-smooth"
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>
      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}
      <aside className={clsx('fixed inset-y-0 left-0 z-40 w-64 bg-white dark:bg-neutral-900 shadow-elevated border-r-2 border-black dark:border-neutral-600 transform transition-transform duration-300 ease-in-out lg:hidden', mobileOpen ? 'translate-x-0' : '-translate-x-full')}>
        {sidebarContent}
      </aside>
      <aside className={clsx('hidden lg:flex flex-col fixed inset-y-0 left-0 bg-white dark:bg-neutral-900 border-r-2 border-black dark:border-neutral-600 shadow-soft transition-[width] duration-300 ease-in-out z-30', collapsed ? 'w-16' : 'w-64')}>
        {sidebarContent}
      </aside>
    </>
  );
}
