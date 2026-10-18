'use client';

import React, { useState, useEffect } from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import { apiFetch, Project, ConfigurationParam, Equipment } from '@/lib/api';
import {
  Sliders,
  Plus,
  Search,
  Eye,
  EyeOff,
  Trash2,
  Lock,
  Server,
  X,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function ConfigurationsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [configurations, setConfigurations] = useState<ConfigurationParam[]>([]);
  const [equipments, setEquipments] = useState<Equipment[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [unmaskSecrets, setUnmaskSecrets] = useState(false);

  // Modal Add Config
  const [showModal, setShowModal] = useState(false);
  const [confCategory, setConfCategory] = useState('network');
  const [confKey, setConfKey] = useState('');
  const [confValue, setConfValue] = useState('');
  const [confDesc, setConfDesc] = useState('');
  const [confIsSecret, setConfIsSecret] = useState(false);
  const [confEquipmentId, setConfEquipmentId] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const canEdit = user?.role === 'administrator' || user?.role === 'engineer';

  useEffect(() => {
    apiFetch<Project[]>('/api/projects')
      .then((data) => {
        setProjects(data);
        if (data.length > 0 && !selectedProjectId) {
          setSelectedProjectId(data[0].id);
        }
      })
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, []);

  const fetchConfigs = async () => {
    if (!selectedProjectId) return;
    try {
      setLoading(true);
      let query = '';
      if (selectedCategory !== 'all') query += `?category=${selectedCategory}`;
      if (unmaskSecrets) query += `${query ? '&' : '?'}unmask=true`;

      const [confData, eqData] = await Promise.all([
        apiFetch<ConfigurationParam[]>(`/api/projects/${selectedProjectId}/configurations${query}`),
        apiFetch<Equipment[]>(`/api/projects/${selectedProjectId}/equipment`),
      ]);
      setConfigurations(confData);
      setEquipments(eqData);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, [selectedProjectId, selectedCategory, unmaskSecrets]);

  const handleCreateConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      await apiFetch(`/api/projects/${selectedProjectId}/configurations`, {
        method: 'POST',
        body: JSON.stringify({
          equipment_id: confEquipmentId || undefined,
          category: confCategory,
          key: confKey,
          value: confValue,
          description: confDesc || undefined,
          is_secret: confIsSecret,
        }),
      });
      setShowModal(false);
      setConfKey('');
      setConfValue('');
      setConfDesc('');
      setConfIsSecret(false);
      setConfEquipmentId('');
      fetchConfigs();
    } catch (err: any) {
      setFormError(err.message || "Erreur lors de l'enregistrement");
    }
  };

  const handleDeleteConfig = async (id: string) => {
    if (!window.confirm('Supprimer ce paramètre de configuration ?')) return;
    try {
      await apiFetch(`/api/configurations/${id}`, { method: 'DELETE' });
      fetchConfigs();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de la suppression');
    }
  };

  const filteredConfigs = configurations.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.key.toLowerCase().includes(q) ||
      (c.description && c.description.toLowerCase().includes(q)) ||
      (c.equipment_name && c.equipment_name.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.configurations')}</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Paramètres structurés d'infrastructure avec masquage automatique des secrets
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <label className="text-xs font-semibold text-slate-600">Projet :</label>
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 font-semibold bg-white outline-hidden focus:ring-1 focus:ring-blue-500 min-w-[200px]"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.reference} - {p.name}
                </option>
              ))}
            </select>
          </div>

          {canEdit && (
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Nouveau paramètre</span>
            </button>
          )}
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2 text-xs font-semibold">
        {[
          { id: 'all', label: 'Toutes les catégories' },
          { id: 'network', label: 'Réseau & Switching' },
          { id: 'routing', label: 'Routage' },
          { id: 'security', label: 'Sécurité' },
          { id: 'storage', label: 'Stockage' },
          { id: 'virtualization', label: 'Virtualisation' },
          { id: 'backup', label: 'Sauvegarde' },
          { id: 'services', label: 'Services (DNS/NTP)' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSelectedCategory(tab.id)}
            className={`px-3 py-1.5 rounded-lg transition ${
              selectedCategory === tab.id
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Controls Bar: Search & Secret Mask Toggle */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher par clé, équipement ou description..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-hidden focus:ring-1 focus:ring-blue-500 bg-white"
          />
        </div>

        <div className="flex items-center space-x-3">
          {user?.role === 'administrator' && (
            <button
              onClick={() => setUnmaskSecrets(!unmaskSecrets)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-medium flex items-center space-x-1.5 transition ${
                unmaskSecrets
                  ? 'bg-amber-50 text-amber-800 border-amber-300 font-bold'
                  : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {unmaskSecrets ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              <span>{unmaskSecrets ? 'Masquer secrets' : 'Afficher secrets (Admin)'}</span>
            </button>
          )}

          <span className="text-xs text-slate-500 font-medium">
            <strong>{filteredConfigs.length}</strong> paramètre(s)
          </span>
        </div>
      </div>

      {/* Configurations Table */}
      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs text-slate-500">Chargement des paramètres...</p>
        </div>
      ) : filteredConfigs.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
          <Sliders className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <h3 className="text-sm font-semibold text-slate-700">Aucun paramètre technique</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
            Renseignez les paramètres réseau, sécurité ou systèmes pour documenter le dossier.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">Catégorie</th>
                  <th className="px-4 py-3">Équipement</th>
                  <th className="px-4 py-3">Clé du paramètre</th>
                  <th className="px-4 py-3">Valeur configurée</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredConfigs.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-800 border border-slate-200 uppercase">
                        {c.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-800">
                      {c.equipment_name ? (
                        <span className="font-mono text-blue-700">{c.equipment_name}</span>
                      ) : (
                        <span className="text-slate-400 italic">Global Projet</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-slate-900">{c.key}</td>
                    <td className="px-4 py-3 font-mono">
                      {c.is_secret && !unmaskSecrets ? (
                        <span className="text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200 text-[10px] inline-flex items-center space-x-1">
                          <Lock className="w-3 h-3" />
                          <span>&lt;SECRET_MASQUÉ&gt;</span>
                        </span>
                      ) : (
                        <span className="text-slate-800">{c.value}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-500">{c.description || '-'}</td>
                    <td className="px-4 py-3 text-right">
                      {canEdit && (
                        <button
                          onClick={() => handleDeleteConfig(c.id)}
                          className="p-1 text-slate-400 hover:text-red-600 rounded"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal Ajout Config */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Ajouter un paramètre technique</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateConfig} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Catégorie *</label>
                <select
                  value={confCategory}
                  onChange={(e) => setConfCategory(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500 font-semibold"
                >
                  <option value="network">Réseau & Switching</option>
                  <option value="routing">Routage (BGP/OSPF/Statique)</option>
                  <option value="security">Sécurité & Firewall</option>
                  <option value="storage">Stockage & Multipathing</option>
                  <option value="virtualization">Virtualisation</option>
                  <option value="backup">Sauvegarde</option>
                  <option value="services">Services (DNS/NTP/Syslog)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Équipement associé (optionnel)</label>
                <select
                  value={confEquipmentId}
                  onChange={(e) => setConfEquipmentId(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">Paramètre global au projet</option>
                  {equipments.map((eq) => (
                    <option key={eq.id} value={eq.id}>{eq.name} ({eq.category})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Clé du paramètre *</label>
                <input
                  type="text"
                  required
                  value={confKey}
                  onChange={(e) => setConfKey(e.target.value)}
                  placeholder="ex. default_gateway, ntp_servers, bgp_as"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Valeur *</label>
                <textarea
                  rows={2}
                  required
                  value={confValue}
                  onChange={(e) => setConfValue(e.target.value)}
                  placeholder="Valeur du paramètre..."
                  className="w-full border border-slate-300 rounded-lg p-3 font-mono outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="secret_modal_check"
                  checked={confIsSecret}
                  onChange={(e) => setConfIsSecret(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="secret_modal_check" className="font-semibold text-slate-700">
                  Valeur sensible / secrète (masquer par défaut avec &lt;SECRET_MASQUÉ&gt;)
                </label>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Description</label>
                <input
                  type="text"
                  value={confDesc}
                  onChange={(e) => setConfDesc(e.target.value)}
                  placeholder="Justification ou référence..."
                  className="w-full border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold shadow-xs"
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
