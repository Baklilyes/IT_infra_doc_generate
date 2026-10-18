'use client';

import React from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { FileText, Cpu } from 'lucide-react';

export default function DocumentsPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.documents')}</h1>
          <p className="text-xs text-slate-500">Génération du HLD, LLD, Annexes et Dossier de mise en service (DOCX & PDF)</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <FileText className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <h3 className="text-sm font-semibold text-slate-700">Génération documentaire & IA Locale (Lot 7)</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          L'espace d'assistance IA locale (Ollama) et les moteurs d'exportation DOCX/PDF bilingues seront implémentés dans le Lot 7.
        </p>
      </div>
    </div>
  );
}
