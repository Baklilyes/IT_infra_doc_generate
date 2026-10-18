'use client';

import React, { useState } from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import { Shield, KeyRound, User, Lock, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const { t, locale, setLocale } = useTranslation();
  const { login } = useAuth();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('AdminStrongPassword123!');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(username, password);
    } catch (err: any) {
      setError(err.message || t('auth.invalidCredentials'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const setDemoAccount = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-700 to-indigo-800 p-6 text-white text-center relative">
          <div className="absolute top-4 right-4 flex bg-blue-900/60 rounded-lg p-0.5 border border-blue-400/30 text-xs font-semibold">
            <button
              onClick={() => setLocale('fr')}
              className={`px-2 py-0.5 rounded ${locale === 'fr' ? 'bg-white text-blue-900' : 'text-blue-100'}`}
            >
              FR
            </button>
            <button
              onClick={() => setLocale('en')}
              className={`px-2 py-0.5 rounded ${locale === 'en' ? 'bg-white text-blue-900' : 'text-blue-100'}`}
            >
              EN
            </button>
          </div>

          <div className="w-14 h-14 bg-white/10 rounded-xl flex items-center justify-center mx-auto mb-3 backdrop-blur-xs border border-white/20">
            <Shield className="w-8 h-8 text-blue-200" />
          </div>
          <h2 className="text-xl font-bold">{t('auth.loginTitle')}</h2>
          <p className="text-xs text-blue-200 mt-1">{t('auth.loginSubtitle')}</p>
        </div>

        {/* Form Body */}
        <div className="p-6 md:p-8 space-y-6">
          {error && (
            <div className="flex items-start space-x-2 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('auth.username')}
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-hidden"
                  placeholder="admin"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('auth.password')}
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-hidden"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-sm shadow-sm transition-all focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:opacity-50"
            >
              {isSubmitting ? t('auth.signingIn') : t('auth.signIn')}
            </button>
          </form>

          {/* Quick Demo Credentials Tabs */}
          <div className="pt-4 border-t border-slate-200">
            <span className="block text-xs font-semibold text-slate-600 mb-2">
              {t('auth.demoCredentialsTitle')}
            </span>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => setDemoAccount('admin', 'AdminStrongPassword123!')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-slate-50 transition"
              >
                <div className="font-semibold text-purple-700">{t('roles.administrator')}</div>
                <div className="text-[10px] text-slate-500">admin</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('engineer_demo', 'EngineerPass123!')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-slate-50 transition"
              >
                <div className="font-semibold text-blue-700">{t('roles.engineer')}</div>
                <div className="text-[10px] text-slate-500">engineer_demo</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('lead_demo', 'LeadPass123!')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-slate-50 transition"
              >
                <div className="font-semibold text-amber-700">{t('roles.technical_lead')}</div>
                <div className="text-[10px] text-slate-500">lead_demo</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('validator_demo', 'ValPass123!')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-slate-50 transition"
              >
                <div className="font-semibold text-emerald-700">{t('roles.final_validator')}</div>
                <div className="text-[10px] text-slate-500">validator_demo</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
