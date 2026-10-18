'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import { apiFetch, ProjectDetail, Site, Location, ProjectStatus } from '@/lib/api';
import {
  ArrowLeft,
  Building,
  MapPin,
  Server,
  Plus,
  Trash2,
  Edit,
  Save,
  CheckCircle2,
  Calendar,
  Layers,
  FileText,
  User,
  X,
  AlertCircle,
  Copy,
  Archive
} from 'lucide-react';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.id as string;
  const { t } = useTranslation();
  const { user } = useAuth();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'sites' | 'details'>('sites');

  // Add Site Modal
  const [showAddSiteModal, setShowAddSiteModal] = useState(false);
  const [siteName, setSiteName] = useState('');
  const [siteCode, setSiteCode] = useState('');
  const [siteAddress, setSiteAddress] = useState('');
  const [siteCity, setSiteCity] = useState('');
  const [siteCountry, setSiteCountry] = useState('France');

  // Add Location Modal
  const [showAddLocModal, setShowAddLocModal] = useState(false);
  const [targetSiteId, setTargetSiteId] = useState<string | null>(null);
  const [locName, setLocName] = useState('');
  const [locRoom, setLocRoom] = useState('');
  const [locRack, setLocRack] = useState('');
  const [locNotes, setLocNotes] = useState('');

  // Edit metadata inline
  const [isEditingScope, setIsEditingScope] = useState(false);
  const [editScope, setEditScope] = useState('');
  const [editDescription, setEditDescription] = useState('');

  const canEdit = user?.role === 'administrator' || user?.role === 'engineer';

  const fetchProject = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch<ProjectDetail>(`/api/projects/${projectId}`);
      setProject(data);
      setEditScope(data.scope || '');
      setEditDescription(data.description || '');
    } catch (err: any) {
      setError(err.message || 'Projet introuvable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) {
      fetchProject();
    }
  }, [projectId]);

  const handleStatusChange = async (newStatus: ProjectStatus) => {
    if (!canEdit || !project) return;
    try {
      const updated = await apiFetch<ProjectDetail>(`/api/projects/${project.id}`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus }),
      });
      setProject(updated);
    } catch (err: any) {
      alert(err.message || 'Erreur lors du changement de statut');
    }
  };

  const handleSaveDetails = async () => {
    if (!canEdit || !project) return;
    try {
      const updated = await apiFetch<ProjectDetail>(`/api/projects/${project.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          scope: editScope,
          description: editDescription,
        }),
      });
      setProject(updated);
      setIsEditingScope(false);
    } catch (err: any) {
      alert(err.message || 'Erreur lors de la mise à jour');
    }
  };

  const handleAddSite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!project) return;
    try {
      await apiFetch(`/api/projects/${project.id}/sites`, {
        method: 'POST',
        body: JSON.stringify({
          name: siteName,
          code: siteCode || undefined,
          address: siteAddress || undefined,
          city: siteCity || undefined,
          country: siteCountry || undefined,
        }),
      });
      setShowAddSiteModal(false);
      setSiteName('');
      setSiteCode('');
      setSiteAddress('');
      setSiteCity('');
      fetchProject();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de l’ajout du site');
    }
  };

  const handleDeleteSite = async (siteId: string) => {
    if (!window.confirm('Supprimer ce site et tous ses emplacements associés ?')) return;
    try {
      await apiFetch(`/api/sites/${siteId}`, { method: 'DELETE' });
      fetchProject();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de la suppression du site');
    }
  };

  const handleAddLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetSiteId) return;
    try {
      await apiFetch(`/api/sites/${targetSiteId}/locations`, {
        method: 'POST',
        body: JSON.stringify({
          name: locName,
          room: locRoom || undefined,
          rack: locRack || undefined,
          notes: locNotes || undefined,
        }),
      });
      setShowAddLocModal(false);
      setLocName('');
      setLocRoom('');
      setLocRack('');
      setLocNotes('');
      fetchProject();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de l’ajout de l’emplacement');
    }
  };

  const handleDeleteLocation = async (locId: string) => {
    if (!window.confirm('Supprimer cet emplacement ?')) return;
    try {
      await apiFetch(`/api/locations/${locId}`, { method: 'DELETE' });
      fetchProject();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de la suppression');
    }
  };

  const openAddLocationModal = (siteId: string) => {
    setTargetSiteId(siteId);
    setShowAddLocModal(true);
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-xs text-slate-500">{t('common.loading')}</p>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs">
        <AlertCircle className="w-5 h-5 mb-2" />
        <p className="font-semibold">{error || 'Projet introuvable'}</p>
        <Link href="/projects" className="mt-3 inline-block font-semibold text-blue-700 underline">
          Retour à la liste des projets
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="flex items-center space-x-3">
          <Link
            href="/projects"
            className="p-2 border border-slate-200 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                {project.reference}
              </span>
              <span className="text-slate-400">•</span>
              <span className="text-xs text-slate-600 font-semibold">{project.client_name}</span>
            </div>
            <h1 className="text-lg font-bold text-slate-900 mt-0.5">{project.name}</h1>
          </div>
        </div>

        {/* Status Dropdown */}
        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <label className="text-xs text-slate-500 font-medium">Statut :</label>
          <select
            value={project.status}
            disabled={!canEdit}
            onChange={(e) => handleStatusChange(e.target.value as ProjectStatus)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:ring-1 focus:ring-blue-500 outline-hidden"
          >
            <option value="draft">{t('projectStatus.draft')}</option>
            <option value="in_preparation">{t('projectStatus.in_preparation')}</option>
            <option value="in_review">{t('projectStatus.in_review')}</option>
            <option value="validated">{t('projectStatus.validated')}</option>
            <option value="closed">{t('projectStatus.closed')}</option>
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('sites')}
          className={`pb-3 transition flex items-center space-x-2 ${
            activeTab === 'sites'
              ? 'border-b-2 border-blue-600 text-blue-700'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <MapPin className="w-4 h-4" />
          <span>Sites & Emplacements ({project.sites.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('details')}
          className={`pb-3 transition flex items-center space-x-2 ${
            activeTab === 'details'
              ? 'border-b-2 border-blue-600 text-blue-700'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Périmètre technique & Description</span>
        </button>
      </div>

      {/* TAB 1: SITES & LOCATIONS */}
      {activeTab === 'sites' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Sites d'installation</h2>
              <p className="text-xs text-slate-500">Implantations physiques hébergeant les équipements de ce projet</p>
            </div>
            {canEdit && (
              <button
                onClick={() => setShowAddSiteModal(true)}
                className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 transition"
              >
                <Plus className="w-4 h-4" />
                <span>Ajouter un site</span>
              </button>
            )}
          </div>

          {project.sites.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-xs">
              <MapPin className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-700">Aucun site défini pour ce projet</p>
              <p className="text-[11px] text-slate-400 mt-1 mb-3">
                Un site permet de rattacher des équipements à un bâtiment, une salle serveur ou une baie.
              </p>
              {canEdit && (
                <button
                  onClick={() => setShowAddSiteModal(true)}
                  className="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded-lg inline-flex items-center space-x-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Ajouter le premier site</span>
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5">
              {project.sites.map((site) => (
                <div
                  key={site.id}
                  className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4"
                >
                  <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-sm text-slate-900">{site.name}</span>
                        {site.code && (
                          <span className="font-mono text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                            {site.code}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5 flex items-center space-x-1">
                        <Building className="w-3.5 h-3.5 text-slate-400" />
                        <span>
                          {[site.address, site.city, site.country].filter(Boolean).join(', ') || 'Adresse non renseignée'}
                        </span>
                      </p>
                    </div>

                    <div className="flex items-center space-x-2">
                      {canEdit && (
                        <>
                          <button
                            onClick={() => openAddLocationModal(site.id)}
                            className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded flex items-center space-x-1"
                          >
                            <Plus className="w-3.5 h-3.5" />
                            <span>Salle / Baie</span>
                          </button>
                          <button
                            onClick={() => handleDeleteSite(site.id)}
                            title="Supprimer le site"
                            className="p-1.5 text-slate-400 hover:text-red-600 rounded"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Locations List */}
                  <div>
                    <h3 className="text-xs font-semibold text-slate-600 mb-2">
                      Salles techniques & Baies ({site.locations?.length || 0}) :
                    </h3>
                    {site.locations && site.locations.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {site.locations.map((loc) => (
                          <div
                            key={loc.id}
                            className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start justify-between text-xs"
                          >
                            <div>
                              <div className="font-semibold text-slate-800">{loc.name}</div>
                              <div className="text-[11px] text-slate-500 mt-0.5 space-x-2">
                                {loc.room && <span>Salle : <strong>{loc.room}</strong></span>}
                                {loc.rack && <span>Baie : <strong>{loc.rack}</strong></span>}
                              </div>
                            </div>
                            {canEdit && (
                              <button
                                onClick={() => handleDeleteLocation(loc.id)}
                                className="text-slate-400 hover:text-red-600 p-1"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 italic">
                        Aucun emplacement détaillé pour ce site.
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: TECHNICAL SCOPE & METADATA */}
      {activeTab === 'details' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Spécifications & Périmètre du Projet</h2>
              <p className="text-xs text-slate-500">Détails documentaires utilisés pour la constitution du HLD et LLD</p>
            </div>
            {canEdit && (
              <div>
                {isEditingScope ? (
                  <button
                    onClick={handleSaveDetails}
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg flex items-center space-x-1.5 shadow-xs"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{t('common.save')}</span>
                  </button>
                ) : (
                  <button
                    onClick={() => setIsEditingScope(true)}
                    className="px-3.5 py-1.5 border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg flex items-center space-x-1.5"
                  >
                    <Edit className="w-3.5 h-3.5" />
                    <span>{t('common.edit')}</span>
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1.5">
                Périmètre technique (Scope) :
              </label>
              {isEditingScope ? (
                <textarea
                  rows={4}
                  value={editScope}
                  onChange={(e) => setEditScope(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-3 outline-hidden focus:ring-1 focus:ring-blue-500"
                  placeholder="Familles d'équipements, constructeurs, technologies..."
                />
              ) : (
                <p className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {project.scope || 'Aucun périmètre spécifié.'}
                </p>
              )}
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1.5">
                Description générale & Objectifs :
              </label>
              {isEditingScope ? (
                <textarea
                  rows={4}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-3 outline-hidden focus:ring-1 focus:ring-blue-500"
                  placeholder="Contexte client, contraintes de production..."
                />
              ) : (
                <p className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {project.description || 'Aucune description générale spécifiée.'}
                </p>
              )}
            </div>
          </div>

          {/* Metadata Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-slate-500 block mb-0.5">Responsable technique</span>
              <span className="font-semibold text-slate-900">{project.lead_name}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-slate-500 block mb-0.5">Langue documentaire</span>
              <span className="font-semibold text-slate-900 uppercase font-mono">{project.document_language}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="text-slate-500 block mb-0.5">Créé le</span>
              <span className="font-semibold text-slate-900">
                {new Date(project.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* MODAL AJOUT SITE */}
      {showAddSiteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Ajouter un site d'infrastructure</h3>
              <button onClick={() => setShowAddSiteModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddSite} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Nom du site *</label>
                <input
                  type="text"
                  required
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  placeholder="Ex. Datacenter DC2"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Code site</label>
                  <input
                    type="text"
                    value={siteCode}
                    onChange={(e) => setSiteCode(e.target.value)}
                    placeholder="DC2-PAR"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Ville</label>
                  <input
                    type="text"
                    value={siteCity}
                    onChange={(e) => setSiteCity(e.target.value)}
                    placeholder="Paris"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Adresse</label>
                <input
                  type="text"
                  value={siteAddress}
                  onChange={(e) => setSiteAddress(e.target.value)}
                  placeholder="12 Avenue des Télécoms"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddSiteModal(false)}
                  className="px-3.5 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-xs"
                >
                  {t('common.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL AJOUT EMPLACEMENT */}
      {showAddLocModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Ajouter un emplacement (Salle / Baie)</h3>
              <button onClick={() => setShowAddLocModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddLocation} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Désignation *</label>
                <input
                  type="text"
                  required
                  value={locName}
                  onChange={(e) => setLocName(e.target.value)}
                  placeholder="Ex. Baie Réseau Principal"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Salle technique</label>
                  <input
                    type="text"
                    value={locRoom}
                    onChange={(e) => setLocRoom(e.target.value)}
                    placeholder="Salle 101"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Baie / Rack</label>
                  <input
                    type="text"
                    value={locRack}
                    onChange={(e) => setLocRack(e.target.value)}
                    placeholder="Rack 42U #1"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Notes</label>
                <input
                  type="text"
                  value={locNotes}
                  onChange={(e) => setLocNotes(e.target.value)}
                  placeholder="Climatisation, alimentation secourue..."
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddLocModal(false)}
                  className="px-3.5 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-xs"
                >
                  {t('common.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
