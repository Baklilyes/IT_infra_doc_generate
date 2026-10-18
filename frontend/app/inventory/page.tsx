'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import {
  apiFetch,
  Project,
  Equipment,
  EquipmentCategory,
  DuplicateFinding,
  Site
} from '@/lib/api';
import {
  Server,
  Plus,
  Search,
  Filter,
  AlertTriangle,
  LayoutGrid,
  List as ListIcon,
  Shield,
  Wifi,
  HardDrive,
  Cpu,
  Boxes,
  Network,
  Trash2,
  ExternalLink,
  X,
  CheckCircle2,
  Building
} from 'lucide-react';

export default function InventoryPage() {
  const { t, locale } = useTranslation();
  const { user } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [equipments, setEquipments] = useState<Equipment[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicateFinding[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Add Equipment Modal
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [category, setCategory] = useState<EquipmentCategory>('switch');
  const [subcategory, setSubcategory] = useState('');
  const [manufacturer, setManufacturer] = useState('');
  const [model, setModel] = useState('');
  const [serial, setSerial] = useState('');
  const [mgmtIp, setMgmtIp] = useState('');
  const [firmware, setFirmware] = useState('');
  const [role, setRole] = useState('');
  const [siteId, setSiteId] = useState('');
  const [notes, setNotes] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  // Specific attributes state
  const [poeBudget, setPoeBudget] = useState('740');
  const [stacking, setStacking] = useState(false);
  const [haMode, setHaMode] = useState('Active/Passive');
  const [cpuCores, setCpuCores] = useState('32');
  const [ramGb, setRamGb] = useState('128');
  const [storageTb, setStorageTb] = useState('4.0');
  const [osName, setOsName] = useState('Windows Server 2022');
  const [raidType, setRaidType] = useState('RAID 6');

  const canEdit = user?.role === 'administrator' || user?.role === 'engineer';

  // 1. Fetch Projects
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

  // 2. Fetch Equipment & Duplicates when Project or Category changes
  const fetchEquipment = async () => {
    if (!selectedProjectId) return;
    try {
      setLoading(true);
      let query = '';
      if (selectedCategory !== 'all') query += `?category=${selectedCategory}`;
      if (search) query += `${query ? '&' : '?'}search=${encodeURIComponent(search)}`;

      const [eqData, dupData, siteData] = await Promise.all([
        apiFetch<Equipment[]>(`/api/projects/${selectedProjectId}/equipment${query}`),
        apiFetch<DuplicateFinding[]>(`/api/projects/${selectedProjectId}/equipment/duplicates`),
        apiFetch<Site[]>(`/api/projects/${selectedProjectId}/sites`),
      ]);
      setEquipments(eqData);
      setDuplicates(dupData);
      setSites(siteData);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEquipment();
  }, [selectedProjectId, selectedCategory, search]);

  const handleCreateEquipment = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      // Build specific attributes payload based on category
      const specificAttrs: Record<string, any> = {};
      if (category === 'switch') {
        specificAttrs.poe_budget = poeBudget ? Number(poeBudget) : undefined;
        specificAttrs.stacking = stacking;
      } else if (category === 'firewall') {
        specificAttrs.ha_mode = haMode;
      } else if (category === 'physical_server' || category === 'virtual_machine') {
        specificAttrs.cpu_cores = cpuCores ? Number(cpuCores) : undefined;
        specificAttrs.ram_gb = ramGb ? Number(ramGb) : undefined;
        specificAttrs.storage_tb = storageTb ? Number(storageTb) : undefined;
        specificAttrs.os = osName;
      } else if (category === 'storage') {
        specificAttrs.usable_capacity_tb = storageTb ? Number(storageTb) : undefined;
        specificAttrs.raid_type = raidType;
      }

      await apiFetch(`/api/projects/${selectedProjectId}/equipment`, {
        method: 'POST',
        body: JSON.stringify({
          name,
          category,
          subcategory: subcategory || undefined,
          manufacturer: manufacturer || undefined,
          model: model || undefined,
          serial_number: serial || undefined,
          management_ip: mgmtIp || undefined,
          firmware_version: firmware || undefined,
          role: role || undefined,
          site_id: siteId || undefined,
          notes: notes || undefined,
          specific_attributes: specificAttrs,
        }),
      });

      setShowModal(false);
      // Reset form
      setName('');
      setSubcategory('');
      setManufacturer('');
      setModel('');
      setSerial('');
      setMgmtIp('');
      setFirmware('');
      setRole('');
      setNotes('');
      fetchEquipment();
    } catch (err: any) {
      setFormError(err.message || "Erreur lors de l'enregistrement");
    }
  };

  const handleDeleteEquipment = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm("Supprimer cet équipement et l'ensemble de ses interfaces associées ?")) return;
    try {
      await apiFetch(`/api/equipment/${id}`, { method: 'DELETE' });
      fetchEquipment();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de la suppression');
    }
  };

  const categoryIcons: Record<string, any> = {
    switch: Network,
    router: Network,
    firewall: Shield,
    physical_server: Server,
    hypervisor: Cpu,
    virtual_machine: Boxes,
    storage: HardDrive,
    wifi: Wifi,
    generic: Server,
  };

  const getCategoryBadge = (cat: EquipmentCategory) => {
    const labels: Record<EquipmentCategory, string> = {
      switch: 'Switch',
      router: 'Routeur',
      firewall: 'Firewall',
      physical_server: 'Serveur Physique',
      hypervisor: 'Hyperviseur',
      virtual_machine: 'Machine Virtuelle',
      storage: 'Baie Stockage / NAS',
      wifi: 'Wi-Fi / AP',
      generic: 'Générique',
    };
    return (
      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
        {labels[cat] || cat}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header and Project Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.inventory')}</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Répertoire technique du matériel physique et logique documenté
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* Project selector dropdown */}
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
              <span>Ajouter un équipement</span>
            </button>
          )}
        </div>
      </div>

      {/* Duplicate Findings Warning Banner */}
      {duplicates.length > 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold">Doublons potentiels détectés dans l'inventaire ({duplicates.length}) :</h4>
            <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-700">
              {duplicates.map((dup, i) => (
                <li key={i}>
                  Champ <strong>{dup.field}</strong> = <span className="font-mono font-semibold">"{dup.value}"</span> partagé par : {dup.equipment_names.join(', ')}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2 text-xs font-semibold">
        {[
          { id: 'all', label: 'Tous les équipements' },
          { id: 'switch', label: 'Switches' },
          { id: 'router', label: 'Routeurs' },
          { id: 'firewall', label: 'Firewalls' },
          { id: 'physical_server', label: 'Serveurs' },
          { id: 'hypervisor', label: 'Hyperviseurs' },
          { id: 'virtual_machine', label: 'VMs' },
          { id: 'storage', label: 'Stockage' },
          { id: 'wifi', label: 'Wi-Fi' },
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

      {/* Controls Bar: Search & View toggle */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher par nom, modèle, IP, numéro de série..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg outline-hidden focus:ring-1 focus:ring-blue-500 bg-white"
          />
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs text-slate-500 font-medium">
            <strong>{equipments.length}</strong> équipement(s)
          </span>

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
      </div>

      {/* Equipment List or Grid */}
      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs text-slate-500">Chargement de l'inventaire...</p>
        </div>
      ) : equipments.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
          <Server className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <h3 className="text-sm font-semibold text-slate-700">Aucun équipement répertorié</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
            Vous pouvez saisir manuellement des équipements ou les importer via CSV / Excel.
          </p>
          {canEdit && (
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs inline-flex items-center space-x-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Ajouter un premier équipement</span>
            </button>
          )}
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid Cards View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {equipments.map((eq) => {
            const IconComponent = categoryIcons[eq.category] || Server;
            return (
              <Link
                key={eq.id}
                href={`/inventory/${eq.id}`}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:shadow-md hover:border-blue-400 transition flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2 rounded-lg bg-blue-50 text-blue-700 border border-blue-100">
                      <IconComponent className="w-4 h-4" />
                    </div>
                    {getCategoryBadge(eq.category)}
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition font-mono">
                    {eq.name}
                  </h3>

                  <div className="mt-2 space-y-1 text-xs text-slate-600">
                    <p className="flex items-center justify-between">
                      <span className="text-slate-400">Modèle :</span>
                      <span className="font-semibold">{eq.manufacturer} {eq.model || 'N/A'}</span>
                    </p>
                    {eq.management_ip && (
                      <p className="flex items-center justify-between">
                        <span className="text-slate-400">IP Gestion :</span>
                        <span className="font-mono font-semibold text-blue-700">{eq.management_ip}</span>
                      </p>
                    )}
                    {eq.serial_number && (
                      <p className="flex items-center justify-between">
                        <span className="text-slate-400">N° Série :</span>
                        <span className="font-mono text-slate-500">{eq.serial_number}</span>
                      </p>
                    )}
                    {eq.site_name && (
                      <p className="flex items-center justify-between">
                        <span className="text-slate-400">Site :</span>
                        <span className="flex items-center space-x-1 text-slate-700">
                          <Building className="w-3 h-3 text-slate-400" />
                          <span>{eq.site_name}</span>
                        </span>
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <div className="flex items-center space-x-3 text-[11px]">
                    <span><strong>{eq.interfaces_count}</strong> interface(s)</span>
                    <span>•</span>
                    <span><strong>{eq.configurations_count}</strong> config(s)</span>
                  </div>

                  {canEdit && (
                    <button
                      onClick={(e) => handleDeleteEquipment(eq.id, e)}
                      title="Supprimer"
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        /* Table View */
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">Équipement</th>
                  <th className="px-4 py-3">Famille</th>
                  <th className="px-4 py-3">Modèle</th>
                  <th className="px-4 py-3">IP Gestion</th>
                  <th className="px-4 py-3">N° Série</th>
                  <th className="px-4 py-3">Site</th>
                  <th className="px-4 py-3">Interfaces</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {equipments.map((eq) => (
                  <tr key={eq.id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3 font-mono font-bold text-blue-700">
                      <Link href={`/inventory/${eq.id}`} className="hover:underline">
                        {eq.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{getCategoryBadge(eq.category)}</td>
                    <td className="px-4 py-3 font-medium">{eq.manufacturer} {eq.model}</td>
                    <td className="px-4 py-3 font-mono text-blue-700">{eq.management_ip || '-'}</td>
                    <td className="px-4 py-3 font-mono text-slate-500">{eq.serial_number || '-'}</td>
                    <td className="px-4 py-3">{eq.site_name || '-'}</td>
                    <td className="px-4 py-3 font-bold">{eq.interfaces_count}</td>
                    <td className="px-4 py-3 text-right">
                      {canEdit && (
                        <button
                          onClick={(e) => handleDeleteEquipment(eq.id, e)}
                          title="Supprimer"
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

      {/* Modal Ajout Équipement */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <Server className="w-4 h-4 text-blue-600" />
                <span>Ajouter un équipement d'infrastructure</span>
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateEquipment} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Hostname / Nom *</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="SW-CORE-01"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Famille d'infrastructure *</label>
                  <select
                    value={category}
                    onChange={(e: any) => setCategory(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500 font-semibold"
                  >
                    <option value="switch">Switch</option>
                    <option value="router">Routeur</option>
                    <option value="firewall">Firewall / Sécurité</option>
                    <option value="physical_server">Serveur Physique</option>
                    <option value="hypervisor">Hyperviseur</option>
                    <option value="virtual_machine">Machine Virtuelle</option>
                    <option value="storage">Baie Stockage (SAN/NAS)</option>
                    <option value="wifi">Borne Wi-Fi (AP)</option>
                    <option value="generic">Générique</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Constructeur</label>
                  <input
                    type="text"
                    value={manufacturer}
                    onChange={(e) => setManufacturer(e.target.value)}
                    placeholder="Ex. Cisco, Dell, Fortinet, HPE"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Modèle</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="Ex. Catalyst 9300-48P"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">IP de gestion</label>
                  <input
                    type="text"
                    value={mgmtIp}
                    onChange={(e) => setMgmtIp(e.target.value)}
                    placeholder="192.168.1.1"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Numéro de série</label>
                  <input
                    type="text"
                    value={serial}
                    onChange={(e) => setSerial(e.target.value)}
                    placeholder="FCW2219B001"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Site d'implantation</label>
                  <select
                    value={siteId}
                    onChange={(e) => setSiteId(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="">Aucun site assigné</option>
                    {sites.map((s) => (
                      <option key={s.id} value={s.id}>{s.name} ({s.code || s.city || 'Site'})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Version logicielle / Firmware</label>
                  <input
                    type="text"
                    value={firmware}
                    onChange={(e) => setFirmware(e.target.value)}
                    placeholder="Ex. IOS-XE 17.9.4a"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Dynamic Specific Attributes per Category */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
                <span className="font-bold text-slate-800 block text-[11px] uppercase tracking-wider">
                  Attributs Spécifiques ({category})
                </span>

                {category === 'switch' && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Budget PoE (Watts)</label>
                      <input
                        type="number"
                        value={poeBudget}
                        onChange={(e) => setPoeBudget(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-3 py-1.5 bg-white"
                      />
                    </div>
                    <div className="flex items-center space-x-2 mt-5">
                      <input
                        type="checkbox"
                        id="stack"
                        checked={stacking}
                        onChange={(e) => setStacking(e.target.checked)}
                        className="rounded text-blue-600 focus:ring-blue-500"
                      />
                      <label htmlFor="stack" className="font-semibold text-slate-700">
                        Membre d'un Stack (StackWise / VSS)
                      </label>
                    </div>
                  </div>
                )}

                {category === 'firewall' && (
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Mode Haute Disponibilité (HA)</label>
                    <select
                      value={haMode}
                      onChange={(e) => setHaMode(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-1.5 bg-white"
                    >
                      <option value="Standalone">Standalone (Autonome)</option>
                      <option value="Active/Passive">Actif / Passif</option>
                      <option value="Active/Active">Actif / Actif</option>
                    </select>
                  </div>
                )}

                {(category === 'physical_server' || category === 'virtual_machine') && (
                  <div className="grid grid-cols-4 gap-2">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">CPU Cores</label>
                      <input
                        type="number"
                        value={cpuCores}
                        onChange={(e) => setCpuCores(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-2 py-1.5 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">RAM (Go)</label>
                      <input
                        type="number"
                        value={ramGb}
                        onChange={(e) => setRamGb(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-2 py-1.5 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Stockage (To)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={storageTb}
                        onChange={(e) => setStorageTb(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-2 py-1.5 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Système OS</label>
                      <input
                        type="text"
                        value={osName}
                        onChange={(e) => setOsName(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-2 py-1.5 bg-white"
                      />
                    </div>
                  </div>
                )}

                {category === 'storage' && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Capacité Utile (To)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={storageTb}
                        onChange={(e) => setStorageTb(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-3 py-1.5 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Configuration RAID</label>
                      <select
                        value={raidType}
                        onChange={(e) => setRaidType(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-3 py-1.5 bg-white"
                      >
                        <option value="RAID 5">RAID 5</option>
                        <option value="RAID 6">RAID 6</option>
                        <option value="RAID 10">RAID 10</option>
                        <option value="RAID 0">RAID 0</option>
                      </select>
                    </div>
                  </div>
                )}
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
