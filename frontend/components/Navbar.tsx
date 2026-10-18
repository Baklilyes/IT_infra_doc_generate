'use client';

import React, { useState, useEffect } from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import { apiFetch, HealthResponse } from '@/lib/api';
import { Globe, LogOut, Shield, User as UserIcon, CheckCircle2, AlertTriangle } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { locale, setLocale, t } = useTranslation();
  const { user, logout } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    apiFetch<HealthResponse>('/api/health')
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const getRoleBadgeColor = (role?: string) => {
    switch (role) {
      case 'administrator':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'technical_lead':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'final_validator':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'engineer':
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30 shadow-xs">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
          ID
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-900 leading-tight">
            {t('app.title')}
          </h1>
          <p className="text-xs text-slate-500 font-medium">
            {t('app.subtitle')}
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Backend / AI Status Indicator */}
        <div className="hidden md:flex items-center space-x-2 text-xs bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-full">
          {health?.status === 'healthy' ? (
            <span className="flex items-center text-emerald-700 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
              API Connectée
            </span>
          ) : (
            <span className="flex items-center text-amber-700 font-medium">
              <span className="w-2 h-2 rounded-full bg-amber-500 mr-1.5" />
              Diagnostic
            </span>
          )}
          <span className="text-slate-300">|</span>
          <span className="text-slate-600 font-mono text-[11px]">
            {health?.components.ai_runtime.status === 'operational'
              ? `IA: ${health.components.ai_runtime.model}`
              : 'IA: Local Off'}
          </span>
        </div>

        {/* Language Switcher */}
        <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
          <button
            onClick={() => setLocale('fr')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
              locale === 'fr'
                ? 'bg-white text-blue-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            FR
          </button>
          <button
            onClick={() => setLocale('en')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
              locale === 'en'
                ? 'bg-white text-blue-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            EN
          </button>
        </div>

        {/* User Info & Role Badge */}
        {user && (
          <div className="flex items-center space-x-3 pl-2 border-l border-slate-200">
            <div className="text-right">
              <div className="text-xs font-semibold text-slate-800">
                {user.full_name}
              </div>
              <span
                className={`inline-block text-[10px] font-medium px-2 py-0.5 rounded-full border ${getRoleBadgeColor(
                  user.role
                )}`}
              >
                {t(`roles.${user.role}`)}
              </span>
            </div>

            <button
              onClick={logout}
              title={t('auth.logout')}
              className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
