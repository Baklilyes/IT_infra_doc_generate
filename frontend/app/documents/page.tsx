'use client';

import React, { useState, useEffect } from 'react';
import {
  FileText, Cpu, Download, RefreshCw, CheckCircle2,
  Trash2, ShieldAlert, Sparkles, FileSpreadsheet, Lock,
  Layers, Clock, AlertTriangle, ArrowRight, BookOpen
} from 'lucide-react';
import {
  apiFetch, Project, DocumentItem, DocumentStatusResponse
} from '@/lib/api';

const DOC_TYPES = [
  {
    type: 'hld',
    title: "Dossier d'Architecture Générale (HLD)",
    subtitle: "High Level Design & Principes Directeurs",
    description: "Vision d'ensemble, périmètre, stratégie de résilience, choix technologiques et dimensionnement global.",
    badgeColor: "bg-blue-50 text-blue-700 border-blue-200",
    iconColor: "text-blue-600 bg-blue-100",
  },
  {
    type: 'lld',
    title: "Dossier d'Architecture Technique (LLD)",
    subtitle: "Low Level Design & Spécifications Détaillées",
    description: "Inventaire complet, spécifications port à port, plan d'adressage IP exhaustif, segmentation VLAN et matrice de flux.",
    badgeColor: "bg-indigo-50 text-indigo-700 border-indigo-200",
    iconColor: "text-indigo-600 bg-indigo-100",
  },
  {
    type: 'config_annexes',
    title: "Annexes de Configuration Matérielle",
    subtitle: "Paramètres Techniques & Pré-déploiement",
    description: "Configurations cibles par équipement (NTP, DNS, Syslog, SNMP) avec masquage automatique des secrets <SECRET_MASQUÉ>.",
    badgeColor: "bg-amber-50 text-amber-700 border-amber-200",
    iconColor: "text-amber-600 bg-amber-100",
  },
  {
    type: 'commissioning',
    title: "Dossier de Recette & Mise en Service",
    subtitle: "Plan de Validation Opérationnelle & PV",
    description: "Fiches de tests unitaires, validation des liaisons et du routage, grille d'émargement et procès-verbal de recette.",
    badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
    iconColor: "text-emerald-600 bg-emerald-100",
  },
];

