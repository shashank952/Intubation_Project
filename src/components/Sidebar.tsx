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
  ChevronRight,
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

  useEffect(() => {
    document.documentElement.style.setProperty('--sidebar-w', collapsed ? '4rem' : '16rem');
  }, [collapsed]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileOpen) return;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

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

  const renderSidebar = (isCollapsed: boolean) => (
    <div className="flex h-full flex-col bg-white dark:bg-neutral-900">
      <div
        className={clsx(
          'flex items-center border-b-2 border-black dark:border-neutral-600',
          isCollapsed ? 'flex-col gap-3 px-2 py-4' : 'justify-between px-4 py-5'
        )}
      >
        <div className={clsx('flex items-center', isCollapsed ? 'justify-center' : 'gap-3')}>
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-[4px] bg-black shadow-[3px_3px_0_#111111]">
            <Stethoscope className="h-5 w-5 text-white" />
          </div>
          {!isCollapsed && (
            <div>
              <h1 className="text-lg font-bold leading-tight text-gray-800 dark:text-neutral-50">Airway MD</h1>
              <p className="text-[10px] font-medium uppercase tracking-wide text-gray-400 dark:text-neutral-400">
                Clinical Assessment
              </p>
            </div>
          )}
        </div>
        {isCollapsed ? (
          <button
            onClick={() => setCollapsed(false)}
            aria-label="Expand sidebar"
            title="Expand"
            className="hidden h-7 w-7 items-center justify-center rounded-[4px] border-2 border-black bg-brand-500 text-black shadow-[2px_2px_0_#000000] transition-smooth hover:brightness-95 lg:flex"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={() => setCollapsed(true)}
            aria-label="Collapse sidebar"
            title="Collapse"
            className="hidden h-7 w-7 items-center justify-center rounded-[4px] border-2 border-black bg-white text-gray-500 shadow-[2px_2px_0_#000000] transition-smooth hover:bg-gray-100 hover:text-gray-800 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-400 dark:shadow-[2px_2px_0_#3F3F46] dark:hover:bg-neutral-700 dark:hover:text-neutral-200 lg:flex"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      <nav className={clsx('flex-1 space-y-1 overflow-y-auto py-4', isCollapsed ? 'px-2' : 'px-3')}>
        {navItems.map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              onClick={() => setMobileOpen(false)}
              className={clsx(
                'relative flex items-center rounded-[4px] border-2 text-sm font-semibold transition-smooth',
                isCollapsed ? 'justify-center px-2 py-3' : 'gap-3 px-3 py-2.5',
                active
                  ? 'border-black bg-brand-500 text-black shadow-[4px_4px_0_#000000] dark:border-neutral-600 dark:shadow-[4px_4px_0_#3F3F46]'
                  : 'border-black bg-white text-neutral-600 shadow-[3px_3px_0_#000000] hover:bg-neutral-100 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300 dark:shadow-[3px_3px_0_#3F3F46] dark:hover:bg-neutral-700'
              )}
            >
              {active && !isCollapsed && (
                <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-[1px] bg-black" />
              )}
              <Icon className={clsx('h-5 w-5 flex-shrink-0', active ? 'text-black' : 'text-neutral-400 dark:text-neutral-400')} />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className={clsx('space-y-2 border-t-2 border-black py-4 dark:border-neutral-600', isCollapsed ? 'px-2' : 'px-4')}>
        {!isCollapsed && user && (
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-[3px] bg-black text-sm font-semibold text-white shadow-[2px_2px_0_#111111]">
              {user.email.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-gray-700 dark:text-neutral-100">{user.email}</p>
              <p className="text-xs capitalize text-gray-400 dark:text-neutral-400">{user.role}</p>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          title="Sign Out"
          className={clsx(
            'flex w-full items-center rounded-[4px] border-2 border-black bg-white text-sm font-semibold text-neutral-700 shadow-[3px_3px_0_#111111] transition-smooth hover:bg-danger-50 hover:text-danger-700 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-200 dark:shadow-[3px_3px_0_#3F3F46] dark:hover:bg-danger-900/20 dark:hover:text-danger-400',
            isCollapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2'
          )}
        >
          <LogOut className="h-4 w-4" />
          {!isCollapsed && <span>Sign Out</span>}
        </button>
      </div>
    </div>
  );

  return (
    <>
      <button
        onClick={() => setMobileOpen((v) => !v)}
        aria-label="Toggle navigation"
        className="fixed left-3 top-3 z-50 flex h-10 w-10 items-center justify-center rounded-[4px] border-2 border-black bg-white text-neutral-700 shadow-[4px_4px_0_#111111] transition-smooth hover:bg-neutral-100 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-200 dark:shadow-[4px_4px_0_#3F3F46] dark:hover:bg-neutral-700 lg:hidden"
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      <div
        onClick={() => setMobileOpen(false)}
        className={clsx(
          'fixed inset-0 z-30 bg-black/40 backdrop-blur-[1px] transition-opacity duration-300 lg:hidden',
          mobileOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        )}
      />

      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-40 w-64 transform border-r-2 border-black bg-white shadow-elevated transition-transform duration-300 ease-smooth dark:border-neutral-600 dark:bg-neutral-900 lg:hidden',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {renderSidebar(false)}
      </aside>

      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 hidden flex-col border-r-2 border-black bg-white shadow-soft transition-[width] duration-300 ease-smooth dark:border-neutral-600 dark:bg-neutral-900 lg:flex',
          collapsed ? 'w-16' : 'w-64'
        )}
      >
        {renderSidebar(collapsed)}
      </aside>
    </>
  );
}
