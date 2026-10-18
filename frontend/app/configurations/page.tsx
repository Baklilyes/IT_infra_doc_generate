'use client';

import React from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { Sliders } from 'lucide-react';

export default function ConfigurationsPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.configurations')}</h1>
          <p className="text-xs text-slate-500">Paramètres techniques structurés et fichiers sources</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <Sliders className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <h3 className="text-sm font-semibold text-slate-700">Configurations techniques (Lot 3 & 4)</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          Les paramètres réseau, routage, firewall, stockage et sauvegarde avec masquage automatique des secrets seront gérés ici.
        </p>
      </div>
    </div>
  );
}