export default function DocumentsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [docStatus, setDocStatus] = useState<DocumentStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [generatingType, setGeneratingType] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form options per document
  const [format, setFormat] = useState<'docx' | 'pdf'>('docx');
  const [useAi, setUseAi] = useState<boolean>(true);
  const [version, setVersion] = useState<string>('1.0');

  useEffect(() => {
    loadProjects();
    loadStatus();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadDocuments();
    }
  }, [selectedProjectId]);

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

  const loadStatus = async () => {
    try {
      const data = await apiFetch<DocumentStatusResponse>('/api/documents/ai-status');
      setDocStatus(data);
    } catch {
      // offline fallback
    }
  };

  const loadDocuments = async () => {
    if (!selectedProjectId) return;
    setLoading(true);
    try {
      const data = await apiFetch<DocumentItem[]>(`/api/projects/${selectedProjectId}/documents`);
      setDocuments(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors du chargement des documents.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (docType: string) => {
    if (!selectedProjectId) return;
    setGeneratingType(docType);
    setErrorMsg(null);

    try {
      await apiFetch(`/api/projects/${selectedProjectId}/documents/generate`, {
        method: 'POST',
        body: JSON.stringify({
          document_type: docType,
          file_format: format,
          use_ai: useAi,
          version: version || '1.0',
        }),
      });
      await loadDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la génération du document.');
    } finally {
      setGeneratingType(null);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Voulez-vous vraiment supprimer ce document ?')) return;
    try {
      await apiFetch(`/api/documents/${docId}`, { method: 'DELETE' });
      await loadDocuments();
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la suppression.');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} Mo`;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Génération Documentaire &amp; IA Locale</h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Lot 7 Actif
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Génération bilingue haute fidélité (DOCX &amp; PDF) avec page de garde, sommaire, masquage des secrets et copilotage IA local.
          </p>
        </div>

        {/* Project Selector & AI Status */}
        <div className="flex items-center gap-3">
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

          {/* AI Status Badge */}
          {docStatus?.ai_status.online ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-[11px] font-semibold">
              <Cpu className="w-3.5 h-3.5 text-emerald-600" />
              <span>Ollama En Ligne</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-[11px] font-semibold" title="Mode secours actif : templates déterministes par défaut">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              <span>IA Hors Ligne (Secours Déterministe)</span>
            </div>
          )}
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-xs text-red-700">
          <ShieldAlert className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Global Generation Settings Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-700">Format de sortie :</span>
            <div className="flex gap-1.5">
              <button
                type="button"
                onClick={() => setFormat('docx')}
                className={`px-3 py-1 rounded text-xs font-semibold border transition-colors ${
                  format === 'docx'
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                }`}
              >
                Microsoft Word (.docx)
              </button>
              <button
                type="button"
                onClick={() => setFormat('pdf')}
                className={`px-3 py-1 rounded text-xs font-semibold border transition-colors ${
                  format === 'pdf'
                    ? 'bg-red-600 text-white border-red-600'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                }`}
              >
                Adobe PDF (.pdf)
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-700">Version :</span>
            <input
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              className="w-16 border border-slate-300 rounded px-2 py-1 text-xs text-center font-mono"
            />
          </div>

          <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={useAi}
              onChange={(e) => setUseAi(e.target.checked)}
              className="rounded text-blue-600 focus:ring-blue-500"
            />
            <span className="flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Copilote IA local (synthèses narratives)
            </span>
          </label>
        </div>

        <div className="text-[11px] text-slate-500 italic">
          * Les secrets sont systématiquement masqués &lt;SECRET_MASQUÉ&gt;.
        </div>
      </div>

      {/* 4 Deliverable Generator Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {DOC_TYPES.map((dt) => {
          const isGenerating = generatingType === dt.type;

          return (
            <div key={dt.type} className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-all">
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${dt.iconColor}`}>
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">{dt.title}</h3>
                      <p className="text-[11px] text-slate-500">{dt.subtitle}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${dt.badgeColor}`}>
                    {dt.type}
                  </span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">
                  {dt.description}
                </p>
              </div>

              <div className="pt-5 mt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">
                  Format : <span className="font-semibold uppercase text-slate-700">{format}</span>
                </span>

                <button
                  onClick={() => handleGenerate(dt.type)}
                  disabled={isGenerating || !selectedProjectId}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 disabled:opacity-50 flex items-center gap-2 shadow-xs transition-colors"
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Génération en cours...
                    </>
                  ) : (
                    <>
                      <BookOpen className="w-3.5 h-3.5" />
                      Générer ce document
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Generated Documents History Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-xs">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Documents Générés pour ce Projet</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Livrables compilés, versionnés et téléchargeables au format DOCX ou PDF scellé.
            </p>
          </div>
          <button
            onClick={loadDocuments}
            disabled={loading}
            className="px-3 py-1.5 text-xs text-slate-700 hover:text-slate-900 border border-slate-200 rounded-lg flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </button>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
              <tr>
                <th className="px-4 py-3">Format</th>
                <th className="px-4 py-3">Titre du Document</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Taille</th>
                <th className="px-4 py-3">IA Enrichie</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    Aucun document généré pour l'instant. Choisissez un livrable ci-dessus pour lancer la compilation.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                        doc.file_format === 'docx'
                          ? 'bg-blue-100 text-blue-800 border border-blue-200'
                          : 'bg-red-100 text-red-800 border border-red-200'
                      }`}>
                        {doc.file_format}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-900 max-w-xs truncate">
                      {doc.title}
                    </td>
                    <td className="px-4 py-3 uppercase text-[11px] font-mono text-slate-600">
                      {doc.document_type}
                    </td>
                    <td className="px-4 py-3 font-mono font-medium">v{doc.version}</td>
                    <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                      {formatFileSize(doc.file_size)}
                    </td>
                    <td className="px-4 py-3">
                      {doc.ai_enhanced ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1 w-max">
                          <Sparkles className="w-3 h-3 text-amber-600" /> Oui
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px]">Non (Template)</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                      {new Date(doc.created_at).toLocaleString('fr-FR')}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <a
                          href={doc.download_url}
                          download
                          className="px-2.5 py-1 bg-blue-600 text-white rounded text-[11px] font-semibold hover:bg-blue-700 flex items-center gap-1 shadow-2xs"
                        >
                          <Download className="w-3 h-3" />
                          Télécharger
                        </a>
                        {!doc.is_locked && (
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="p-1 text-slate-400 hover:text-red-600 rounded"
                            title="Supprimer ce document"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
