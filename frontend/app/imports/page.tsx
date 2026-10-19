'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import {
  Upload, FileSpreadsheet, Terminal, CheckCircle2, AlertTriangle,
  XCircle, ArrowRight, ArrowLeft, RefreshCw, Layers, ShieldCheck,
  FileText, Database, Server, Network, Filter, Download
} from 'lucide-react';
import {
  apiFetch, Project, ImportUploadResponse,
  ImportPreviewResponse, ImportApplyResponse, ImportJob
} from '@/lib/api';

const EQUIPMENT_FIELDS = [
  { value: '', label: '-- Ignorer cette colonne --' },
  { value: 'name', label: 'Nom / Hostname (Obligatoire)' },
  { value: 'category', label: 'Catégorie (switch, firewall, serveur...)' },
  { value: 'manufacturer', label: 'Constructeur (Cisco, Dell...)' },
  { value: 'model', label: 'Modèle' },
  { value: 'serial_number', label: 'Numéro de série' },
  { value: 'management_ip', label: 'Adresse IP de gestion' },
  { value: 'role', label: 'Rôle / Fonction' },
  { value: 'firmware_version', label: 'Version Firmware / OS' },
  { value: 'site_name', label: 'Nom du Site' },
  { value: 'location_name', label: 'Emplacement / Baie' },
];

const SEGMENT_FIELDS = [
  { value: '', label: '-- Ignorer cette colonne --' },
  { value: 'vlan_id', label: 'Numéro de VLAN (1-4094)' },
  { value: 'name', label: 'Nom du VLAN / Sous-réseau' },
  { value: 'cidr', label: 'CIDR (ex. 192.168.1.0/24)' },
  { value: 'gateway', label: 'Passerelle IP' },
  { value: 'dhcp_range', label: 'Plage DHCP' },
  { value: 'zone', label: 'Zone de sécurité' },
  { value: 'description', label: 'Description / Remarques' },
];

