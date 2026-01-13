
import React, { useEffect, useState } from 'react';
import { Button } from '@agentic/ui-lib';
import { useGetApi, usePostApi } from '@/hooks/useApi';
import { User } from '@agentic/ui-lib';

interface UserListResponse {
  users: Array<{
    userId: string;
    firstName: string;
    lastName: string;
    emailAddress: string;
    phoneNumber?: string;
    accountStatus: "active" | "inactive" | "suspended";
  }>;
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
}

interface CreateUserCommand {
  firstName: string;
  lastName: string;
  emailAddress: string;
  phoneNumber?: string;
}

export const UserList: React.FC = () => {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  
  // Construct URL with query parameters
  const userListUrl = `/users?page=${page}&page_size=${pageSize}`;
  
  const { data: response, loading, error, refetch } = useGetApi<UserListResponse>(userListUrl);
  const { loading: postLoading, error: postError, post } = usePostApi<UserListResponse["users"][0], CreateUserCommand>("/users");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateUserCommand>({ firstName: '', lastName: '', emailAddress: '' });
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
      setForm({ firstName: '', lastName: '', emailAddress: '' });
      setShowForm(false);
      await refetch();
    } catch (e: any) {
      setFormError(e.message || "Failed to add user");
    }
  };

  const users = response?.users || [];
  const totalPages = response?.totalPages || 1;

  return (
    <section className="mt-8">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-semibold">Users</h2>
        <Button onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancel' : 'Add User'}
        </Button>
      </div>
      {showForm && (
        <form className="mb-4 flex gap-2 flex-wrap" onSubmit={handleAddUser}>
          <input
            className="border rounded px-2 py-1"
            placeholder="First Name"
            value={form.firstName}
            onChange={e => setForm(f => ({ ...f, firstName: e.target.value }))}
            required
          />
          <input
            className="border rounded px-2 py-1"
            placeholder="Last Name"
            value={form.lastName}
            onChange={e => setForm(f => ({ ...f, lastName: e.target.value }))}
            required
          />
          <input
            className="border rounded px-2 py-1"
            placeholder="Email"
            type="email"
            value={form.emailAddress}
            onChange={e => setForm(f => ({ ...f, emailAddress: e.target.value }))}
            required
          />
          <input
            className="border rounded px-2 py-1"
            placeholder="Phone (optional)"
            value={form.phoneNumber || ''}
            onChange={e => setForm(f => ({ ...f, phoneNumber: e.target.value || undefined }))}
          />
          <Button type="submit">Save</Button>
        </form>
      )}
      {formError && <div className="text-red-600">{formError}</div>}
      {(loading || postLoading) ? (
        <div>Loading users...</div>
      ) : error ? (
        <div className="text-red-600">{error instanceof Error ? error.message : String(error)}</div>
      ) : (
        <>
          <table className="min-w-full border mt-2">
            <thead>
              <tr className="bg-gray-200">
                <th className="px-2 py-1 border">User ID</th>
                <th className="px-2 py-1 border">Name</th>
                <th className="px-2 py-1 border">Email</th>
                <th className="px-2 py-1 border">Phone</th>
                <th className="px-2 py-1 border">Status</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.userId} className="odd:bg-gray-50">
                  <td className="px-2 py-1 border">{u.userId}</td>
                  <td className="px-2 py-1 border">{u.firstName} {u.lastName}</td>
                  <td className="px-2 py-1 border">{u.emailAddress}</td>
                  <td className="px-2 py-1 border">{u.phoneNumber || '-'}</td>
                  <td className="px-2 py-1 border">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${
                      u.accountStatus === 'active' ? 'bg-green-100 text-green-800' :
                      u.accountStatus === 'inactive' ? 'bg-gray-100 text-gray-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {u.accountStatus}
                    </span>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-2">No users found.</td>
                </tr>
              )}
            </tbody>
          </table>
          
          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-gray-600">
                Page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button 
                  disabled={page <= 1}
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button 
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
};
