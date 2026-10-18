'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ShieldAlert, ShieldCheck, AlertTriangle, XCircle, Info,
  RefreshCw, CheckCircle2, Lock, ArrowRight, ExternalLink,
  MessageSquare, Trash2, Filter, Layers, FileCheck, HelpCircle
} from 'lucide-react';
import {
  apiFetch, Project, ConsistencyReport, Finding, CanPublishResponse
} from '@/lib/api';

export default function ValidationsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [report, setReport] = useState<ConsistencyReport | null>(null);
  const [canPublish, setCanPublish] = useState<CanPublishResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [runningChecks, setRunningChecks] = useState<boolean>(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'blocking' | 'warning' | 'info' | 'overridden'>('all');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Override Modal state
  const [overrideFinding, setOverrideFinding] = useState<Finding | null>(null);
  const [justification, setJustification] = useState<string>('');
  const [submittingOverride, setSubmittingOverride] = useState<boolean>(false);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadValidationReport();
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

  const loadValidationReport = async () => {
    if (!selectedProjectId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const [repData, pubData] = await Promise.all([
        apiFetch<ConsistencyReport>(`/api/projects/${selectedProjectId}/validations/latest`),
        apiFetch<CanPublishResponse>(`/api/projects/${selectedProjectId}/validations/can-publish`),
      ]);
      setReport(repData);
      setCanPublish(pubData);
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors du chargement des contrôles.');
    } finally {
      setLoading(false);
    }
  };

  const runChecks = async () => {
    if (!selectedProjectId) return;
    setRunningChecks(true);
    setErrorMsg(null);
    try {
      const [repData, pubData] = await Promise.all([
        apiFetch<ConsistencyReport>(`/api/projects/${selectedProjectId}/validations/run`, { method: 'POST' }),
        apiFetch<CanPublishResponse>(`/api/projects/${selectedProjectId}/validations/can-publish`),
      ]);
      setReport(repData);
      setCanPublish(pubData);
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de l\'exécution des contrôles de cohérence.');
    } finally {
      setRunningChecks(false);
    }
  };

  const handleOpenOverrideModal = (f: Finding) => {
    setOverrideFinding(f);
    setJustification('');
    setErrorMsg(null);
  };

  const handleCloseOverrideModal = () => {
    setOverrideFinding(null);
    setJustification('');
  };

  const handleSubmitOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideFinding || !selectedProjectId) return;
    if (justification.trim().length < 10) {
      setErrorMsg('La justification technique doit contenir au minimum 10 caractères.');
      return;
    }

    setSubmittingOverride(true);
    setErrorMsg(null);
    try {
      await apiFetch(`/api/projects/${selectedProjectId}/validations/override`, {
        method: 'POST',
        body: JSON.stringify({
          rule_code: overrideFinding.rule_code,
          target_id: overrideFinding.target_id,
          target_type: overrideFinding.target_type,
          severity: overrideFinding.severity,
          justification: justification.trim(),
        }),
      });
      handleCloseOverrideModal();
      await runChecks();
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de l\'enregistrement de la dérogation.');
    } finally {
      setSubmittingOverride(false);
    }
  };

  const handleRevokeOverride = async (overrideId: string) => {
    if (!selectedProjectId || !confirm('Voulez-vous vraiment révoquer cette dérogation ? L\'anomalie redeviendra active.')) return;
    try {
      await apiFetch(`/api/projects/${selectedProjectId}/validations/override/${overrideId}`, {
        method: 'DELETE',
      });
      await runChecks();
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la révocation de la dérogation.');
    }
  };

  const filteredFindings = report?.findings.filter((f) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'overridden') return f.is_overridden;
    if (activeFilter === 'blocking') return f.severity === 'blocking' && !f.is_overridden;
    if (activeFilter === 'warning') return f.severity === 'warning' && !f.is_overridden;
    if (activeFilter === 'info') return f.severity === 'info' && !f.is_overridden;
    return true;
  }) || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Contrôles de Cohérence & Dérogations</h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Lot 5 Actif
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Moteur de règles déterministes indépendant de l'IA (IP, VLANs, CIDR overlap, secrets et conformité documentaire).
          </p>
        </div>

        {/* Project Selector & Actions */}
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

          <button
            onClick={runChecks}
            disabled={runningChecks || !selectedProjectId}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${runningChecks ? 'animate-spin' : ''}`} />
            <span>{runningChecks ? 'Analyse en cours...' : 'Exécuter les contrôles'}</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-xs text-red-700">
          <XCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Global Status Banner (Gatekeeper for Lot 8) */}
      {canPublish && (
        <div className={`p-4 rounded-xl border flex items-center justify-between shadow-xs ${
          canPublish.can_publish
            ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
            : 'bg-red-50/80 border-red-200 text-red-900'
        }`}>
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl ${canPublish.can_publish ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
              {canPublish.can_publish ? (
                <ShieldCheck className="w-6 h-6" />
              ) : (
                <ShieldAlert className="w-6 h-6" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider">
                  {canPublish.can_publish ? 'Conforme pour Publication & Circuit d\'approbation' : 'Publication Bloquée — Non Conforme'}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  canPublish.can_publish ? 'bg-emerald-200 text-emerald-800' : 'bg-red-200 text-red-800'
                }`}>
                  {canPublish.status}
                </span>
              </div>
              <p className="text-xs mt-0.5 font-medium">{canPublish.message}</p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2">
            <Link
              href="/documents"
              className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                canPublish.can_publish
                  ? 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-xs'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed pointer-events-none'
              }`}
            >
              <span>Accéder aux Livrables</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}

      {/* Metric KPI Cards */}
      {report && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-medium">Anomalies Bloquantes</span>
              <XCircle className="w-4 h-4 text-red-500" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{report.blocking_count}</p>
            <p className="text-[11px] text-red-600 mt-1 font-medium">Empêchent la validation documentaire</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-medium">Avertissements</span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{report.warning_count}</p>
            <p className="text-[11px] text-amber-700 mt-1 font-medium">Risques à vérifier ou à déroger</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-medium">Recommandations</span>
              <Info className="w-4 h-4 text-blue-500" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{report.info_count}</p>
            <p className="text-[11px] text-slate-500 mt-1 font-medium">Bonnes pratiques d'exploitation</p>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-medium">Dérogations Actives</span>
              <FileCheck className="w-4 h-4 text-emerald-600" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{report.resolved_count}</p>
            <p className="text-[11px] text-emerald-700 mt-1 font-medium">Motifs horodatés & audités</p>
          </div>
        </div>
      )}

      {/* Filter Tabs & Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Journal des Anomalies et Diagnostics Techniques</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Dernière exécution : {report?.created_at ? new Date(report.created_at).toLocaleString('fr-FR') : 'Non exécuté'}
              {report?.executed_by_name && ` par ${report.executed_by_name}`}
            </p>
          </div>

          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                activeFilter === 'all'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              Tous ({report?.findings.length || 0})
            </button>
            <button
              onClick={() => setActiveFilter('blocking')}
              className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                activeFilter === 'blocking'
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-white text-red-700 border-red-200 hover:bg-red-50'
              }`}
            >
              Bloquants ({report?.blocking_count || 0})
            </button>
            <button
              onClick={() => setActiveFilter('warning')}
              className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                activeFilter === 'warning'
                  ? 'bg-amber-600 text-white border-amber-600'
                  : 'bg-white text-amber-700 border-amber-200 hover:bg-amber-50'
              }`}
            >
              Avertissements ({report?.warning_count || 0})
            </button>
            <button
              onClick={() => setActiveFilter('info')}
              className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                activeFilter === 'info'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-blue-700 border-blue-200 hover:bg-blue-50'
              }`}
            >
              Infos ({report?.info_count || 0})
            </button>
            <button
              onClick={() => setActiveFilter('overridden')}
              className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                activeFilter === 'overridden'
                  ? 'bg-emerald-600 text-white border-emerald-600'
                  : 'bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-50'
              }`}
            >
              Dérogés ({report?.resolved_count || 0})
            </button>
          </div>
        </div>

        {/* Findings Table */}
        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
              <tr>
                <th className="px-4 py-3">Niveau</th>
                <th className="px-4 py-3">Règle & Code</th>
                <th className="px-4 py-3">Élément affecté</th>
                <th className="px-4 py-3">Diagnostic Technique & Message</th>
                <th className="px-4 py-3">Recommandation</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {filteredFindings.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                    Aucune anomalie détectée pour ce filtre. L'infrastructure est conforme.
                  </td>
                </tr>
              ) : (
                filteredFindings.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      {f.is_overridden ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 w-max">
                          <ShieldCheck className="w-3 h-3" /> Dérogé
                        </span>
                      ) : f.severity === 'blocking' ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-red-50 text-red-700 border border-red-200 flex items-center gap-1 w-max">
                          <XCircle className="w-3 h-3" /> Bloquant
                        </span>
                      ) : f.severity === 'warning' ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1 w-max">
                          <AlertTriangle className="w-3 h-3" /> Avertissement
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1 w-max">
                          <Info className="w-3 h-3" /> Info
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      <div>{f.rule_title}</div>
                      <span className="text-[10px] font-mono text-slate-400 font-normal">{f.rule_code}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-700 font-medium">
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-600 uppercase mr-1.5 font-mono">
                        {f.target_type}
                      </span>
                      {f.target_name}
                    </td>
                    <td className="px-4 py-3 text-slate-700 max-w-sm">
                      <p>{f.message}</p>
                      {f.is_overridden && f.override_justification && (
                        <div className="mt-1.5 p-2 bg-emerald-50/70 border border-emerald-100 rounded text-[11px] text-emerald-800">
                          <span className="font-bold">Dérogation accordée : </span>
                          {f.override_justification}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-[11px] max-w-xs">
                      {f.recommendation}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {f.is_overridden ? (
                        <button
                          onClick={() => f.override_id && handleRevokeOverride(f.override_id)}
                          className="px-2.5 py-1 text-slate-500 hover:text-red-600 border border-slate-200 hover:border-red-200 rounded text-[11px] font-medium flex items-center gap-1 ml-auto"
                          title="Révoquer cette dérogation"
                        >
                          <Trash2 className="w-3 h-3" />
                          Révoquer
                        </button>
                      ) : (
                        <button
                          onClick={() => handleOpenOverrideModal(f)}
                          className="px-2.5 py-1 bg-white hover:bg-slate-50 text-blue-600 border border-blue-200 rounded text-[11px] font-semibold flex items-center gap-1 ml-auto shadow-2xs"
                        >
                          <FileCheck className="w-3 h-3" />
                          Déroger
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Override / Justification Modal */}
      {overrideFinding && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4 border border-slate-200 animate-in fade-in duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-blue-600" />
                <h3 className="text-sm font-bold text-slate-900">Dérogation Formelle & Justification</h3>
              </div>
              <button onClick={handleCloseOverrideModal} className="text-slate-400 hover:text-slate-600 text-sm">
                ✕
              </button>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
              <div className="font-bold text-slate-800">{overrideFinding.rule_title}</div>
              <div className="text-slate-600">Élément : <span className="font-semibold">{overrideFinding.target_name}</span></div>
              <div className="text-slate-500 text-[11px]">{overrideFinding.message}</div>
            </div>

            <form onSubmit={handleSubmitOverride} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Motif technique obligatoire de la dérogation (Section 8.3 & 6.8) :
                </label>
                <textarea
                  required
                  rows={4}
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="Ex. : Sous-réseau d'administration OOB physiquement isolé sur commutateurs dédiés non routés..."
                  className="w-full border border-slate-300 rounded-lg p-3 text-xs bg-white text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                />
                <div className="flex justify-between items-center text-[11px] text-slate-400 mt-1">
                  <span>Minimum 10 caractères requis</span>
                  <span>{justification.length} / 10 min</span>
                </div>
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900 space-y-1">
                <div className="font-bold flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-700" />
                  Traçabilité et responsabilité :
                </div>
                <p>
                  Toute dérogation est enregistrée nominativement dans l'audit trail et figurera dans l'annexe de conformité du document généré.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={handleCloseOverrideModal}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={submittingOverride || justification.trim().length < 10}
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
                >
                  {submittingOverride ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Enregistrement...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Valider la Dérogation
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