export default function ImportsPage() {
  const [activeTab, setActiveTab] = useState<'wizard' | 'history'>('wizard');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [step, setStep] = useState<number>(1);

  // Step 1: Upload state
  const [targetType, setTargetType] = useState<string>('equipment');
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<ImportUploadResponse | null>(null);

  // Step 2: Mapping state
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [isPreviewing, setIsPreviewing] = useState<boolean>(false);

  // Step 3: Preview state
  const [previewResult, setPreviewResult] = useState<ImportPreviewResponse | null>(null);
  const [previewFilter, setPreviewFilter] = useState<'all' | 'valid' | 'conflict' | 'error'>('all');
  const [conflictResolution, setConflictResolution] = useState<'skip' | 'overwrite' | 'create_new'>('skip');
  const [isApplying, setIsApplying] = useState<boolean>(false);

  // Step 4: Final report state
  const [applyResult, setApplyResult] = useState<ImportApplyResponse | null>(null);

  // Template download state
  const [downloadingTemplate, setDownloadingTemplate] = useState<string | null>(null);

  const handleDownloadTemplate = async (templateType: 'equipment' | 'segments' | 'complete') => {
    try {
      setDownloadingTemplate(templateType);
      const token = typeof window !== 'undefined' ? localStorage.getItem('infradoc_token') : null;
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${apiBase}/api/imports/templates?type=${templateType}`, {
        headers,
      });

      if (!res.ok) {
        let msg = 'Erreur lors du téléchargement du modèle Excel';
        try {
          const err = await res.json();
          msg = err.detail || msg;
        } catch {}
        throw new Error(msg);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      let filename = 'template_inventaire_equipements.xlsx';
      if (templateType === 'segments') {
        filename = 'template_vlans_reseaux.xlsx';
      } else if (templateType === 'complete') {
        filename = 'template_import_inventaire_complet.xlsx';
      }

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(err.message || 'Impossible de télécharger le modèle Excel');
    } finally {
      setDownloadingTemplate(null);
    }
  };

  // History state
  const [importHistory, setImportHistory] = useState<ImportJob[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId && activeTab === 'history') {
      loadHistory();
    }
  }, [selectedProjectId, activeTab]);

  const loadProjects = async () => {
    try {
      const data = await apiFetch<Project[]>('/api/projects');
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
      }
    } catch (err: any) {
      console.error('Erreur chargement projets:', err);
    }
  };

  const loadHistory = async () => {
    if (!selectedProjectId) return;
    setLoadingHistory(true);
    try {
      const data = await apiFetch<ImportJob[]>(`/api/imports?project_id=${selectedProjectId}`);
      setImportHistory(data);
    } catch (err: any) {
      console.error('Erreur historique:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMsg(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !selectedProjectId) {
      setErrorMsg('Veuillez sélectionner un projet et un fichier.');
      return;
    }
    setIsUploading(true);
    setErrorMsg(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project_id', selectedProjectId);
      formData.append('target_type', targetType);

      const res = await apiFetch<ImportUploadResponse>('/api/imports/upload', {
        method: 'POST',
        body: formData,
      });

      setUploadResult(res);
      setMappings(res.suggested_mapping || {});
      
      // If CLI config or auto previewable, jump straight to preview
      if (res.file_type === 'cisco_ios' || res.file_type === 'fortinet_cli') {
        await executePreview(res.job_id, res.suggested_mapping, res.detected_target);
        setStep(3);
      } else {
        setStep(2);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Erreur lors de l'envoi du fichier.");
    } finally {
      setIsUploading(false);
    }
  };

  const executePreview = async (jobId: string, mapToUse: Record<string, string>, target: string) => {
    setIsPreviewing(true);
    setErrorMsg(null);
    try {
      const res = await apiFetch<ImportPreviewResponse>(`/api/imports/${jobId}/preview`, {
        method: 'POST',
        body: JSON.stringify({
          mappings: mapToUse,
          target_type: target,
        }),
      });
      setPreviewResult(res);
      setStep(3);
    } catch (err: any) {
      setErrorMsg(err.message || "Erreur lors de l'analyse du prévisualiseur.");
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleApply = async () => {
    if (!uploadResult?.job_id) return;
    setIsApplying(true);
    setErrorMsg(null);
    try {
      const res = await apiFetch<ImportApplyResponse>(`/api/imports/${uploadResult.job_id}/apply`, {
        method: 'POST',
        body: JSON.stringify({
          conflict_resolution: conflictResolution,
        }),
      });
      setApplyResult(res);
      setStep(4);
    } catch (err: any) {
      setErrorMsg(err.message || "Erreur lors de l'application de l'import.");
    } finally {
      setIsApplying(false);
    }
  };

  const resetWizard = () => {
    setStep(1);
    setFile(null);
    setUploadResult(null);
    setPreviewResult(null);
    setApplyResult(null);
    setErrorMsg(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const filteredPreviewItems = previewResult?.items.filter(item => {
    if (previewFilter === 'all') return true;
    return item.status === previewFilter;
  }) || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Imports & Ingestion de Données</h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Lot 4 Actif
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Parseurs automatisés Excel (.xlsx), CSV, et extractions de configurations CLI (Cisco IOS, Fortinet).
          </p>
        </div>

        {/* Project Selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-700">Projet cible :</label>
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs bg-white text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.reference} - {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('wizard')}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'wizard'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Upload className="w-4 h-4" />
          Nouvel Ingestion / Import
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'history'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Database className="w-4 h-4" />
          Historique des Imports ({importHistory.length})
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-xs text-red-700">
          <XCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ----------------- WIZARD TAB ----------------- */}
      {activeTab === 'wizard' && (
        <div className="space-y-6">
          {/* Stepper Header */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
            <div className="grid grid-cols-4 gap-2 text-center text-xs">
              <div className={`p-2 rounded-lg font-medium flex items-center justify-center gap-2 ${
                step >= 1 ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'text-slate-400'
              }`}>
                <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px]">1</span>
                <span>Source & Fichier</span>
              </div>
              <div className={`p-2 rounded-lg font-medium flex items-center justify-center gap-2 ${
                step >= 2 ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'text-slate-400'
              }`}>
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  step >= 2 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'
                }`}>2</span>
                <span>Mapping Colonnes</span>
              </div>
              <div className={`p-2 rounded-lg font-medium flex items-center justify-center gap-2 ${
                step >= 3 ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'text-slate-400'
              }`}>
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  step >= 3 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'
                }`}>3</span>
                <span>Aperçu & Conflits</span>
              </div>
              <div className={`p-2 rounded-lg font-medium flex items-center justify-center gap-2 ${
                step >= 4 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'text-slate-400'
              }`}>
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  step >= 4 ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
                }`}>4</span>
                <span>Rapport & Succès</span>
              </div>
            </div>
          </div>

          {/* STEP 1: Upload & Format Choice */}
          {step === 1 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6 shadow-xs">
              <div>
                <h2 className="text-sm font-bold text-slate-900">1. Choisissez le type de données et le fichier source</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  L'import est strictement non-destructif : une vérification des doublons est effectuée avant tout enregistrement.
                </p>
              </div>

              {/* Target Type Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  type="button"
                  onClick={() => setTargetType('equipment')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    targetType === 'equipment'
                      ? 'border-blue-600 bg-blue-50/50 ring-2 ring-blue-500/20'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-blue-100 text-blue-700">
                      <Server className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900">Inventaire Équipements</h3>
                      <p className="text-[11px] text-slate-500 mt-0.5">Excel (.xlsx), CSV</p>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-3">
                    Switches, serveurs, routeurs, firewalls avec leurs modèles, séries, et adresses IP.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setTargetType('network_segments')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    targetType === 'network_segments'
                      ? 'border-blue-600 bg-blue-50/50 ring-2 ring-blue-500/20'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-indigo-100 text-indigo-700">
                      <Network className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900">Plan d'Adressage & VLANs</h3>
                      <p className="text-[11px] text-slate-500 mt-0.5">Excel (.xlsx), CSV</p>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-3">
                    VLANs (1-4094), sous-réseaux CIDR, passerelles IP et zones de sécurité.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setTargetType('cli')}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    targetType === 'cli'
                      ? 'border-blue-600 bg-blue-50/50 ring-2 ring-blue-500/20'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-slate-800 text-emerald-400">
                      <Terminal className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900">Configuration CLI Matériel</h3>
                      <p className="text-[11px] text-slate-500 mt-0.5">Cisco IOS, Fortinet (.cfg, .txt)</p>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-3">
                    Extraction des interfaces physiques, SVI, VLANs, et secrets masqués automatiquement.
                  </p>
                </button>
              </div>

              {/* Excel Templates Download Section */}
              <div className="bg-gradient-to-r from-blue-50/90 via-indigo-50/60 to-slate-50 border border-blue-200 rounded-xl p-4.5 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="p-2.5 bg-blue-600 text-white rounded-xl shrink-0 shadow-xs">
                    <FileSpreadsheet className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-xs font-bold text-slate-900">
                        Modèles Excel pré-formatés à remplir
                      </h3>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200 uppercase tracking-wide">
                        Prêt à l'emploi
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 max-w-2xl leading-relaxed">
                      Téléchargez une matrice pré-remplie avec en-têtes reconnus automatiquement, règles de validation, commentaires intégrés et exemples concrets.
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleDownloadTemplate('equipment')}
                    disabled={downloadingTemplate !== null}
                    className="px-3 py-1.5 bg-white border border-slate-300 hover:border-blue-600 hover:text-blue-700 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-all disabled:opacity-50 cursor-pointer"
                    title="Télécharger la matrice d'équipements avec colonnes types"
                  >
                    {downloadingTemplate === 'equipment' ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-600" />
                    ) : (
                      <Download className="w-3.5 h-3.5 text-blue-600" />
                    )}
                    <span>Modèle Équipements (.xlsx)</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDownloadTemplate('segments')}
                    disabled={downloadingTemplate !== null}
                    className="px-3 py-1.5 bg-white border border-slate-300 hover:border-indigo-600 hover:text-indigo-700 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-all disabled:opacity-50 cursor-pointer"
                    title="Télécharger la matrice de plan d'adressage et VLANs"
                  >
                    {downloadingTemplate === 'segments' ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                    ) : (
                      <Download className="w-3.5 h-3.5 text-indigo-600" />
                    )}
                    <span>Modèle VLANs (.xlsx)</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDownloadTemplate('complete')}
                    disabled={downloadingTemplate !== null}
                    className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-all disabled:opacity-50 cursor-pointer"
                    title="Télécharger le classeur multi-onglets complet (Équipements + VLANs + Guide)"
                  >
                    {downloadingTemplate === 'complete' ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Download className="w-3.5 h-3.5" />
                    )}
                    <span>Classeur Complet (.xlsx)</span>
                  </button>
                </div>
              </div>

              {/* Upload Dropzone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-50/50"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv,.txt,.cfg,.conf,.ios"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <Upload className="w-10 h-10 mx-auto text-slate-400 mb-2" />
                <p className="text-xs font-semibold text-slate-700">
                  {file ? file.name : 'Cliquez pour sélectionner ou glissez un fichier ici'}
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Formats supportés : .xlsx, .csv, .txt, .cfg (Max. 20 Mo)
                </p>
                {file && (
                  <span className="inline-block mt-3 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">
                    {(file.size / 1024).toFixed(1)} Ko - Prêt pour l'analyse
                  </span>
                )}
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={!file || isUploading}
                  onClick={handleUpload}
                  className="px-5 py-2 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 shadow-xs"
                >
                  {isUploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Analyse du fichier en cours...
                    </>
                  ) : (
                    <>
                      <span>Étape suivante : Analyser</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Column Mapping */}
          {step === 2 && uploadResult && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6 shadow-xs">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-slate-900">2. Associez les colonnes source aux champs cibles</h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Fichier : <span className="font-semibold text-slate-700">{uploadResult.filename}</span> ({uploadResult.total_raw_rows} lignes détectées)
                  </p>
                </div>
                <button
                  onClick={() => setStep(1)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Changer de fichier
                </button>
              </div>

              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
                    <tr>
                      <th className="px-4 py-3">Colonne source détectée</th>
                      <th className="px-4 py-3">Échantillon (Ligne 1)</th>
                      <th className="px-4 py-3">Champ cible dans la base</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-800">
                    {uploadResult.headers.map((colName) => {
                      const sampleVal = uploadResult.sample_rows[0]?.[colName] ?? '-';
                      const currentField = mappings[colName] || '';
                      const fieldOptions = targetType === 'network_segments' ? SEGMENT_FIELDS : EQUIPMENT_FIELDS;

                      return (
                        <tr key={colName} className="hover:bg-slate-50/70">
                          <td className="px-4 py-3 font-semibold text-slate-900">{colName}</td>
                          <td className="px-4 py-3 text-slate-500 font-mono text-[11px] truncate max-w-xs">{sampleVal}</td>
                          <td className="px-4 py-2">
                            <select
                              value={currentField}
                              onChange={(e) => setMappings({ ...mappings, [colName]: e.target.value })}
                              className="w-full border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-xs text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                            >
                              {fieldOptions.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                  {opt.label}
                                </option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Précédent
                </button>
                <button
                  type="button"
                  disabled={isPreviewing}
                  onClick={() => executePreview(uploadResult.job_id, mappings, uploadResult.detected_target)}
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 shadow-xs"
                >
                  {isPreviewing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Calcul des conflits...
                    </>
                  ) : (
                    <>
                      <span>Étape suivante : Prévisualiser & Vérifier</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Preview & Conflicts Detection */}
          {step === 3 && previewResult && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6 shadow-xs">
              <div>
                <h2 className="text-sm font-bold text-slate-900">3. Prévisualisation et Détection des Conflits</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Vérification de la validité des formats IP, VLANs et détection automatique des équipements existants.
                </p>
              </div>

              {/* KPI Counters */}
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
                  <span className="text-xs text-slate-500 font-medium">Total Éléments</span>
                  <p className="text-xl font-bold text-slate-800 mt-1">{previewResult.total_items}</p>
                </div>
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-center">
                  <span className="text-xs text-emerald-700 font-medium flex items-center justify-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Valides
                  </span>
                  <p className="text-xl font-bold text-emerald-800 mt-1">{previewResult.valid_count}</p>
                </div>
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-center">
                  <span className="text-xs text-amber-700 font-medium flex items-center justify-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Conflits / Doublons
                  </span>
                  <p className="text-xl font-bold text-amber-800 mt-1">{previewResult.conflict_count}</p>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-xl p-3.5 text-center">
                  <span className="text-xs text-red-700 font-medium flex items-center justify-center gap-1">
                    <XCircle className="w-3.5 h-3.5" /> Erreurs de Validation
                  </span>
                  <p className="text-xl font-bold text-red-800 mt-1">{previewResult.error_count}</p>
                </div>
              </div>

              {/* Conflict Resolution Strategy */}
              {previewResult.conflict_count > 0 && (
                <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                    <ShieldCheck className="w-4 h-4 text-amber-700" />
                    Stratégie de résolution des doublons détectés :
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <label className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                      conflictResolution === 'skip'
                        ? 'border-amber-600 bg-white ring-1 ring-amber-600 font-semibold text-amber-900'
                        : 'border-amber-200 bg-amber-50/50 text-slate-700'
                    }`}>
                      <input
                        type="radio"
                        name="conflict_res"
                        value="skip"
                        checked={conflictResolution === 'skip'}
                        onChange={() => setConflictResolution('skip')}
                        className="mr-2"
                      />
                      Ignorer les doublons (Recommandé)
                      <p className="text-[11px] text-slate-500 font-normal mt-1">Conserve les équipements existants intacts.</p>
                    </label>

                    <label className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                      conflictResolution === 'overwrite'
                        ? 'border-amber-600 bg-white ring-1 ring-amber-600 font-semibold text-amber-900'
                        : 'border-amber-200 bg-amber-50/50 text-slate-700'
                    }`}>
                      <input
                        type="radio"
                        name="conflict_res"
                        value="overwrite"
                        checked={conflictResolution === 'overwrite'}
                        onChange={() => setConflictResolution('overwrite')}
                        className="mr-2"
                      />
                      Écraser les données existantes
                      <p className="text-[11px] text-slate-500 font-normal mt-1">Met à jour les attributs avec les valeurs du fichier.</p>
                    </label>

                    <label className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                      conflictResolution === 'create_new'
                        ? 'border-amber-600 bg-white ring-1 ring-amber-600 font-semibold text-amber-900'
                        : 'border-amber-200 bg-amber-50/50 text-slate-700'
                    }`}>
                      <input
                        type="radio"
                        name="conflict_res"
                        value="create_new"
                        checked={conflictResolution === 'create_new'}
                        onChange={() => setConflictResolution('create_new')}
                        className="mr-2"
                      />
                      Créer sous un nouveau nom
                      <p className="text-[11px] text-slate-500 font-normal mt-1">Ajoute un suffixe "_imported" pour isoler l'élément.</p>
                    </label>
                  </div>
                </div>
              )}

              {/* Filter Tabs */}
              <div className="flex items-center justify-between">
                <div className="flex gap-2">
                  <button
                    onClick={() => setPreviewFilter('all')}
                    className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                      previewFilter === 'all'
                        ? 'bg-slate-900 text-white border-slate-900'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    Tous ({previewResult.items.length})
                  </button>
                  <button
                    onClick={() => setPreviewFilter('valid')}
                    className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                      previewFilter === 'valid'
                        ? 'bg-emerald-600 text-white border-emerald-600'
                        : 'bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-50'
                    }`}
                  >
                    Valides ({previewResult.valid_count})
                  </button>
                  <button
                    onClick={() => setPreviewFilter('conflict')}
                    className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                      previewFilter === 'conflict'
                        ? 'bg-amber-600 text-white border-amber-600'
                        : 'bg-white text-amber-700 border-amber-200 hover:bg-amber-50'
                    }`}
                  >
                    Conflits ({previewResult.conflict_count})
                  </button>
                  <button
                    onClick={() => setPreviewFilter('error')}
                    className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                      previewFilter === 'error'
                        ? 'bg-red-600 text-white border-red-600'
                        : 'bg-white text-red-700 border-red-200 hover:bg-red-50'
                    }`}
                  >
                    Erreurs ({previewResult.error_count})
                  </button>
                </div>
              </div>

              {/* Preview Table */}
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
                    <tr>
                      <th className="px-3 py-2.5 w-12 text-center">#</th>
                      <th className="px-3 py-2.5">Statut</th>
                      <th className="px-4 py-2.5">Nom / Élément</th>
                      <th className="px-3 py-2.5">Famille / Type</th>
                      <th className="px-3 py-2.5">IP Management</th>
                      <th className="px-4 py-2.5">Détails / Diagnostic</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-800">
                    {filteredPreviewItems.map((item) => {
                      const data = item.data;
                      const isCLI = !!data.parsed_interfaces_count;

                      return (
                        <tr key={item.row_number} className="hover:bg-slate-50/70">
                          <td className="px-3 py-3 text-center text-slate-400 font-mono text-[11px]">
                            {item.row_number}
                          </td>
                          <td className="px-3 py-3">
                            {item.status === 'valid' && (
                              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 w-max">
                                <CheckCircle2 className="w-3 h-3" /> Valide
                              </span>
                            )}
                            {item.status === 'conflict' && (
                              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1 w-max">
                                <AlertTriangle className="w-3 h-3" /> Conflit
                              </span>
                            )}
                            {item.status === 'error' && (
                              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-red-50 text-red-700 border border-red-200 flex items-center gap-1 w-max">
                                <XCircle className="w-3 h-3" /> Erreur
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-900">
                            {data.name || (data.vlan_id ? `VLAN ${data.vlan_id} - ${data.name}` : '-')}
                          </td>
                          <td className="px-3 py-3 text-slate-600">
                            {data.category || (data.vlan_id ? 'VLAN / Segment' : '-')}
                          </td>
                          <td className="px-3 py-3 font-mono text-slate-700 text-[11px]">
                            {data.management_ip || data.gateway || '-'}
                          </td>
                          <td className="px-4 py-3 text-[11px]">
                            {item.conflicts.length > 0 && (
                              <div className="text-amber-800 font-medium">
                                {item.conflicts.join(', ')}
                              </div>
                            )}
                            {item.errors.length > 0 && (
                              <div className="text-red-700 font-medium">
                                {item.errors.join(', ')}
                              </div>
                            )}
                            {item.conflicts.length === 0 && item.errors.length === 0 && (
                              <span className="text-slate-500">
                                {isCLI ? (
                                  `${data.parsed_interfaces_count} interfaces, ${data.parsed_segments_count} VLANs, ${data.parsed_configs_count} configs extraites`
                                ) : (
                                  `Prêt pour création (${data.model || data.cidr || 'aucun conflit'})`
                                )}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={() => setStep(uploadResult?.file_type === 'cisco_ios' ? 1 : 2)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Précédent
                </button>
                <button
                  type="button"
                  disabled={isApplying || (previewResult.valid_count === 0 && previewResult.conflict_count === 0)}
                  onClick={handleApply}
                  className="px-6 py-2 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2 shadow-xs"
                >
                  {isApplying ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Application de l'import...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Confirmer et Appliquer l'Importation</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Success & Final Report */}
          {step === 4 && applyResult && (
            <div className="bg-white rounded-xl border border-slate-200 p-8 space-y-6 shadow-xs text-center">
              <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mx-auto text-emerald-600">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div className="max-w-md mx-auto space-y-1">
                <h2 className="text-base font-bold text-slate-900">Importation Terminée avec Succès !</h2>
                <p className="text-xs text-slate-500">{applyResult.message}</p>
              </div>

              {/* Results Grid */}
              <div className="grid grid-cols-4 gap-4 max-w-xl mx-auto text-center">
                <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                  <span className="text-[11px] text-emerald-700 font-semibold">Créés</span>
                  <p className="text-xl font-bold text-emerald-800">{applyResult.created_count}</p>
                </div>
                <div className="p-3 bg-blue-50 rounded-xl border border-blue-100">
                  <span className="text-[11px] text-blue-700 font-semibold">Mis à jour</span>
                  <p className="text-xl font-bold text-blue-800">{applyResult.updated_count}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-semibold">Ignorés</span>
                  <p className="text-xl font-bold text-slate-700">{applyResult.skipped_count}</p>
                </div>
                <div className="p-3 bg-red-50 rounded-xl border border-red-100">
                  <span className="text-[11px] text-red-700 font-semibold">Erreurs</span>
                  <p className="text-xl font-bold text-red-800">{applyResult.error_count}</p>
                </div>
              </div>

              <div className="flex justify-center items-center gap-3 pt-4">
                <button
                  onClick={resetWizard}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Nouvel import
                </button>
                <Link
                  href="/inventory"
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 flex items-center gap-1.5 shadow-xs"
                >
                  <Server className="w-3.5 h-3.5" />
                  Consulter l'Inventaire
                </Link>
                <Link
                  href="/configurations"
                  className="px-5 py-2 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900 flex items-center gap-1.5 shadow-xs"
                >
                  <Terminal className="w-3.5 h-3.5" />
                  Voir les Configurations
                </Link>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ----------------- HISTORY TAB ----------------- */}
      {activeTab === 'history' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Historique des Ingestions et Imports</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Traçabilité complète des fichiers traités, dates d'exécution et rapports volumétriques.
              </p>
            </div>
            <button
              onClick={loadHistory}
              disabled={loadingHistory}
              className="px-3 py-1.5 text-xs text-slate-700 hover:text-slate-900 border border-slate-200 rounded-lg flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
              Actualiser
            </button>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
                <tr>
                  <th className="px-4 py-3">Fichier</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Cible</th>
                  <th className="px-4 py-3">Statut</th>
                  <th className="px-4 py-3">Créés</th>
                  <th className="px-4 py-3">Mis à jour</th>
                  <th className="px-4 py-3">Ignorés</th>
                  <th className="px-4 py-3">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {importHistory.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                      Aucun import enregistré pour ce projet.
                    </td>
                  </tr>
                ) : (
                  importHistory.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-50/70">
                      <td className="px-4 py-3 font-semibold text-slate-900 flex items-center gap-2">
                        {job.file_type === 'excel' ? (
                          <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                        ) : job.file_type === 'csv' ? (
                          <FileText className="w-4 h-4 text-blue-600" />
                        ) : (
                          <Terminal className="w-4 h-4 text-slate-700" />
                        )}
                        {job.filename}
                      </td>
                      <td className="px-4 py-3 uppercase text-[11px] font-mono text-slate-600">
                        {job.file_type}
                      </td>
                      <td className="px-4 py-3 text-slate-600 capitalize">
                        {job.target_type}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                          job.status === 'applied'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : job.status === 'previewed'
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : 'bg-slate-100 text-slate-600'
                        }`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-bold text-emerald-700">{job.created_count}</td>
                      <td className="px-4 py-3 font-bold text-blue-700">{job.updated_count}</td>
                      <td className="px-4 py-3 text-slate-500">{job.skipped_count}</td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                        {new Date(job.created_at).toLocaleString('fr-FR')}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
