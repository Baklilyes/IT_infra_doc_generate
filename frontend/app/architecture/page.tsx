'use client';

import React, { useState, useEffect } from 'react';
import {
  Network, Server, Share2, Download, RefreshCw, Layers,
  Maximize2, Eye, Shield, HardDrive, CheckCircle2, AlertCircle
} from 'lucide-react';
import { apiFetch, Project, DiagramResponse } from '@/lib/api';

export default function ArchitecturePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'physical' | 'logical' | 'flows'>('physical');
  const [diagram, setDiagram] = useState<DiagramResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadDiagram(activeTab);
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

  const loadDiagram = async (type: 'physical' | 'logical' | 'flows') => {
    if (!selectedProjectId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await apiFetch<DiagramResponse>(`/api/projects/${selectedProjectId}/diagrams/${type}`);
      setDiagram(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors de la génération du schéma.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadSvg = () => {
    if (!diagram || !diagram.svg) return;
    const blob = new Blob([diagram.svg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${diagram.diagram_type}_${selectedProjectId}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">Architecture &amp; Schémas d'Infrastructure</h1>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Lot 6 Actif
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Génération vectorielle SVG automatique et déterministe à partir des données d'inventaire réelles.
          </p>
        </div>

        {/* Project Selector & Export Actions */}
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
            onClick={() => loadDiagram(activeTab)}
            disabled={loading || !selectedProjectId}
            className="p-2 border border-slate-300 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-50"
            title="Actualiser le schéma"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleDownloadSvg}
            disabled={!diagram}
            className="px-3.5 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Exporter SVG</span>
          </button>
        </div>
      </div>

      {/* Diagram Type Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('physical')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'physical'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Server className="w-4 h-4" />
          Infrastructure Physique (Sites &amp; Baies)
        </button>
        <button
          onClick={() => setActiveTab('logical')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'logical'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Network className="w-4 h-4" />
          Topologie Réseau Logique (VLANs &amp; Routage)
        </button>
        <button
          onClick={() => setActiveTab('flows')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'flows'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Share2 className="w-4 h-4" />
          Matrice des Flux Applicatifs
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-xs text-red-700">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* SVG Canvas Container */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Canvas Toolbar */}
        <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-600">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-800">{diagram?.title || 'Schéma'}</span>
            <span className="text-slate-300">|</span>
            <span className="text-[11px] text-slate-500 font-mono">Format vectoriel SVG natif</span>
            <span className="text-slate-300">|</span>
            <span className="text-[11px] text-slate-500">{diagram?.elements_count || 0} entités représentées</span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span>Intégrable dans Word (DOCX) &amp; PDF</span>
          </div>
        </div>

        {/* Canvas Viewer */}
        <div className="p-6 overflow-auto max-h-[750px] bg-slate-50/50 flex justify-center items-center min-h-[500px]">
          {loading ? (
            <div className="text-center py-12 space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto" />
              <p className="text-xs font-semibold text-slate-700">Génération du schéma vectoriel en cours...</p>
              <p className="text-[11px] text-slate-400">Calcul du positionnement automatique des équipements et liaisons</p>
            </div>
          ) : diagram?.svg ? (
            <div
              className="w-full max-w-5xl shadow-sm rounded-lg overflow-hidden border border-slate-200 bg-white"
              dangerouslySetInnerHTML={{ __html: diagram.svg }}
            />
          ) : (
            <div className="text-center py-12 text-slate-400">
              <Network className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-xs">Aucune donnée disponible pour générer ce schéma.</p>
            </div>
          )}
        </div>
      </div>

      {/* Explanatory Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
            <Server className="w-4 h-4 text-blue-600" />
            Schéma Physique
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Représente l'implantation géographique par site, les baies 19 pouces, les matériels actifs/passifs et le câblage principal (cuivre, fibre optique OM4).
          </p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
            <Network className="w-4 h-4 text-indigo-600" />
            Topologie Logique
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Illustre la segmentation 802.1Q (VLANs), les sous-réseaux CIDR, les passerelles de routage par défaut et l'appartenance des hôtes aux zones.
          </p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
            <Shield className="w-4 h-4 text-emerald-600" />
            Matrice des Flux
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Détaille les règles de filtrage de sécurité inter-zones, les protocoles (TCP/UDP), les ports autorisés et la politique de pare-feu implicite "Deny All".
          </p>
        </div>
      </div>
    </div>
  );
}
