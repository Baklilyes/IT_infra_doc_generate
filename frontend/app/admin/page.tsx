'use client';

import React, { useState, useEffect } from 'react';
import { useTranslation } from '@/i18n/LanguageContext';
import { useAuth } from '@/lib/auth-context';
import { apiFetch, User } from '@/lib/api';
import { Users, Plus, Shield, Check, X, AlertCircle } from 'lucide-react';

export default function AdminPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New user form modal state
  const [showModal, setShowModal] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newRole, setNewRole] = useState<'engineer' | 'technical_lead' | 'final_validator' | 'administrator'>('engineer');
  const [newPassword, setNewPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const data = await apiFetch<User[]>('/api/auth/users');
      setUsers(data);
    } catch (err: any) {
      setError(err.message || 'Erreur de chargement des utilisateurs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'administrator') {
      fetchUsers();
    }
  }, [user]);

  if (user?.role !== 'administrator') {
    return (
      <div className="p-8 bg-red-50 border border-red-200 rounded-xl text-red-700 text-center">
        <Shield className="w-10 h-10 mx-auto text-red-500 mb-2" />
        <h2 className="text-base font-bold">Accès Refusé</h2>
        <p className="text-xs mt-1">Cette section est strictement réservée au rôle Administrateur.</p>
      </div>
    );
  }

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      await apiFetch<User>('/api/auth/users', {
        method: 'POST',
        body: JSON.stringify({
          username: newUsername,
          email: newEmail,
          full_name: newFullName,
          role: newRole,
          password: newPassword,
        }),
      });
      setShowModal(false);
      setNewUsername('');
      setNewEmail('');
      setNewFullName('');
      setNewPassword('');
      fetchUsers();
    } catch (err: any) {
      setFormError(err.message || 'Erreur lors de la création');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t('nav.admin')}</h1>
          <p className="text-xs text-slate-500">Gestion des comptes utilisateurs et des rôles d'accès</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 transition"
        >
          <Plus className="w-4 h-4" />
          <span>Nouvel utilisateur</span>
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
            <Users className="w-4 h-4 text-blue-600" />
            <span>Comptes Actifs & Habilités</span>
          </h2>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Chargement des comptes...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-4 py-3">Utilisateur</th>
                  <th className="px-4 py-3">Nom complet</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Rôle</th>
                  <th className="px-4 py-3">Statut</th>
                  <th className="px-4 py-3">Création</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50 transition">
                    <td className="px-4 py-3 font-semibold text-slate-900 font-mono">
                      {u.username}
                    </td>
                    <td className="px-4 py-3">{u.full_name}</td>
                    <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">{u.email}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold border bg-slate-100 text-slate-800 border-slate-200">
                        {t(`roles.${u.role}`)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {u.is_active ? (
                        <span className="inline-flex items-center text-emerald-700 font-medium text-[11px]">
                          <Check className="w-3.5 h-3.5 mr-1" /> Actif
                        </span>
                      ) : (
                        <span className="inline-flex items-center text-rose-700 font-medium text-[11px]">
                          <X className="w-3.5 h-3.5 mr-1" /> Désactivé
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-[11px]">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal create user */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Créer un compte utilisateur</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Nom d'utilisateur</label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Nom complet</label>
                <input
                  type="text"
                  required
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Rôle</label>
                <select
                  value={newRole}
                  onChange={(e: any) => setNewRole(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                >
                  <option value="engineer">{t('roles.engineer')}</option>
                  <option value="technical_lead">{t('roles.technical_lead')}</option>
                  <option value="final_validator">{t('roles.final_validator')}</option>
                  <option value="administrator">{t('roles.administrator')}</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Mot de passe temporaire</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-hidden focus:ring-1 focus:ring-blue-500"
                  placeholder="Min. 8 caractères"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
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
