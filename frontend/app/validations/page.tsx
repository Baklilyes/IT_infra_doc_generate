'use client';

import React from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { CheckCircle } from 'lucide-react';

export default function ValidationsPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.validations')}</h1>
          <p className="text-xs text-slate-500">Workflow d'approbation Ingénieur ➔ Responsable Technique ➔ Validateur Final</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <CheckCircle className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <h3 className="text-sm font-semibold text-slate-700">Workflow de validation documentaire (Lot 8)</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          Le cycle strict d'approbation avec motifs de rejet et scellement des versions sera opérationnel au Lot 8.
        </p>
      </div>
    </div>
  );
}
