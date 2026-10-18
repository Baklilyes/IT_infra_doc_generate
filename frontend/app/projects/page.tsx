'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import { apiFetch, Project, ProjectStatus } from '@/lib/api';
import {
  FolderKanban,
  Plus,
  Search,
  Filter,
  Copy,
  Archive,
  Trash2,
  Calendar,
  Building,
  User,
  ExternalLink,
  X,
  AlertCircle,
  LayoutGrid,
  List as ListIcon,
  CheckCircle2
} from 'lucide-react';

export default function ProjectsPage() {
  const { t, locale } = useTranslation();
  const { user } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showArchived, setShowArchived] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDuplicateModal, setShowDuplicateModal] = useState(false);
  const [targetProject, setTargetProject] = useState<Project | null>(null);

  // Create Project Form
  const [ref, setRef] = useState('');
  const [name, setName] = useState('');
  const [clientName, setClientName] = useState('');
  const [leadName, setLeadName] = useState(user?.full_name || '');
  const [contributors, setContributors] = useState('');
  const [docLang, setDocLang] = useState<'fr' | 'en'>('fr');
  const [initialSite, setInitialSite] = useState('');
  const [scope, setScope] = useState('');
  const [description, setDescription] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Duplicate Form
  const [newRef, setNewRef] = useState('');
  const [newName, setNewName] = useState('');

  const fetchProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      let query = `?is_archived=${showArchived}`;
      if (search) query += `&search=${encodeURIComponent(search)}`;
      if (statusFilter !== 'all') query += `&status=${statusFilter}`;
      
      const data = await apiFetch<Project[]>(`/api/projects${query}`);
      setProjects(data);
    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement des projets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [search, statusFilter, showArchived]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);
    try {
      await apiFetch<Project>('/api/projects', {
        method: 'POST',
        body: JSON.stringify({
          reference: ref,
          name,
          client_name: clientName,
          lead_name: leadName || user?.full_name || 'Ingénieur',
          contributors: contributors || undefined,
          description: description || undefined,
          scope: scope || undefined,
          document_language: docLang,
          initial_site_name: initialSite || undefined,
        }),
      });

      setShowCreateModal(false);
      // Reset form
      setRef('');
      setName('');
      setClientName('');
      setDescription('');
      setScope('');
      setInitialSite('');
      fetchProjects();
    } catch (err: any) {
      setFormError(err.message || 'Erreur lors de la création');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDuplicateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetProject) return;
    setFormError(null);
    setIsSubmitting(true);
    try {
      await apiFetch(`/api/projects/${targetProject.id}/duplicate`, {
        method: 'POST',
        body: JSON.stringify({
          new_reference: newRef,
          new_name: newName || undefined,
        }),
      });
      setShowDuplicateModal(false);
      setTargetProject(null);
      fetchProjects();
    } catch (err: any) {
      setFormError(err.message || 'Erreur lors de la duplication');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleArchive = async (proj: Project, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiFetch(`/api/projects/${proj.id}/archive`, { method: 'POST' });
      fetchProjects();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de l’archivage');
    }
  };

  const handleDeleteProject = async (proj: Project, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(t('projects.deleteConfirm'))) return;
    try {
      await apiFetch(`/api/projects/${proj.id}`, { method: 'DELETE' });
      fetchProjects();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de la suppression');
    }
  };

  const openDuplicate = (proj: Project, e: React.MouseEvent) => {
    e.stopPropagation();
    setTargetProject(proj);
    setNewRef(`${proj.reference}-COPY`);
    setNewName(`${proj.name} - Copie`);
    setShowDuplicateModal(true);
  };

  const getStatusBadge = (status: ProjectStatus) => {
    const styles: Record<ProjectStatus, string> = {
      draft: 'bg-slate-100 text-slate-700 border-slate-300',
      in_preparation: 'bg-blue-100 text-blue-800 border-blue-200',
      in_review: 'bg-amber-100 text-amber-800 border-amber-200',
      validated: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      closed: 'bg-gray-100 text-gray-700 border-gray-300',
    };
    return (
      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${styles[status]}`}>
        {t(`projectStatus.${status}`)}
      </span>
    );
  };

  const canEdit = user?.role === 'administrator' || user?.role === 'engineer';

  return (
    <div className="space-y-6">
      {/* Page Title & Main Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('projects.title')}</h1>
          <p className="text-xs text-slate-500 mt-0.5">{t('projects.subtitle')}</p>
        </div>
        {canEdit && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 transition self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>{t('projects.newProjectBtn')}</span>
          </button>
        )}
      </div>

      {/* Filter and Control Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
          {/* Search Input */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('projects.searchPlaceholder')}
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-hidden focus:ring-1 focus:ring-blue-500 bg-white"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-700 bg-white outline-hidden focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">{t('projects.allStatuses')}</option>
            <option value="draft">{t('projectStatus.draft')}</option>
            <option value="in_preparation">{t('projectStatus.in_preparation')}</option>
            <option value="in_review">{t('projectStatus.in_review')}</option>
            <option value="validated">{t('projectStatus.validated')}</option>
            <option value="closed">{t('projectStatus.closed')}</option>
          </select>

          {/* Archive Toggle */}
          <button
            onClick={() => setShowArchived(!showArchived)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition ${
              showArchived
                ? 'bg-amber-50 text-amber-800 border-amber-300 font-semibold'
                : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
            }`}
          >
            {showArchived ? t('projects.showArchived') : t('projects.hideArchived')}
          </button>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-md transition ${
              viewMode === 'grid' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-500 hover:text-slate-900'
            }`}
            title="Vue Grille"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`p-1.5 rounded-md transition ${
              viewMode === 'table' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-500 hover:text-slate-900'
            }`}
            title="Vue Tableau"
          >
            <ListIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs text-slate-500">{t('common.loading')}</p>
        </div>
      ) : projects.length === 0 ? (
        /* Empty state */
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
          <FolderKanban className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <h3 className="text-sm font-semibold text-slate-700">{t('projects.emptyTitle')}</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">{t('projects.emptySubtitle')}</p>
          {canEdit && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs inline-flex items-center space-x-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>{t('projects.newProjectBtn')}</span>
            </button>
          )}
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((p) => (
            <Link
              key={p.id}
              href={`/projects/${p.id}`}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:shadow-md hover:border-blue-400 transition flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                    {p.reference}
                  </span>
                  {getStatusBadge(p.status)}
                </div>

                <h3 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition line-clamp-1">
                  {p.name}
                </h3>

                <p className="text-xs text-slate-500 mt-1 flex items-center space-x-1">
                  <Building className="w-3.5 h-3.5 text-slate-400" />
                  <span>{p.client_name}</span>
                </p>

                {p.scope && (
                  <p className="text-[11px] text-slate-600 mt-3 line-clamp-2 bg-slate-50 p-2 rounded border border-slate-100">
                    {p.scope}
                  </p>
                )}
              </div>

              <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center space-x-3 text-[11px]">
                  <span><strong>{p.sites_count}</strong> {t('projects.sitesCount')}</span>
                  <span>•</span>
                  <span className="font-mono uppercase font-bold text-slate-600">{p.document_language}</span>
                </div>

                <div className="flex items-center space-x-1">
                  {canEdit && (
                    <>
                      <button
                        onClick={(e) => openDuplicate(p, e)}
                        title={t('projects.duplicate')}
                        className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleToggleArchive(p, e)}
                        title={p.is_archived ? t('projects.unarchive') : t('projects.archive')}
                        className="p-1.5 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded"
                      >
                        <Archive className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteProject(p, e)}
                        title={t('projects.delete')}
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">{t('projects.reference')}</th>
                  <th className="px-4 py-3">{t('projects.name')}</th>
                  <th className="px-4 py-3">{t('projects.client')}</th>
                  <th className="px-4 py-3">{t('projects.sitesCount')}</th>
                  <th className="px-4 py-3">{t('projects.lead')}</th>
                  <th className="px-4 py-3">{t('common.status')}</th>
                  <th className="px-4 py-3 text-right">{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {projects.map((p) => (
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
                    <td className="px-4 py-3 text-slate-500">{p.lead_name}</td>
                    <td className="px-4 py-3">{getStatusBadge(p.status)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end space-x-1">
                        {canEdit && (
                          <>
                            <button
                              onClick={(e) => openDuplicate(p, e)}
                              title={t('projects.duplicate')}
                              className="p-1 text-slate-400 hover:text-blue-600 rounded"
                            >
                              <Copy className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={(e) => handleToggleArchive(p, e)}
                              title={p.is_archived ? t('projects.unarchive') : t('projects.archive')}
                              className="p-1 text-slate-400 hover:text-amber-600 rounded"
                            >
                              <Archive className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={(e) => handleDeleteProject(p, e)}
                              title={t('projects.delete')}
                              className="p-1 text-slate-400 hover:text-red-600 rounded"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal Nouveau Projet */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <FolderKanban className="w-4 h-4 text-blue-600" />
                <span>{t('projects.newProjectBtn')}</span>
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateProject} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    {t('projects.reference')} *
                  </label>
                  <input
                    type="text"
                    required
                    value={ref}
                    onChange={(e) => setRef(e.target.value)}
                    placeholder="PRJ-2026-001"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    {t('projects.language')}
                  </label>
                  <select
                    value={docLang}
                    onChange={(e: any) => setDocLang(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="fr">Français (FR)</option>
                    <option value="en">English (EN)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {t('projects.name')} *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ex. Refonte Cœur de Réseau & Datacenter"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    {t('projects.client')} *
                  </label>
                  <input
                    type="text"
                    required
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="Ex. Groupe Magpharm"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    {t('projects.lead')} *
                  </label>
                  <input
                    type="text"
                    required
                    value={leadName}
                    onChange={(e) => setLeadName(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {t('projects.initialSite')}
                </label>
                <input
                  type="text"
                  value={initialSite}
                  onChange={(e) => setInitialSite(e.target.value)}
                  placeholder="Ex. Siège Social - Paris"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {t('projects.scope')}
                </label>
                <input
                  type="text"
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  placeholder="Ex. Switches Cisco Catalyst, Firewalls Fortinet, Cluster VMware"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {t('projects.description')}
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  placeholder="Objectif de l'installation, contexte et contraintes..."
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-xs disabled:opacity-50"
                >
                  {isSubmitting ? t('common.loading') : t('common.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Duplication */}
      {showDuplicateModal && targetProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <Copy className="w-4 h-4 text-blue-600" />
                <span>{t('projects.duplicateModalTitle')}</span>
              </h3>
              <button onClick={() => setShowDuplicateModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 bg-blue-50 p-3 rounded-lg border border-blue-200 leading-relaxed">
              {t('projects.duplicateNotice')}
            </p>

            {formError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleDuplicateProject} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {t('projects.newReference')} *
                </label>
                <input
                  type="text"
                  required
                  value={newRef}
                  onChange={(e) => setNewRef(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {t('projects.newProjectName')}
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowDuplicateModal(false)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-xs"
                >
                  {isSubmitting ? t('common.loading') : t('projects.duplicate')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
