'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import {
  LayoutDashboard,
  FolderKanban,
  Server,
  Upload,
  Sliders,
  Network,
  FileText,
  CheckCircle,
  Users,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const { t } = useTranslation();
  const { user } = useAuth();

  const navItems = [
    { href: '/dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard },
    { href: '/projects', labelKey: 'nav.projects', icon: FolderKanban },
    { href: '/inventory', labelKey: 'nav.inventory', icon: Server },
    { href: '/imports', labelKey: 'nav.imports', icon: Upload },
    { href: '/configurations', labelKey: 'nav.configurations', icon: Sliders },
    { href: '/architecture', labelKey: 'nav.architecture', icon: Network },
    { href: '/documents', labelKey: 'nav.documents', icon: FileText },
    { href: '/validations', labelKey: 'nav.validations', icon: CheckCircle },
  ];

  // Administration only for Administrator role
  if (user?.role === 'administrator') {
    navItems.push({ href: '/admin', labelKey: 'nav.admin', icon: Users });
  }

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800">
      <div className="p-4 border-b border-slate-800">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Navigation Principale
        </span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
              <span>{t(item.labelKey)}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800 text-xs text-slate-500">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="font-mono text-[11px]">Serveur Local On-Premise</span>
        </div>
        <p className="mt-1 text-[10px] text-slate-400">v1.0.0 • Sécurisé & Isolé</p>
      </div>
    </aside>
  );
};
