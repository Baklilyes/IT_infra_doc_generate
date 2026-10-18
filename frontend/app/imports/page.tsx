'use client';

import React from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { Upload } from 'lucide-react';

export default function ImportsPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.imports')}</h1>
          <p className="text-xs text-slate-500">Imports de fichiers Excel, CSV et fichiers de configuration CLI</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <Upload className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <h3 className="text-sm font-semibold text-slate-700">Moteur d'import sécurisé (Lot 4)</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          Le workflow d'import en 10 étapes avec aperçu, mapping des colonnes et détection des conflits sera disponible dans le Lot 4.
        </p>
      </div>
    </div>
  );
}
