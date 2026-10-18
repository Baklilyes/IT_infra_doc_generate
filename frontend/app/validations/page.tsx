'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ShieldAlert, ShieldCheck, AlertTriangle, XCircle, Info,
  RefreshCw, CheckCircle2, Lock, Unlock, ArrowRight, ExternalLink,
  MessageSquare, Trash2, Filter, Layers, FileCheck, GitBranch,
  UserCheck, Send, CheckSquare, Clock, AlertCircle, History
} from 'lucide-react';
import {
  apiFetch, Project, ConsistencyReport, Finding, CanPublishResponse,
  WorkflowStatusResponse, WorkflowDecision
} from '@/lib/api';

export default function ValidationsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'checks' | 'workflow'>('checks');

  // Consistency checks state
  const [report, setReport] = useState<ConsistencyReport | null>(null);
  const [canPublish, setCanPublish] = useState<CanPublishResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [runningChecks, setRunningChecks] = useState<boolean>(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'blocking' | 'warning' | 'info' | 'overridden'>('all');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Override Modal state
  const [overrideFinding, setOverrideFinding] = useState<Finding | null>(null);
  const [justification, setJustification] = useState<string>('');
  const [submittingOverride, setSubmittingOverride] = useState<boolean>(false);

  // Workflow state
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatusResponse | null>(null);
  const [workflowHistory, setWorkflowHistory] = useState<WorkflowDecision[]>([]);
  const [workflowLoading, setWorkflowLoading] = useState<boolean>(false);
  const [actionComment, setActionComment] = useState<string>('');
  const [submittingWorkflow, setSubmittingWorkflow] = useState<boolean>(false);

  // Rejection Modal state
  const [rejectModalOpen, setRejectModalOpen] = useState<boolean>(false);
  const [rejectStage, setRejectStage] = useState<'tech' | 'final'>('tech');
  const [rejectMotive, setRejectMotive] = useState<string>('');

  // Branch Version Modal state
  const [branchModalOpen, setBranchModalOpen] = useState<boolean>(false);
  const [branchBump, setBranchBump] = useState<'minor' | 'major'>('minor');
  const [customVersion, setCustomVersion] = useState<string>('');
  const [branchComment, setBranchComment] = useState<string>('');

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadValidationReport();
      loadWorkflowData();
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

  const loadWorkflowData = async () => {
    if (!selectedProjectId) return;
    setWorkflowLoading(true);
    try {
      const [statusData, historyData] = await Promise.all([
        apiFetch<WorkflowStatusResponse>(`/api/projects/${selectedProjectId}/workflow`),
        apiFetch<WorkflowDecision[]>(`/api/projects/${selectedProjectId}/workflow/history`),
      ]);
      setWorkflowStatus(statusData);
      setWorkflowHistory(historyData);
    } catch (err: any) {
      console.error('Erreur chargement workflow:', err);
    } finally {
      setWorkflowLoading(false);
    }
  };

  const runChecks = async () => {
    if (!selectedProjectId) return;
    setRunningChecks(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const [repData, pubData] = await Promise.all([
        apiFetch<ConsistencyReport>(`/api/projects/${selectedProjectId}/validations/run`, { method: 'POST' }),
        apiFetch<CanPublishResponse>(`/api/projects/${selectedProjectId}/validations/can-publish`),
      ]);
      setReport(repData);
      setCanPublish(pubData);
      await loadWorkflowData();
      setSuccessMsg('Contrôles de cohérence exécutés avec succès.');
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
      setSuccessMsg('Dérogation formelle enregistrée et auditée.');
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la validation de la dérogation.');
    } finally {
      setSubmittingOverride(false);
    }
  };

  const handleDeleteOverride = async (overrideId: string) => {
    if (!selectedProjectId) return;
    if (!confirm('Êtes-vous sûr de vouloir révoquer cette dérogation ? Le contrôle redeviendra actif.')) return;

    try {
      await apiFetch(`/api/projects/${selectedProjectId}/validations/override/${overrideId}`, {
        method: 'DELETE',
      });
      await runChecks();
      setSuccessMsg('Dérogation révoquée.');
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la suppression de la dérogation.');
    }
  };

  // Workflow Handlers
  const handleWorkflowSubmit = async () => {
    if (!selectedProjectId) return;
    setSubmittingWorkflow(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await apiFetch(`/api/projects/${selectedProjectId}/workflow/submit`, {
        method: 'POST',
        body: JSON.stringify({ comment: actionComment.trim() || undefined })
      });
      setActionComment('');
      setSuccessMsg('Dossier soumis pour revue technique avec succès.');
      await loadWorkflowData();
      await loadProjects();
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la soumission du dossier.');
    } finally {
      setSubmittingWorkflow(false);
    }
  };

  const handleTechApprove = async () => {
    if (!selectedProjectId) return;
    setSubmittingWorkflow(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await apiFetch(`/api/projects/${selectedProjectId}/workflow/tech-approve`, {
        method: 'POST',
        body: JSON.stringify({ comment: actionComment.trim() || undefined })
      });
      setActionComment('');
      setSuccessMsg('Revue technique validée avec succès. Dossier en attente de validation finale.');
      await loadWorkflowData();
      await loadProjects();
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la validation technique.');
    } finally {
      setSubmittingWorkflow(false);
    }
  };

  const handleFinalApprove = async () => {
    if (!selectedProjectId) return;
    setSubmittingWorkflow(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await apiFetch(`/api/projects/${selectedProjectId}/workflow/final-approve`, {
        method: 'POST',
        body: JSON.stringify({ comment: actionComment.trim() || undefined })
      });
      setActionComment('');
      setSuccessMsg('Validation finale accordée. Le projet est désormais scellé et verrouillé.');
      await loadWorkflowData();
      await loadProjects();
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la validation finale.');
    } finally {
      setSubmittingWorkflow(false);
    }
  };

  const handleOpenRejectModal = (stage: 'tech' | 'final') => {
    setRejectStage(stage);
    setRejectMotive('');
    setRejectModalOpen(true);
    setErrorMsg(null);
  };

  const handleSubmitRejection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || rejectMotive.trim().length < 5) {
      setErrorMsg('Le motif de renvoi pour correction doit comporter au moins 5 caractères.');
      return;
    }
    setSubmittingWorkflow(true);
    setErrorMsg(null);
    try {
      const endpoint = rejectStage === 'tech'
        ? `/api/projects/${selectedProjectId}/workflow/tech-reject`
        : `/api/projects/${selectedProjectId}/workflow/final-reject`;

      await apiFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({ comment: rejectMotive.trim() })
      });
      setRejectModalOpen(false);
      setRejectMotive('');
      setSuccessMsg('Dossier renvoyé pour correction avec motif consigné.');
      await loadWorkflowData();
      await loadProjects();
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors du renvoi pour correction.');
    } finally {
      setSubmittingWorkflow(false);
    }
  };

  const handleOpenBranchModal = () => {
    setBranchBump('minor');
    setCustomVersion('');
    setBranchComment('');
    setBranchModalOpen(true);
    setErrorMsg(null);
  };

  const handleSubmitBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;
    setSubmittingWorkflow(true);
    setErrorMsg(null);
    try {
      const res = await apiFetch<Project>(`/api/projects/${selectedProjectId}/workflow/branch-version`, {
        method: 'POST',
        body: JSON.stringify({
          version_bump: branchBump,
          new_version: customVersion.trim() || undefined,
          comment: branchComment.trim() || undefined
        })
      });
      setBranchModalOpen(false);
      setSuccessMsg(`Nouvelle version ${res.version} créée avec succès (${res.reference}).`);
      await loadProjects();
      setSelectedProjectId(res.id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors du branchement de version.');
    } finally {
      setSubmittingWorkflow(false);
    }
  };

  const currentProject = projects.find(p => p.id === selectedProjectId);

  const filteredFindings = report?.findings ? report.findings.filter(f => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'overridden') return f.is_overridden;
    if (activeFilter === 'blocking') return f.severity === 'blocking' && !f.is_overridden;
    if (activeFilter === 'warning') return f.severity === 'warning' && !f.is_overridden;
    if (activeFilter === 'info') return f.severity === 'info' && !f.is_overridden;
    return true;
  }) : [];

  return (
    <div className="space-y-6">
      {/* Top Header & Project Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-blue-600" />
            Contrôles, Validation & Approbation
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Vérifications d'intégrité déterministes, dérogations formelles et circuit de validation strict.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white px-3 py-1.5 border border-slate-200 rounded-lg shadow-xs">
            <span className="text-xs font-semibold text-slate-500">Projet :</span>
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="text-xs font-medium text-slate-800 bg-transparent focus:outline-hidden cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.reference} — {p.name} (v{p.version || '1.0'}) [{p.status}]
                </option>
              ))}
            </select>
          </div>

          {activeTab === 'checks' && (
            <button
              onClick={runChecks}
              disabled={runningChecks || !selectedProjectId}
              className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium flex items-center gap-2 shadow-xs transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${runningChecks ? 'animate-spin' : ''}`} />
              <span>{runningChecks ? 'Vérification...' : 'Lancer les contrôles'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start justify-between">
          <div className="flex items-center gap-2">
            <XCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-red-500 hover:text-red-700 font-bold ml-2">✕</button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-start justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-500 hover:text-emerald-700 font-bold ml-2">✕</button>
        </div>
      )}

      {/* Main Tab Navigation */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('checks')}
          className={`pb-3 px-4 text-xs font-bold transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'checks'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Contrôles de Cohérence & Dérogations</span>
          {report && (
            <span className={`px-2 py-0.5 rounded-full text-[10px] ${
              report.blocking_count > 0 ? 'bg-red-100 text-red-700 font-bold' : 'bg-slate-100 text-slate-600'
            }`}>
              {report.blocking_count + report.warning_count}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('workflow')}
          className={`pb-3 px-4 text-xs font-bold transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === 'workflow'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <GitBranch className="w-4 h-4" />
          <span>Circuit d'Approbation & Verrouillage (Workflow)</span>
          {workflowStatus && (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              workflowStatus.is_locked
                ? 'bg-emerald-100 text-emerald-800'
                : workflowStatus.status === 'in_review'
                ? 'bg-amber-100 text-amber-800'
                : 'bg-slate-100 text-slate-700'
            }`}>
              {workflowStatus.status}
            </span>
          )}
        </button>
      </div>

      {/* ========================================================= */}
      {/* TAB 1: CONSISTENCY CHECKS & FORMAL OVERRIDES               */}
      {/* ========================================================= */}
      {activeTab === 'checks' && (
        <div className="space-y-6">
          {/* Gatekeeper Banner */}
          {canPublish && (
            <div className={`p-4 rounded-xl border flex items-center justify-between shadow-xs transition-all ${
              canPublish.can_publish
                ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                : 'bg-red-50/80 border-red-200 text-red-900'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-xl ${canPublish.can_publish ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                  {canPublish.can_publish ? <ShieldCheck className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
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
                <button
                  onClick={() => setActiveTab('workflow')}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
                >
                  <span>Passer au Workflow</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
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

          {/* Filtering Bar */}
          <div className="flex items-center justify-between bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400 ml-1" />
              <span className="text-xs font-semibold text-slate-600 mr-2">Filtrer par sévérité :</span>
              <div className="flex gap-1.5">
                {(['all', 'blocking', 'warning', 'info', 'overridden'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setActiveFilter(filter)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                      activeFilter === filter
                        ? 'bg-slate-900 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {filter === 'all' && 'Tous les constats'}
                    {filter === 'blocking' && `Bloquants (${report?.blocking_count || 0})`}
                    {filter === 'warning' && `Avertissements (${report?.warning_count || 0})`}
                    {filter === 'info' && `Infos (${report?.info_count || 0})`}
                    {filter === 'overridden' && `Dérogés (${report?.resolved_count || 0})`}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Findings List */}
          {filteredFindings.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-900">Aucune anomalie détectée dans ce filtre</h3>
              <p className="text-xs text-slate-500 mt-1">
                Toutes les règles déterministes d'intégrité sont respectées pour cette sélection.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredFindings.map((f, idx) => (
                <div
                  key={`${f.rule_code}-${f.target_id}-${idx}`}
                  className={`p-4 rounded-xl border bg-white shadow-xs transition-all ${
                    f.is_overridden
                      ? 'border-emerald-200 bg-emerald-50/30'
                      : f.severity === 'blocking'
                      ? 'border-red-200 hover:border-red-300'
                      : f.severity === 'warning'
                      ? 'border-amber-200 hover:border-amber-300'
                      : 'border-blue-200'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">
                        {f.is_overridden ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                        ) : f.severity === 'blocking' ? (
                          <XCircle className="w-5 h-5 text-red-500" />
                        ) : f.severity === 'warning' ? (
                          <AlertTriangle className="w-5 h-5 text-amber-500" />
                        ) : (
                          <Info className="w-5 h-5 text-blue-500" />
                        )}
                      </div>

                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            f.severity === 'blocking'
                              ? 'bg-red-100 text-red-800'
                              : f.severity === 'warning'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}>
                            {f.severity}
                          </span>
                          <span className="text-xs font-mono text-slate-400">{f.rule_code}</span>
                          <span className="text-xs font-bold text-slate-900">{f.rule_title}</span>
                        </div>

                        <p className="text-xs text-slate-700 font-medium">{f.message}</p>

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500 pt-0.5">
                          <span>Cible : <strong className="text-slate-800">{f.target_name}</strong> ({f.target_type})</span>
                          <span>Recommandation : <em className="text-slate-600">{f.recommendation}</em></span>
                        </div>

                        {/* Overridden Badge & Justification */}
                        {f.is_overridden && (
                          <div className="mt-2.5 p-2.5 bg-emerald-100/60 border border-emerald-200 rounded-lg text-xs text-emerald-950 space-y-1">
                            <div className="flex items-center justify-between font-semibold">
                              <span className="flex items-center gap-1.5">
                                <FileCheck className="w-3.5 h-3.5 text-emerald-700" />
                                Dérogation formelle accordée
                              </span>
                            </div>
                            {f.override_justification && (
                              <p className="text-[11px] italic bg-white/70 p-2 rounded border border-emerald-200">
                                « {f.override_justification} »
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                      {!f.is_overridden ? (
                        <button
                          onClick={() => handleOpenOverrideModal(f)}
                          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                        >
                          <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
                          <span>Déroger</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => f.override_id && handleDeleteOverride(f.override_id)}
                          title="Révoquer cette dérogation"
                          className="px-2.5 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-xs font-medium flex items-center gap-1 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Révoquer</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: WORKFLOW DE VALIDATION, SOD & VEROUILLAGE          */}
      {/* ========================================================= */}
      {activeTab === 'workflow' && workflowStatus && (
        <div className="space-y-6">
          {/* Lifecycle Stepper */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-6">
              Circuit de Validation Strict (Section 6.14)
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
              {/* Step 1: Brouillon */}
              <div className={`p-4 rounded-xl border flex flex-col justify-between ${
                workflowStatus.status === 'draft' || workflowStatus.status === 'in_preparation'
                  ? 'bg-blue-50/70 border-blue-400 ring-2 ring-blue-500/20'
                  : 'bg-slate-50 border-slate-200'
              }`}>
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-500 mb-2">
                    <span>1. PRÉPARATION</span>
                    <span className="text-[10px] bg-slate-200 px-1.5 py-0.5 rounded text-slate-700">Ingénieur</span>
                  </div>
                  <p className="text-xs text-slate-700 font-medium">Saisie des données et résolution des erreurs bloquantes.</p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center gap-1.5 text-[11px] font-bold text-slate-600">
                  {workflowStatus.status === 'draft' || workflowStatus.status === 'in_preparation' ? (
                    <Clock className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
                  ) : (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  )}
                  <span>Statut : Brouillon</span>
                </div>
              </div>

              {/* Step 2: En Revue */}
              <div className={`p-4 rounded-xl border flex flex-col justify-between ${
                workflowStatus.status === 'in_review'
                  ? 'bg-amber-50/70 border-amber-400 ring-2 ring-amber-500/20'
                  : 'bg-slate-50 border-slate-200'
              }`}>
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-500 mb-2">
                    <span>2. REVUE TECHNIQUE</span>
                    <span className="text-[10px] bg-amber-100 px-1.5 py-0.5 rounded text-amber-800 font-bold">Tech Lead</span>
                  </div>
                  <p className="text-xs text-slate-700 font-medium">Contrôle de l'architecture, VLANs, sécurité et IP.</p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center gap-1.5 text-[11px] font-bold text-slate-600">
                  {workflowStatus.status === 'in_review' ? (
                    <Clock className="w-3.5 h-3.5 text-amber-600 animate-pulse" />
                  ) : workflowStatus.status === 'validated' || workflowStatus.status === 'closed' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <span className="text-slate-400">En attente</span>
                  )}
                  <span>En Revue</span>
                </div>
              </div>

              {/* Step 3: Validé */}
              <div className={`p-4 rounded-xl border flex flex-col justify-between ${
                workflowStatus.status === 'validated'
                  ? 'bg-indigo-50/70 border-indigo-400 ring-2 ring-indigo-500/20'
                  : 'bg-slate-50 border-slate-200'
              }`}>
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-500 mb-2">
                    <span>3. VALIDATION FINALE</span>
                    <span className="text-[10px] bg-indigo-100 px-1.5 py-0.5 rounded text-indigo-800 font-bold">Validateur Final</span>
                  </div>
                  <p className="text-xs text-slate-700 font-medium">Approbation formelle du dossier complet pour livraison.</p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center gap-1.5 text-[11px] font-bold text-slate-600">
                  {workflowStatus.status === 'validated' ? (
                    <Clock className="w-3.5 h-3.5 text-indigo-600 animate-pulse" />
                  ) : workflowStatus.status === 'closed' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <span className="text-slate-400">En attente</span>
                  )}
                  <span>Validé</span>
                </div>
              </div>

              {/* Step 4: Scellé / Clôturé */}
              <div className={`p-4 rounded-xl border flex flex-col justify-between ${
                workflowStatus.is_locked
                  ? 'bg-emerald-50/80 border-emerald-400 ring-2 ring-emerald-500/20'
                  : 'bg-slate-50 border-slate-200'
              }`}>
                <div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-500 mb-2">
                    <span>4. VERROUILLÉ & SCELLÉ</span>
                    <span className="text-[10px] bg-emerald-100 px-1.5 py-0.5 rounded text-emerald-800 font-bold">Immuable</span>
                  </div>
                  <p className="text-xs text-slate-700 font-medium">Version publiée immuable. Modifications interdites.</p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center gap-1.5 text-[11px] font-bold text-slate-600">
                  {workflowStatus.is_locked ? (
                    <Lock className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Unlock className="w-3.5 h-3.5 text-slate-400" />
                  )}
                  <span>{workflowStatus.is_locked ? 'Scellé' : 'Non scellé'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Project Lock & Immutability Banner */}
          {workflowStatus.is_locked ? (
            <div className="p-5 bg-emerald-50 border border-emerald-200 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xs">
              <div className="flex items-center gap-3.5">
                <div className="p-3 bg-emerald-600 text-white rounded-xl shadow-xs">
                  <Lock className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-900">
                      Version Scellée et Clôturée (v{workflowStatus.version})
                    </span>
                    <span className="px-2 py-0.5 bg-emerald-200 text-emerald-800 text-[10px] font-bold rounded">
                      IMMUABLE
                    </span>
                  </div>
                  <p className="text-xs text-emerald-800 mt-1">
                    Ce dossier a reçu toutes les approbations requises. Les équipements, adresses IP et schémas sont définitivement verrouillés pour cette version.
                  </p>
                </div>
              </div>

              <button
                onClick={handleOpenBranchModal}
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xs transition-colors shrink-0"
              >
                <GitBranch className="w-4 h-4" />
                <span>Créer une nouvelle version de travail</span>
              </button>
            </div>
          ) : (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-slate-200 text-slate-700 rounded-xl">
                  <Unlock className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-900">Version de travail active : v{workflowStatus.version}</span>
                    <span className="px-2 py-0.5 bg-slate-200 text-slate-800 text-[10px] font-bold rounded uppercase">
                      {workflowStatus.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Toute modification après soumission réinitialise automatiquement le statut en Brouillon pour garantir l'intégrité.
                  </p>
                </div>
              </div>

              {workflowStatus.can_publish ? (
                <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold bg-emerald-100 px-3 py-1.5 rounded-lg">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Prêt pour soumission</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-xs text-red-700 font-semibold bg-red-100 px-3 py-1.5 rounded-lg">
                  <ShieldAlert className="w-4 h-4" />
                  <span>{workflowStatus.blocking_issues_count} erreur(s) bloquante(s)</span>
                </div>
              )}
            </div>
          )}

          {/* Action Decision Panel */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
            <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-blue-600" />
              Actions Disponibles sur cette Étape
            </h4>

            {/* Comment input for workflow transition */}
            {!workflowStatus.is_locked && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Commentaire ou note d'accompagnement (optionnel) :
                </label>
                <input
                  type="text"
                  value={actionComment}
                  onChange={(e) => setActionComment(e.target.value)}
                  placeholder="Ex. : Mise à jour du plan d'adressage WAN conformément au PV de réunion..."
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            {/* Action Buttons according to allowed_actions */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              {workflowStatus.allowed_actions.includes('submit') && (
                <button
                  onClick={handleWorkflowSubmit}
                  disabled={submittingWorkflow || !workflowStatus.can_publish}
                  className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xs transition-colors disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                  <span>Soumettre pour Revue Technique</span>
                </button>
              )}

              {workflowStatus.allowed_actions.includes('tech_approve') && (
                <button
                  onClick={handleTechApprove}
                  disabled={submittingWorkflow}
                  className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xs transition-colors"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Approuver la Revue Technique</span>
                </button>
              )}

              {workflowStatus.allowed_actions.includes('tech_reject') && (
                <button
                  onClick={() => handleOpenRejectModal('tech')}
                  disabled={submittingWorkflow}
                  className="px-4 py-2.5 bg-red-100 hover:bg-red-200 text-red-700 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Renvoyer pour Correction (Rejet Technique)</span>
                </button>
              )}

              {workflowStatus.allowed_actions.includes('final_approve') && (
                <button
                  onClick={handleFinalApprove}
                  disabled={submittingWorkflow}
                  className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xs transition-colors"
                >
                  <Lock className="w-4 h-4" />
                  <span>Valider Définitivement & Sceller le Projet</span>
                </button>
              )}

              {workflowStatus.allowed_actions.includes('final_reject') && (
                <button
                  onClick={() => handleOpenRejectModal('final')}
                  disabled={submittingWorkflow}
                  className="px-4 py-2.5 bg-red-100 hover:bg-red-200 text-red-700 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Renvoyer pour Correction (Rejet Final)</span>
                </button>
              )}

              {workflowStatus.is_locked && (
                <button
                  onClick={handleOpenBranchModal}
                  className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-xs transition-colors"
                >
                  <GitBranch className="w-4 h-4 text-emerald-400" />
                  <span>Créer une nouvelle version de travail</span>
                </button>
              )}

              {workflowStatus.allowed_actions.length === 0 && !workflowStatus.is_locked && (
                <p className="text-xs text-slate-500 italic">
                  Aucune action disponible pour votre rôle utilisateur sur cette étape.
                </p>
              )}
            </div>
          </div>

          {/* Audit Trail & Decision History */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
            <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <History className="w-4 h-4 text-slate-600" />
              Journal d'Audit et Historique des Décisions (Section 6.14)
            </h4>

            {workflowHistory.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-4">Aucune décision consignée pour ce projet.</p>
            ) : (
              <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-200">
                {workflowHistory.map((d) => (
                  <div key={d.id} className="relative flex items-start gap-3 pl-8">
                    <div className="absolute left-2 top-2 w-3.5 h-3.5 rounded-full bg-white border-2 border-blue-600" />
                    <div className="p-3.5 bg-slate-50/70 border border-slate-200 rounded-xl text-xs w-full space-y-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            d.action.includes('approve')
                              ? 'bg-emerald-100 text-emerald-800'
                              : d.action.includes('reject')
                              ? 'bg-red-100 text-red-800'
                              : d.action === 'branch_version'
                              ? 'bg-purple-100 text-purple-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}>
                            {d.action}
                          </span>
                          <span className="font-bold text-slate-800">
                            {d.from_status} ➔ {d.to_status}
                          </span>
                          <span className="text-[10px] bg-slate-200 px-1.5 py-0.5 rounded text-slate-700">
                            v{d.version}
                          </span>
                        </div>

                        <span className="text-[11px] text-slate-400">
                          {new Date(d.created_at).toLocaleString('fr-FR')} (UTC)
                        </span>
                      </div>

                      <div className="text-slate-600 font-medium">
                        Par : <strong className="text-slate-900">{d.user_name || 'Système'}</strong> ({d.user_role || 'audit'})
                      </div>

                      {d.comment && (
                        <p className="text-[11px] text-slate-700 italic bg-white p-2 rounded border border-slate-200 mt-1">
                          « {d.comment} »
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Rejet avec motif obligatoire */}
      {rejectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-red-600 font-bold text-sm">
                <XCircle className="w-5 h-5" />
                Renvoi pour Correction — Motif Obligatoire
              </div>
              <button onClick={() => setRejectModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
            </div>

            <p className="text-xs text-slate-600">
              Conformément à la Section 6.14, tout rejet doit comporter un motif technique explicite et argumenté. Le projet reviendra au statut <strong>Brouillon</strong> pour modification par l'ingénieur.
            </p>

            <form onSubmit={handleSubmitRejection} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Motif détaillé du renvoi :
                </label>
                <textarea
                  required
                  rows={4}
                  value={rejectMotive}
                  onChange={(e) => setRejectMotive(e.target.value)}
                  placeholder="Ex. : Le sous-réseau 10.10.10.0/24 chevauche le VLAN DMZ existant. Merci d'ajuster le masque CIDR..."
                  className="w-full border border-slate-300 rounded-lg p-3 text-xs bg-white text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-red-500"
                />
                <div className="flex justify-between items-center text-[11px] text-slate-400 mt-1">
                  <span>Minimum 5 caractères requis</span>
                  <span>{rejectMotive.length} / 5 min</span>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setRejectModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={submittingWorkflow || rejectMotive.trim().length < 5}
                  className="px-5 py-2 bg-red-600 text-white rounded-lg text-xs font-semibold hover:bg-red-700 disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
                >
                  <span>Confirmer le Renvoi</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Création de nouvelle version (Branch) */}
      {branchModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
                <GitBranch className="w-5 h-5 text-emerald-600" />
                Créer une Nouvelle Version de Travail
              </div>
              <button onClick={() => setBranchModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
            </div>

            <p className="text-xs text-slate-600">
              Un clone profond sera généré avec un état <strong>Brouillon</strong> (sites, équipements, VLANs, interfaces). La version actuelle restera <strong>scellée et immuable</strong>.
            </p>

            <form onSubmit={handleSubmitBranch} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Type d'incrémentation :</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setBranchBump('minor')}
                    className={`p-3 rounded-lg border text-xs font-bold text-left transition-all ${
                      branchBump === 'minor'
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-900 ring-2 ring-emerald-500/20'
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    Version Mineure
                    <span className="block text-[11px] font-normal text-slate-500 mt-0.5">Ex : 1.0 ➔ 1.1</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setBranchBump('major')}
                    className={`p-3 rounded-lg border text-xs font-bold text-left transition-all ${
                      branchBump === 'major'
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-900 ring-2 ring-emerald-500/20'
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    Version Majeure
                    <span className="block text-[11px] font-normal text-slate-500 mt-0.5">Ex : 1.0 ➔ 2.0</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Numéro de version personnalisé (optionnel) :
                </label>
                <input
                  type="text"
                  value={customVersion}
                  onChange={(e) => setCustomVersion(e.target.value)}
                  placeholder="Laisser vide pour auto-incrémentation"
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Objectifs / Notes pour cette nouvelle version :
                </label>
                <textarea
                  rows={3}
                  value={branchComment}
                  onChange={(e) => setBranchComment(e.target.value)}
                  placeholder="Ex. : Phase 2 d'extension du datacenter secondaire et ajout des liaisons DWDM..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setBranchModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={submittingWorkflow}
                  className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
                >
                  <span>Créer la Version de Travail</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Formulaire de Dérogation */}
      {overrideFinding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
                <ShieldAlert className="w-5 h-5 text-amber-500" />
                Accorder une Dérogation Formelle
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
