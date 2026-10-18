'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import {
  apiFetch,
  Equipment,
  Interface,
  ConfigurationParam,
} from '@/lib/api';
import {
  ArrowLeft,
  Server,
  Network,
  Sliders,
  Plus,
  Trash2,
  Building,
  Shield,
  Eye,
  EyeOff,
  X,
  AlertCircle,
  ExternalLink,
  CheckCircle2
} from 'lucide-react';

export default function EquipmentDetailPage() {
  const params = useParams();
  const equipmentId = params?.id as string;
  const { t } = useTranslation();
  const { user } = useAuth();

  const [equipment, setEquipment] = useState<Equipment | null>(null);
  const [interfaces, setInterfaces] = useState<Interface[]>([]);
  const [configurations, setConfigurations] = useState<ConfigurationParam[]>([]);
  const [allEquipments, setAllEquipments] = useState<Equipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'interfaces' | 'configs'>('interfaces');

  // Modal Add Interface
  const [showAddIntfModal, setShowAddIntfModal] = useState(false);
  const [intfName, setIntfName] = useState('');
  const [intfType, setIntfType] = useState<'physical' | 'vlan_interface' | 'port_channel' | 'loopback'>('physical');
  const [intfMode, setIntfMode] = useState<'access' | 'trunk' | 'routed'>('access');
  const [intfIp, setIntfIp] = useState('');
  const [intfMask, setIntfMask] = useState('');
  const [intfVlan, setIntfVlan] = useState('');
  const [intfAllowedVlans, setIntfAllowedVlans] = useState('');
  const [intfSpeed, setIntfSpeed] = useState('1000/Full');
  const [intfDesc, setIntfDesc] = useState('');
  const [connectedEqId, setConnectedEqId] = useState('');
  const [connectedIntfName, setConnectedIntfName] = useState('');
  const [linkType, setLinkType] = useState('Cuivre Cat6A');

  // Modal Add Config
  const [showAddConfigModal, setShowAddConfigModal] = useState(false);
  const [confCategory, setConfCategory] = useState('network');
  const [confKey, setConfKey] = useState('');
  const [confValue, setConfValue] = useState('');
  const [confDesc, setConfDesc] = useState('');
  const [confIsSecret, setConfIsSecret] = useState(false);

  // Unmask toggle (Admin only)
  const [unmaskSecrets, setUnmaskSecrets] = useState(false);

  const canEdit = user?.role === 'administrator' || user?.role === 'engineer';

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const eq = await apiFetch<Equipment>(`/api/equipment/${equipmentId}`);
      setEquipment(eq);

      const [intfData, confData, allEqData] = await Promise.all([
        apiFetch<Interface[]>(`/api/equipment/${equipmentId}/interfaces`),
        apiFetch<ConfigurationParam[]>(
          `/api/projects/${eq.project_id}/configurations?equipment_id=${equipmentId}${
            unmaskSecrets ? '&unmask=true' : ''
          }`
        ),
        apiFetch<Equipment[]>(`/api/projects/${eq.project_id}/equipment`),
      ]);
      setInterfaces(intfData);
      setConfigurations(confData);
      setAllEquipments(allEqData.filter((e) => e.id !== equipmentId));
    } catch (err: any) {
      setError(err.message || 'Équipement introuvable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (equipmentId) {
      fetchData();
    }
  }, [equipmentId, unmaskSecrets]);

  const handleCreateInterface = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiFetch(`/api/equipment/${equipmentId}/interfaces`, {
        method: 'POST',
        body: JSON.stringify({
          name: intfName,
          interface_type: intfType,
          mode: intfMode,
          ip_address: intfIp || undefined,
          subnet_mask: intfMask || undefined,
          access_vlan: intfVlan ? Number(intfVlan) : undefined,
          allowed_vlans: intfAllowedVlans || undefined,
          speed_duplex: intfSpeed || undefined,
          description: intfDesc || undefined,
          connected_equipment_id: connectedEqId || undefined,
          connected_interface_name: connectedIntfName || undefined,
          link_type: linkType || undefined,
        }),
      });
      setShowAddIntfModal(false);
      // Reset
      setIntfName('');
      setIntfIp('');
      setIntfMask('');
      setIntfVlan('');
      setIntfAllowedVlans('');
      setIntfDesc('');
      setConnectedEqId('');
      setConnectedIntfName('');
      fetchData();
    } catch (err: any) {
      alert(err.message || "Erreur lors de l'ajout de l'interface");
    }
  };

  const handleDeleteInterface = async (intfId: string) => {
    if (!window.confirm('Supprimer cette interface ?')) return;
    try {
      await apiFetch(`/api/interfaces/${intfId}`, { method: 'DELETE' });
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de la suppression');
    }
  };

  const handleCreateConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!equipment) return;
    try {
      await apiFetch(`/api/projects/${equipment.project_id}/configurations`, {
        method: 'POST',
        body: JSON.stringify({
          equipment_id: equipmentId,
          category: confCategory,
          key: confKey,
          value: confValue,
          description: confDesc || undefined,
          is_secret: confIsSecret,
        }),
      });
      setShowAddConfigModal(false);
      setConfKey('');
      setConfValue('');
      setConfDesc('');
      setConfIsSecret(false);
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de l’ajout du paramètre');
    }
  };

  const handleDeleteConfig = async (confId: string) => {
    if (!window.confirm('Supprimer ce paramètre de configuration ?')) return;
    try {
      await apiFetch(`/api/configurations/${confId}`, { method: 'DELETE' });
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de la suppression');
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-xs text-slate-500">{t('common.loading')}</p>
      </div>
    );
  }

  if (error || !equipment) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs">
        <AlertCircle className="w-5 h-5 mb-2" />
        <p className="font-semibold">{error || 'Équipement introuvable'}</p>
        <Link href="/inventory" className="mt-3 inline-block font-semibold text-blue-700 underline">
          Retour à l'inventaire
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="flex items-center space-x-3">
          <Link
            href="/inventory"
            className="p-2 border border-slate-200 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-sm font-bold text-slate-900">{equipment.name}</span>
              <span className="text-slate-400">•</span>
              <span className="text-xs font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100 uppercase">
                {equipment.category}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {equipment.manufacturer} {equipment.model} {equipment.serial_number && `• S/N: ${equipment.serial_number}`}
            </p>
          </div>
        </div>

        {/* IP and Site Badge */}
        <div className="flex items-center space-x-3 text-xs">
          {equipment.management_ip && (
            <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 font-mono font-bold">
              IP: {equipment.management_ip}
            </div>
          )}
          {equipment.site_name && (
            <div className="flex items-center space-x-1 p-2 bg-slate-100 border border-slate-200 rounded-lg text-slate-700">
              <Building className="w-3.5 h-3.5 text-slate-500" />
              <span>{equipment.site_name}</span>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('interfaces')}
          className={`pb-3 transition flex items-center space-x-2 ${
            activeTab === 'interfaces'
              ? 'border-b-2 border-blue-600 text-blue-700'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <Network className="w-4 h-4" />
          <span>Interfaces & Liens Réseau ({interfaces.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('configs')}
          className={`pb-3 transition flex items-center space-x-2 ${
            activeTab === 'configs'
              ? 'border-b-2 border-blue-600 text-blue-700'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Paramètres de Configuration ({configurations.length})</span>
        </button>
      </div>

      {/* TAB 1: INTERFACES */}
      {activeTab === 'interfaces' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Ports Physiques & Logiques
            </h3>
            {canEdit && (
              <button
                onClick={() => setShowAddIntfModal(true)}
                className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 transition"
              >
                <Plus className="w-4 h-4" />
                <span>Ajouter une interface</span>
              </button>
            )}
          </div>

          {interfaces.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-xs">
              <Network className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-700">Aucune interface documentée</p>
              <p className="text-[11px] text-slate-400 mt-1 mb-3">
                Renseignez les interfaces physiques ou logiques pour constituer la topologie.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="px-4 py-3">Interface</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Mode</th>
                      <th className="px-4 py-3">Adresse IP</th>
                      <th className="px-4 py-3">VLAN</th>
                      <th className="px-4 py-3">Connexion Distante</th>
                      <th className="px-4 py-3">Type de lien</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {interfaces.map((intf) => (
                      <tr key={intf.id} className="hover:bg-slate-50 transition">
                        <td className="px-4 py-3 font-mono font-bold text-blue-700">
                          {intf.name}
                        </td>
                        <td className="px-4 py-3 capitalize text-slate-500">{intf.interface_type}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-800 border border-slate-200 uppercase">
                            {intf.mode}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-blue-700">
                          {intf.ip_address ? `${intf.ip_address} ${intf.subnet_mask || ''}` : '-'}
                        </td>
                        <td className="px-4 py-3 font-semibold">
                          {intf.access_vlan ? `VLAN ${intf.access_vlan}` : intf.allowed_vlans ? `Trunk (${intf.allowed_vlans})` : '-'}
                        </td>
                        <td className="px-4 py-3">
                          {intf.connected_equipment_name ? (
                            <span className="font-semibold text-slate-800">
                              {intf.connected_equipment_name} [{intf.connected_interface_name || 'Port'}]
                            </span>
                          ) : (
                            <span className="text-slate-400 italic">Non connecté</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-500">{intf.link_type || '-'}</td>
                        <td className="px-4 py-3 text-right">
                          {canEdit && (
                            <button
                              onClick={() => handleDeleteInterface(intf.id)}
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
        </div>
      )}

      {/* TAB 2: CONFIGS */}
      {activeTab === 'configs' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Paramètres Techniques Spécifiques
            </h3>

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
                  <span>{unmaskSecrets ? 'Masquer les secrets' : 'Afficher les secrets'}</span>
                </button>
              )}

              {canEdit && (
                <button
                  onClick={() => setShowAddConfigModal(true)}
                  className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 transition"
                >
                  <Plus className="w-4 h-4" />
                  <span>Ajouter un paramètre</span>
                </button>
              )}
            </div>
          </div>

          {configurations.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-xs">
              <Sliders className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-700">Aucun paramètre technique configuré</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="px-4 py-3">Catégorie</th>
                      <th className="px-4 py-3">Clé / Paramètre</th>
                      <th className="px-4 py-3">Valeur</th>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {configurations.map((conf) => (
                      <tr key={conf.id} className="hover:bg-slate-50 transition">
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-800 border border-slate-200 uppercase">
                            {conf.category}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono font-bold text-slate-900">{conf.key}</td>
                        <td className="px-4 py-3 font-mono">
                          {conf.is_secret && !unmaskSecrets ? (
                            <span className="text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200 text-[10px]">
                              &lt;SECRET_MASQUÉ&gt;
                            </span>
                          ) : (
                            <span className="text-slate-800">{conf.value}</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-500">{conf.description || '-'}</td>
                        <td className="px-4 py-3 text-right">
                          {canEdit && (
                            <button
                              onClick={() => handleDeleteConfig(conf.id)}
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
        </div>
      )}

      {/* Modal Ajout Interface */}
      {showAddIntfModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Ajouter une interface</h3>
              <button onClick={() => setShowAddIntfModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateInterface} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Nom d'interface *</label>
                  <input
                    type="text"
                    required
                    value={intfName}
                    onChange={(e) => setIntfName(e.target.value)}
                    placeholder="GigabitEthernet1/0/1"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono outline-hidden focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Type d'interface</label>
                  <select
                    value={intfType}
                    onChange={(e: any) => setIntfType(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="physical">Physique (Ethernet / SFP)</option>
                    <option value="vlan_interface">VLAN Interface (SVI)</option>
                    <option value="port_channel">Port-Channel / Agrégation</option>
                    <option value="loopback">Loopback</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Mode de port</label>
                  <select
                    value={intfMode}
                    onChange={(e: any) => setIntfMode(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500 font-semibold"
                  >
                    <option value="access">Access</option>
                    <option value="trunk">Trunk</option>
                    <option value="routed">Routé</option>
                  </select>
                </div>
                <div>
                  {intfMode === 'access' ? (
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">VLAN Access</label>
                      <input
                        type="number"
                        min="1"
                        max="4094"
                        value={intfVlan}
                        onChange={(e) => setIntfVlan(e.target.value)}
                        placeholder="10"
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono"
                      />
                    </div>
                  ) : intfMode === 'trunk' ? (
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">VLANs autorisés</label>
                      <input
                        type="text"
                        value={intfAllowedVlans}
                        onChange={(e) => setIntfAllowedVlans(e.target.value)}
                        placeholder="10,20,30-40"
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono"
                      />
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Adresse IP</label>
                  <input
                    type="text"
                    value={intfIp}
                    onChange={(e) => setIntfIp(e.target.value)}
                    placeholder="192.168.10.1"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Masque de sous-réseau</label>
                  <input
                    type="text"
                    value={intfMask}
                    onChange={(e) => setIntfMask(e.target.value)}
                    placeholder="255.255.255.0"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono"
                  />
                </div>
              </div>

              {/* Remote Link */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                <span className="font-bold text-slate-700 block text-[11px]">Connexion à un équipement distant :</span>
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={connectedEqId}
                    onChange={(e) => setConnectedEqId(e.target.value)}
                    className="border border-slate-300 rounded px-2 py-1.5 bg-white"
                  >
                    <option value="">Aucun équipement lié</option>
                    {allEquipments.map((eq) => (
                      <option key={eq.id} value={eq.id}>{eq.name} ({eq.category})</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={connectedIntfName}
                    onChange={(e) => setConnectedIntfName(e.target.value)}
                    placeholder="Port distant (ex. Gi0/1)"
                    className="border border-slate-300 rounded px-2 py-1.5 font-mono bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Description</label>
                <input
                  type="text"
                  value={intfDesc}
                  onChange={(e) => setIntfDesc(e.target.value)}
                  placeholder="Liaison uplink vers FW-01"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddIntfModal(false)}
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

      {/* Modal Ajout Configuration */}
      {showAddConfigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Ajouter un paramètre de configuration</h3>
              <button onClick={() => setShowAddConfigModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateConfig} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Catégorie</label>
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
                <label className="block font-semibold text-slate-700 mb-1">Clé du paramètre *</label>
                <input
                  type="text"
                  required
                  value={confKey}
                  onChange={(e) => setConfKey(e.target.value)}
                  placeholder="ex. snmp_community, default_gateway"
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
                  id="secret_check"
                  checked={confIsSecret}
                  onChange={(e) => setConfIsSecret(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="secret_check" className="font-semibold text-slate-700">
                  Valeur sensible / secrète (masquer par défaut avec &lt;SECRET_MASQUÉ&gt;)
                </label>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Description</label>
                <input
                  type="text"
                  value={confDesc}
                  onChange={(e) => setConfDesc(e.target.value)}
                  placeholder="Usage ou justification..."
                  className="w-full border border-slate-300 rounded-lg px-3 py-2"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddConfigModal(false)}
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
