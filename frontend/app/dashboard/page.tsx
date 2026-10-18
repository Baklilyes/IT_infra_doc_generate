'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import { apiFetch, Project } from '@/lib/api';
import {
  FolderKanban,
  CheckCircle2,
  Server,
  AlertTriangle,
  FileText,
  Plus,
  Upload,
  Cpu,
  Search,
  Filter,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  Calendar,
  Building
} from 'lucide-react';

export default function DashboardPage() {
  const { t, locale } = useTranslation();
  const { user } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  // Top Filter state
  const [selectedDate, setSelectedDate] = useState('2026-10-18');
  const [selectedProject, setSelectedProject] = useState('all');
  const [activeKpi, setActiveKpi] = useState('projects');

  useEffect(() => {
    apiFetch<Project[]>('/api/projects')
      .then(setProjects)
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, []);

  // Real metrics calculated from project data
  const projectsCount = projects.length;
  const inValidationCount = projects.filter(p => p.status === 'in_review').length;
  const equipmentCount = 0; // populated in Lot 3
  const anomaliesCount = 0; // populated in Lot 5
  const publishedDocsCount = projects.filter(p => p.status === 'validated').length;

  const filteredProjects = selectedProject === 'all'
    ? projects.slice(0, 5)
    : projects.filter(p => p.id === selectedProject);

  return (
    <div className="space-y-6">
      {/* Top Filter Bar (matching the user reference design) */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">
              Date
            </label>
            <div className="flex items-center space-x-2 border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-xs text-slate-700">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="outline-hidden text-xs text-slate-700"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">
              Projet
            </label>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-700 bg-white outline-hidden focus:ring-1 focus:ring-blue-500 min-w-[200px]"
            >
              <option value="all">Tous les projets ({projects.length})</option>
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.reference} - {p.name}</option>
              ))}
            </select>
          </div>
        </div>

        <button className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition flex items-center space-x-1.5">
          <Filter className="w-3.5 h-3.5" />
          <span>{t('common.apply')}</span>
        </button>
      </div>

      {/* KPI Cards Row (matching reference layout with active borders) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Card 1: Projets */}
        <div
          onClick={() => setActiveKpi('projects')}
          className={`card-kpi cursor-pointer ${
            activeKpi === 'projects' ? 'ring-2 ring-blue-600 border-blue-600 bg-blue-50/20' : ''
          }`}
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
              <FolderKanban className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">{t('dashboard.totalProjects')}</p>
              <p className="text-xl font-bold text-slate-900">{projectsCount}</p>
            </div>
          </div>
        </div>

        {/* Card 2: En validation */}
        <div
          onClick={() => setActiveKpi('validations')}
          className={`card-kpi cursor-pointer ${
            activeKpi === 'validations' ? 'ring-2 ring-blue-600 border-blue-600 bg-blue-50/20' : ''
          }`}
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center text-amber-600">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">{t('dashboard.pendingValidations')}</p>
              <p className="text-xl font-bold text-slate-900">{inValidationCount}</p>
            </div>
          </div>
        </div>

        {/* Card 3: Équipements */}
        <div
          onClick={() => setActiveKpi('equipment')}
          className={`card-kpi cursor-pointer ${
            activeKpi === 'equipment' ? 'ring-2 ring-blue-600 border-blue-600 bg-blue-50/20' : ''
          }`}
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center text-teal-600">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">{t('dashboard.totalEquipment')}</p>
              <p className="text-xl font-bold text-slate-900">{equipmentCount}</p>
            </div>
          </div>
        </div>

        {/* Card 4: Anomalies */}
        <div
          onClick={() => setActiveKpi('anomalies')}
          className={`card-kpi cursor-pointer ${
            activeKpi === 'anomalies' ? 'ring-2 ring-blue-600 border-blue-600 bg-blue-50/20' : ''
          }`}
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">{t('dashboard.missingDataAlerts')}</p>
              <p className="text-xl font-bold text-slate-900">{anomaliesCount}</p>
            </div>
          </div>
        </div>

        {/* Card 5: Documents publiés */}
        <div
          onClick={() => setActiveKpi('docs')}
          className={`card-kpi cursor-pointer ${
            activeKpi === 'docs' ? 'ring-2 ring-blue-600 border-blue-600 bg-blue-50/20' : ''
          }`}
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">Dossiers validés</p>
              <p className="text-xl font-bold text-slate-900">{publishedDocsCount}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Quick Actions & Status Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions Panel */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center space-x-2">
            <span>{t('dashboard.quickActions')}</span>
          </h2>
          <div className="space-y-3">
            <Link
              href="/projects"
              className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-blue-500 hover:bg-blue-50/50 transition group"
            >
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-md bg-blue-100 text-blue-700">
                  <Plus className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-800">
                    {t('dashboard.newProject')}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Créer un nouveau périmètre d'infrastructure
                  </div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition" />
            </Link>

            <Link
              href="/imports"
              className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-blue-500 hover:bg-blue-50/50 transition group"
            >
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-md bg-teal-100 text-teal-700">
                  <Upload className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-800">
                    {t('dashboard.importInventory')}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Fichiers CSV, Excel ou configurations CLI
                  </div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition" />
            </Link>

            <Link
              href="/documents"
              className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-blue-500 hover:bg-blue-50/50 transition group"
            >
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-md bg-purple-100 text-purple-700">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-800">
                    {t('dashboard.generateDoc')}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Export HLD, LLD, Annexes en DOCX et PDF
                  </div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition" />
            </Link>
          </div>
        </div>

        {/* Local AI Status & Security */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs lg:col-span-2">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-blue-600" />
            <span>Environnement Local & Conformité</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-700">Moteur IA Local</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                  Ollama Intégré
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Exécution locale et étanche sans recours aux API cloud externes. Les secrets sont systématiquement masqués avant toute inférence.
              </p>
            </div>

            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-slate-700">Rôle Actif</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                  {user ? t(`roles.${user.role}`) : 'Non connecté'}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Droits stricts appliqués côté backend. Seul le Responsable Technique et le Validateur Final peuvent approuver les jalons documentaires.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Projects Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">
            {t('dashboard.recentProjects')}
          </h3>
          <Link
            href="/projects"
            className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center space-x-1"
          >
            <span>Voir tous les projets</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>

        {projects.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <FolderKanban className="w-12 h-12 mx-auto text-slate-300 mb-2" />
            <p className="text-sm font-medium text-slate-700">Aucun projet d'infrastructure pour l'instant</p>
            <Link
              href="/projects"
              className="mt-3 inline-flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded-lg"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Créer un premier projet</span>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">Référence</th>
                  <th className="px-4 py-3">Nom du projet</th>
                  <th className="px-4 py-3">Client</th>
                  <th className="px-4 py-3">Sites</th>
                  <th className="px-4 py-3">Statut</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredProjects.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3 font-mono font-bold text-blue-700">
                      <Link href={`/projects/${p.id}`} className="hover:underline">
                        {p.reference}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      <Link href={`/projects/${p.id}`} className="hover:text-blue-600">
                        {p.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{p.client_name}</td>
                    <td className="px-4 py-3 font-bold">{p.sites_count}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold border bg-slate-100 text-slate-800 border-slate-200">
                        {t(`projectStatus.${p.status}`)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
