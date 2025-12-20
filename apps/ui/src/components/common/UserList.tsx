
import React, { useEffect, useState } from 'react';
import { Button } from '@agentic/ui-lib';
import { useGetApi, usePostApi } from '@/hooks/useApi';

export interface User {
  user_id: string;
  name: string;
  email: string;
}

export const UserList: React.FC = () => {
  const { data: users, loading, error, refetch } = useGetApi<User[]>("/users");
  const { loading: postLoading, error: postError, post } = usePostApi<User>("/users");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ user_id: '', name: '', email: '' });
  const [formError, setFormError] = useState<string | null>(null);

  // Watch for error changes and show message
  useEffect(() => {
    if (error) {
      setFormError(error instanceof Error ? error.message : String(error));
    } else if (postError) {
      setFormError(postError instanceof Error ? postError.message : String(postError));
    }
  }, [error, postError]);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      await post(form);
      setForm({ user_id: '', name: '', email: '' });
      setShowForm(false);
      await refetch();
    } catch (e: any) {
      setFormError(e.message || "Failed to add user");
    }
  };

  return (
    <section className="mt-8">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-semibold">Users</h2>
        <Button variant="primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancel' : 'Add User'}
        </Button>
      </div>
      {showForm && (
        <form className="mb-4 flex gap-2 flex-wrap" onSubmit={handleAddUser}>
          <input
            className="border rounded px-2 py-1"
            placeholder="User ID"
            value={form.user_id}
            onChange={e => setForm(f => ({ ...f, user_id: e.target.value }))}
            required
          />
          <input
            className="border rounded px-2 py-1"
            placeholder="Name"
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            required
          />
          <input
            className="border rounded px-2 py-1"
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            required
          />
          <Button type="submit" variant="success">Save</Button>
        </form>
      )}
      {formError && <div className="text-red-600">{formError}</div>}
      {(loading || postLoading) ? (
        <div>Loading users...</div>
      ) : error ? (
        <div className="text-red-600">{error.message}</div>
      ) : (
        <table className="min-w-full border mt-2">
          <thead>
            <tr className="bg-gray-200">
              <th className="px-2 py-1 border">User ID</th>
              <th className="px-2 py-1 border">Name</th>
              <th className="px-2 py-1 border">Email</th>
            </tr>
          </thead>
          <tbody>
            {(users || []).map((u) => (
              <tr key={u.user_id} className="odd:bg-gray-50">
                <td className="px-2 py-1 border">{u.user_id}</td>
                <td className="px-2 py-1 border">{u.name}</td>
                <td className="px-2 py-1 border">{u.email}</td>
              </tr>
            ))}
            {(!users || users.length === 0) && (
              <tr>
                <td colSpan={3} className="text-center py-2">No users found.</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
};
