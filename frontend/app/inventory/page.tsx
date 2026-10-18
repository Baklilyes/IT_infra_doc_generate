'use client';

import React from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { Server, Plus } from 'lucide-react';

export default function InventoryPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.inventory')}</h1>
          <p className="text-xs text-slate-500">Équipements réseau, sécurité, serveurs, stockage et virtualisation</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <Server className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <h3 className="text-sm font-semibold text-slate-700">Inventaire technique (Lot 3)</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          L'inventaire multi-familles (switches, routeurs, firewalls, serveurs, hyperviseurs) et les interfaces seront intégrés dans le Lot 3.
        </p>
      </div>
    </div>
  );
}
