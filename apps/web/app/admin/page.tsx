"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Role = "admin" | "user";

type SessionUser = {
  id: number;
  username: string;
  role: Role;
};

type Company = {
  id: number;
  name: string;
  created_at: string;
};

type User = {
  id: number;
  username: string;
  role: Role;
  company_id: number | null;
  company_name: string | null;
  created_at: string;
};

type Material = {
  id: number;
  name: string;
  company_id: number;
  company_name: string;
  remark: string | null;
  created_at: string;
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export default function AdminPage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [companyName, setCompanyName] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<Role>("user");
  const [userCompanyId, setUserCompanyId] = useState("");
  const [materialName, setMaterialName] = useState("");
  const [materialCompanyId, setMaterialCompanyId] = useState("");
  const [materialRemark, setMaterialRemark] = useState("");

  async function bootstrap() {
    try {
      const auth = await fetchJson<{ user: SessionUser }>("/api/proxy/auth/me");
      if (auth.user.role !== "admin") {
        router.replace("/welcome");
        return;
      }
      setCurrentUser(auth.user);

      const [companyList, userList, materialList] = await Promise.all([
        fetchJson<Company[]>("/api/proxy/admin/companies"),
        fetchJson<User[]>("/api/proxy/admin/users"),
        fetchJson<Material[]>("/api/proxy/admin/materials"),
      ]);

      setCompanies(companyList);
      setUsers(userList);
      setMaterials(materialList);
    } catch {
      router.replace("/login");
      return;
    } finally {
      setAuthChecked(true);
    }
  }

  useEffect(() => {
    void bootstrap();
  }, []);

  async function handleLogout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  async function submitCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const company = await fetchJson<Company>("/api/proxy/admin/companies", {
        method: "POST",
        body: JSON.stringify({ name: companyName }),
      });
      setCompanies((prev) => [company, ...prev]);
      setCompanyName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create company");
    }
  }

  async function submitUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const user = await fetchJson<User>("/api/proxy/admin/users", {
        method: "POST",
        body: JSON.stringify({
          username: newUsername,
          password: newPassword,
          role: newRole,
          company_id: userCompanyId ? Number(userCompanyId) : null,
        }),
      });
      setUsers((prev) => [user, ...prev]);
      setNewUsername("");
      setNewPassword("");
      setNewRole("user");
      setUserCompanyId("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    }
  }

  async function submitMaterial(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const material = await fetchJson<Material>("/api/proxy/admin/materials", {
        method: "POST",
        body: JSON.stringify({
          name: materialName,
          company_id: Number(materialCompanyId),
          remark: materialRemark || null,
        }),
      });
      setMaterials((prev) => [material, ...prev]);
      setMaterialName("");
      setMaterialCompanyId("");
      setMaterialRemark("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create material");
    }
  }

  if (!authChecked) {
    return <main className="flex min-h-screen items-center justify-center text-sm text-stone-500">Loading admin page...</main>;
  }

  return (
    <main className="min-h-screen p-6 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="flex flex-col gap-4 rounded-[32px] bg-[#2f241f] p-8 text-stone-100 shadow-panel lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-stone-300">Admin Control</p>
            <h1 className="mt-3 text-3xl font-semibold">Bootstrap companies, users, and material metadata.</h1>
            <p className="mt-2 text-sm text-stone-300">Signed in as {currentUser?.username}</p>
          </div>
          <Button variant="secondary" onClick={handleLogout}>
            Logout
          </Button>
        </section>

        {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

        <section className="grid gap-6 xl:grid-cols-3">
          <Card className="p-6">
            <h2 className="text-xl font-semibold">Create Company</h2>
            <form className="mt-4 space-y-4" onSubmit={submitCompany}>
              <Input placeholder="Company name" required value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
              <Button className="w-full" type="submit">
                Create Company
              </Button>
            </form>
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-semibold">Create User</h2>
            <form className="mt-4 space-y-4" onSubmit={submitUser}>
              <Input placeholder="Username" required value={newUsername} onChange={(event) => setNewUsername(event.target.value)} />
              <Input
                type="password"
                autoComplete="new-password"
                placeholder="Password"
                required
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
              <select
                className="flex h-11 w-full rounded-2xl border border-border bg-white px-4 text-sm text-foreground outline-none"
                value={newRole}
                onChange={(event) => setNewRole(event.target.value as Role)}
              >
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
              <select
                className="flex h-11 w-full rounded-2xl border border-border bg-white px-4 text-sm text-foreground outline-none"
                value={userCompanyId}
                onChange={(event) => setUserCompanyId(event.target.value)}
              >
                <option value="">No company</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
              <Button className="w-full" type="submit">
                Create User
              </Button>
            </form>
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-semibold">Create Material</h2>
            <form className="mt-4 space-y-4" onSubmit={submitMaterial}>
              <Input placeholder="Material name" required value={materialName} onChange={(event) => setMaterialName(event.target.value)} />
              <select
                className="flex h-11 w-full rounded-2xl border border-border bg-white px-4 text-sm text-foreground outline-none"
                value={materialCompanyId}
                onChange={(event) => setMaterialCompanyId(event.target.value)}
                required
              >
                <option value="">Select company</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
              <textarea
                className="min-h-28 w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm text-foreground outline-none"
                placeholder="Remark"
                value={materialRemark}
                onChange={(event) => setMaterialRemark(event.target.value)}
              />
              <Button className="w-full" type="submit">
                Create Material
              </Button>
            </form>
          </Card>
        </section>

        <section className="grid gap-6 xl:grid-cols-3">
          <Card className="p-6" data-testid="companies-panel">
            <h2 className="text-xl font-semibold">Companies</h2>
            <div className="mt-4 space-y-3">
              {companies.map((company) => (
                <div key={company.id} className="rounded-2xl border border-border bg-white p-4" data-testid="company-item">
                  <p className="font-medium">{company.name}</p>
                </div>
              ))}
              {companies.length === 0 ? <p className="text-sm text-stone-500">No companies yet.</p> : null}
            </div>
          </Card>

          <Card className="p-6" data-testid="users-panel">
            <h2 className="text-xl font-semibold">Users</h2>
            <div className="mt-4 space-y-3">
              {users.map((user) => (
                <div key={user.id} className="rounded-2xl border border-border bg-white p-4" data-testid="user-item">
                  <p className="font-medium">{user.username}</p>
                  <p className="text-sm text-stone-500">
                    {user.role}
                    {user.company_name ? ` · ${user.company_name}` : ""}
                  </p>
                </div>
              ))}
              {users.length === 0 ? <p className="text-sm text-stone-500">No users yet.</p> : null}
            </div>
          </Card>

          <Card className="p-6" data-testid="materials-panel">
            <h2 className="text-xl font-semibold">Materials</h2>
            <div className="mt-4 space-y-3">
              {materials.map((material) => (
                <div key={material.id} className="rounded-2xl border border-border bg-white p-4" data-testid="material-item">
                  <p className="font-medium">{material.name}</p>
                  <p className="text-sm text-stone-500">{material.company_name}</p>
                  {material.remark ? <p className="mt-2 text-sm text-stone-600">{material.remark}</p> : null}
                </div>
              ))}
              {materials.length === 0 ? <p className="text-sm text-stone-500">No materials yet.</p> : null}
            </div>
          </Card>
        </section>
      </div>
    </main>
  );
}
