'use client';

import React from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { FolderKanban, Plus } from 'lucide-react';

export default function ProjectsPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.projects')}</h1>
          <p className="text-xs text-slate-500">Gestion des projets d'infrastructure IT et des sites associés</p>
        </div>
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 transition">
          <Plus className="w-4 h-4" />
          <span>{t('dashboard.newProject')}</span>
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <FolderKanban className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <h3 className="text-sm font-semibold text-slate-700">Périmètre des projets (Lot 2)</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          La création, l'édition, l'arborescence multi-sites et les statuts de projets seront intégrés dans le Lot 2.
        </p>
      </div>
    </div>
  );
}
