'use client';

import React from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { Network } from 'lucide-react';

export default function ArchitecturePage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.architecture')}</h1>
          <p className="text-xs text-slate-500">Schémas SVG physiques et logiques générés à partir des données réelles</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <Network className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <h3 className="text-sm font-semibold text-slate-700">Moteur de schémas SVG (Lot 6)</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          La génération automatique des schémas d'architecture physique, logique et segmentation réseau sera livrée au Lot 6.
        </p>
      </div>
    </div>
  );
}
