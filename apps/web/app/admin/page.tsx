"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

/* ==================== Types ==================== */

type Toast = { id: number; message: string; type: "success" | "error" };

type Company = {
  company_id: number;
  company_name: string;
  monthly_video_quota: number;
  monthly_video_remaining: number;
  billing_cycle_start_date: string;
  tts_enabled: boolean;
  ai_voice_monthly_usage: number;
  ai_voice_usage_start_date: string | null;
  asset_library_id: number | null;
  status: string;
  created_at: string;
  updated_at: string;
};

type User = {
  user_id: number;
  company_id: number;
  login_account: string;
  user_name: string | null;
  status: string;
  role: string;
  created_at: string;
  updated_at: string;
};

type Library = {
  asset_library_id: number;
  company_id: number;
  library_name: string;
  root_path: string;
  config_path: string;
  config_version: string | null;
  config_import_status: string;
  config_import_time: string | null;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

type TagGroup = {
  tag_group_id: number;
  asset_library_id: number;
  group_key: string;
  group_name: string;
  group_order: number;
  allow_multi_select: boolean;
  allow_select_all: boolean;
  source_type: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type Tag = {
  tag_id: number;
  asset_library_id: number;
  tag_group_id: number;
  tag_key: string;
  tag_name: string;
  filter_condition: string;
  filter_path: string | null;
  source_value: string | null;
  tag_order: number;
  is_default_selected: boolean;
  status: string;
  created_at: string;
  updated_at: string;
};

type CustomGroup = {
  custom_tag_group_id: number;
  company_id: number;
  user_id: number;
  asset_library_id: number;
  group_name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  tag_ids: number[];
};

type SessionUser = {
  id: number;
  username: string;
  role: string;
};

/* ==================== Helpers ==================== */

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
    throw new Error(payload?.detail ?? payload?.message ?? `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/* ==================== Modal ==================== */

function Modal({
  open,
  onClose,
  title,
  children,
  maxWidth = "max-w-lg",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  maxWidth?: string;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <Card className={`w-full ${maxWidth} max-h-[90vh] overflow-y-auto p-6`}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-stone-400 hover:bg-stone-100 hover:text-stone-600"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        {children}
      </Card>
    </div>
  );
}

/* ==================== Toast ==================== */

function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = (message: string, type: "success" | "error" = "success") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  };

  const ToastContainer = (
    <div className="fixed bottom-6 right-6 z-[60] flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`rounded-2xl px-4 py-3 text-sm shadow-panel ${
            t.type === "error" ? "bg-red-50 text-red-700 border border-red-100" : "bg-card text-foreground border border-border"
          }`}
        >
          {t.message}
        </div>
      ))}
    </div>
  );

  return { showToast, ToastContainer };
}

/* ==================== Select helpers ==================== */

function Select({
  value,
  onChange,
  options,
  placeholder,
  required,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}) {
  return (
    <select
      required={required}
      disabled={disabled}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="flex h-11 w-full rounded-2xl border border-border bg-white px-4 text-sm text-foreground outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:opacity-60 disabled:cursor-not-allowed"
    >
      {placeholder ? <option value="">{placeholder}</option> : null}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

/* ==================== Main Page ==================== */

const TABS = [
  { key: "companies", label: "企业管理" },
  { key: "users", label: "用户管理" },
  { key: "libraries", label: "素材库" },
  { key: "tags", label: "标签管理" },
  { key: "custom-groups", label: "自定义标签组" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function AdminPage() {
  const router = useRouter();
  const { showToast, ToastContainer } = useToast();

  const [authChecked, setAuthChecked] = useState(false);
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("companies");

  /* ---- Data states ---- */
  const [companies, setCompanies] = useState<Company[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [tagGroups, setTagGroups] = useState<TagGroup[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [customGroups, setCustomGroups] = useState<CustomGroup[]>([]);

  /* ---- Modal states ---- */
  // Companies
  const [companyModalOpen, setCompanyModalOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [companyForm, setCompanyForm] = useState({
    company_name: "",
    monthly_video_quota: 0,
    monthly_video_remaining: 0,
    billing_cycle_start_date: "",
    tts_enabled: false,
    status: "active",
  });

  // Users
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [userForm, setUserForm] = useState({
    company_id: "",
    login_account: "",
    password: "",
    user_name: "",
    status: "active",
    role: "user",
  });

  // Libraries
  const [libraryModalOpen, setLibraryModalOpen] = useState(false);
  const [editingLibrary, setEditingLibrary] = useState<Library | null>(null);
  const [libraryForm, setLibraryForm] = useState({
    company_id: "",
    library_name: "",
    root_path: "",
    config_path: "",
    description: "",
    status: "active",
  });

  // Tag Groups
  const [tagGroupModalOpen, setTagGroupModalOpen] = useState(false);
  const [editingTagGroup, setEditingTagGroup] = useState<TagGroup | null>(null);
  const [tagGroupForm, setTagGroupForm] = useState({
    asset_library_id: "",
    group_key: "",
    group_name: "",
    allow_multi_select: false,
    allow_select_all: false,
    source_type: "manual",
    status: "active",
  });
  const [selectedTagGroupId, setSelectedTagGroupId] = useState<number | null>(null);

  // Tags
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [tagForm, setTagForm] = useState({
    asset_library_id: "",
    tag_group_id: "",
    tag_key: "",
    tag_name: "",
    filter_condition: "",
    filter_path: "",
    source_value: "",
    is_default_selected: false,
    status: "active",
  });

  // Custom Groups
  const [customGroupModalOpen, setCustomGroupModalOpen] = useState(false);
  const [viewingCustomGroup, setViewingCustomGroup] = useState<CustomGroup | null>(null);
  const [editingCustomGroup, setEditingCustomGroup] = useState<CustomGroup | null>(null);
  const [customGroupForm, setCustomGroupForm] = useState({
    company_id: "",
    user_id: "",
    asset_library_id: "",
    group_name: "",
    description: "",
    status: "active",
    tag_ids: [] as number[],
  });

  /* ---- Derived ---- */
  const companyOptions = useMemo(
    () => companies.map((c) => ({ value: String(c.company_id), label: c.company_name })),
    [companies]
  );
  const libraryOptions = useMemo(
    () => libraries.map((l) => ({ value: String(l.asset_library_id), label: l.library_name })),
    [libraries]
  );
  const userOptions = useMemo(
    () => users.map((u) => ({ value: String(u.user_id), label: `${u.login_account}${u.user_name ? ` (${u.user_name})` : ""}` })),
    [users]
  );
  const tagGroupOptionsForLibrary = useMemo(() => {
    if (!tagForm.asset_library_id) return [];
    const libId = Number(tagForm.asset_library_id);
    return tagGroups
      .filter((tg) => tg.asset_library_id === libId)
      .map((tg) => ({ value: String(tg.tag_group_id), label: tg.group_name }));
  }, [tagGroups, tagForm.asset_library_id]);
  const tagGroupOptionsForCustom = useMemo(() => {
    if (!customGroupForm.asset_library_id) return [];
    const libId = Number(customGroupForm.asset_library_id);
    return tagGroups
      .filter((tg) => tg.asset_library_id === libId)
      .map((tg) => ({ value: String(tg.tag_group_id), label: tg.group_name }));
  }, [tagGroups, customGroupForm.asset_library_id]);
  const availableTagsForCustom = useMemo(() => {
    if (!customGroupForm.asset_library_id) return [];
    const libId = Number(customGroupForm.asset_library_id);
    return tags.filter((t) => t.asset_library_id === libId);
  }, [tags, customGroupForm.asset_library_id]);
  const userOptionsForCustom = useMemo(() => {
    if (!customGroupForm.company_id) return [];
    const cid = Number(customGroupForm.company_id);
    return users
      .filter((u) => u.company_id === cid)
      .map((u) => ({ value: String(u.user_id), label: `${u.login_account}${u.user_name ? ` (${u.user_name})` : ""}` }));
  }, [users, customGroupForm.company_id]);

  /* ---- Bootstrap ---- */
  async function bootstrap() {
    try {
      const auth = await fetchJson<{ user: SessionUser }>("/api/proxy/auth/me");
      if (auth.user.role !== "admin") {
        router.replace("/welcome");
        return;
      }
      setCurrentUser(auth.user);

      await Promise.all([
        fetchCompanies(),
        fetchUsers(),
        fetchLibraries(),
        fetchTagGroups(),
        fetchTags(),
        fetchCustomGroups(),
      ]);
    } catch {
      router.replace("/login");
    } finally {
      setAuthChecked(true);
    }
  }

  useEffect(() => {
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ---- Fetchers ---- */
  async function fetchCompanies() {
    try {
      const data = await fetchJson<Company[]>("/api/proxy/admin/api/companies");
      setCompanies(data);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "获取企业列表失败", "error");
    }
  }
  async function fetchUsers() {
    try {
      const data = await fetchJson<User[]>("/api/proxy/admin/api/users");
      setUsers(data);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "获取用户列表失败", "error");
    }
  }
  async function fetchLibraries() {
    try {
      const data = await fetchJson<Library[]>("/api/proxy/admin/api/libraries");
      setLibraries(data);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "获取素材库列表失败", "error");
    }
  }
  async function fetchTagGroups() {
    try {
      const data = await fetchJson<TagGroup[]>("/api/proxy/admin/api/tag-groups");
      setTagGroups(data);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "获取标签组列表失败", "error");
    }
  }
  async function fetchTags() {
    try {
      const data = await fetchJson<Tag[]>("/api/proxy/admin/api/tags");
      setTags(data);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "获取标签列表失败", "error");
    }
  }
  async function fetchCustomGroups() {
    try {
      const data = await fetchJson<CustomGroup[]>("/api/proxy/admin/api/custom-groups");
      setCustomGroups(data);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "获取自定义标签组列表失败", "error");
    }
  }

  /* ---- Handlers: Companies ---- */
  function openCompanyModal(company?: Company) {
    if (company) {
      setEditingCompany(company);
      setCompanyForm({
        company_name: company.company_name,
        monthly_video_quota: company.monthly_video_quota,
        monthly_video_remaining: company.monthly_video_remaining,
        billing_cycle_start_date: company.billing_cycle_start_date?.slice(0, 10) ?? "",
        tts_enabled: company.tts_enabled,
        status: company.status,
      });
    } else {
      setEditingCompany(null);
      setCompanyForm({
        company_name: "",
        monthly_video_quota: 100,
        monthly_video_remaining: 100,
        billing_cycle_start_date: "",
        tts_enabled: false,
        status: "active",
      });
    }
    setCompanyModalOpen(true);
  }

  async function submitCompany(e: FormEvent) {
    e.preventDefault();
    try {
      if (editingCompany) {
        await fetchJson(`/api/proxy/admin/api/companies/${editingCompany.company_id}`, {
          method: "PUT",
          body: JSON.stringify({
            company_name: companyForm.company_name,
            monthly_video_quota: companyForm.monthly_video_quota,
            monthly_video_remaining: companyForm.monthly_video_remaining,
            billing_cycle_start_date: companyForm.billing_cycle_start_date || null,
            tts_enabled: companyForm.tts_enabled,
            status: companyForm.status,
          }),
        });
        showToast("企业更新成功");
      } else {
        await fetchJson("/api/proxy/admin/api/companies", {
          method: "POST",
          body: JSON.stringify({
            company_name: companyForm.company_name,
            monthly_video_quota: companyForm.monthly_video_quota,
            monthly_video_remaining: companyForm.monthly_video_remaining,
            billing_cycle_start_date: companyForm.billing_cycle_start_date || null,
            tts_enabled: companyForm.tts_enabled,
            status: companyForm.status,
          }),
        });
        showToast("企业创建成功");
      }
      setCompanyModalOpen(false);
      await fetchCompanies();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失败", "error");
    }
  }

  async function deleteCompany(id: number) {
    if (!confirm("确定要删除该企业吗？")) return;
    try {
      await fetchJson(`/api/proxy/admin/api/companies/${id}`, { method: "DELETE" });
      showToast("企业删除成功");
      await fetchCompanies();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "删除失败", "error");
    }
  }

  /* ---- Handlers: Users ---- */
  function openUserModal(user?: User) {
    if (user) {
      setEditingUser(user);
      setUserForm({
        company_id: String(user.company_id),
        login_account: user.login_account,
        password: "",
        user_name: user.user_name ?? "",
        status: user.status,
        role: user.role,
      });
    } else {
      setEditingUser(null);
      setUserForm({
        company_id: "",
        login_account: "",
        password: "",
        user_name: "",
        status: "active",
        role: "user",
      });
    }
    setUserModalOpen(true);
  }

  async function submitUser(e: FormEvent) {
    e.preventDefault();
    try {
      const payload: Record<string, unknown> = {
        company_id: Number(userForm.company_id),
        login_account: userForm.login_account,
        user_name: userForm.user_name || null,
        status: userForm.status,
        role: userForm.role,
      };
      if (!editingUser || userForm.password) {
        payload.password = userForm.password;
      }
      if (editingUser) {
        await fetchJson(`/api/proxy/admin/api/users/${editingUser.user_id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        showToast("用户更新成功");
      } else {
        await fetchJson("/api/proxy/admin/api/users", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast("用户创建成功");
      }
      setUserModalOpen(false);
      await fetchUsers();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失败", "error");
    }
  }

  async function deleteUser(id: number) {
    if (!confirm("确定要删除该用户吗？")) return;
    try {
      await fetchJson(`/api/proxy/admin/api/users/${id}`, { method: "DELETE" });
      showToast("用户删除成功");
      await fetchUsers();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "删除失败", "error");
    }
  }

  /* ---- Handlers: Libraries ---- */
  function openLibraryModal(library?: Library) {
    if (library) {
      setEditingLibrary(library);
      setLibraryForm({
        company_id: String(library.company_id),
        library_name: library.library_name,
        root_path: library.root_path,
        config_path: library.config_path,
        description: library.description ?? "",
        status: library.status,
      });
    } else {
      setEditingLibrary(null);
      setLibraryForm({
        company_id: "",
        library_name: "",
        root_path: "",
        config_path: "",
        description: "",
        status: "active",
      });
    }
    setLibraryModalOpen(true);
  }

  async function submitLibrary(e: FormEvent) {
    e.preventDefault();
    try {
      const payload = {
        company_id: Number(libraryForm.company_id),
        library_name: libraryForm.library_name,
        root_path: libraryForm.root_path,
        config_path: libraryForm.config_path,
        description: libraryForm.description || null,
        status: libraryForm.status,
      };
      if (editingLibrary) {
        await fetchJson(`/api/proxy/admin/api/libraries/${editingLibrary.asset_library_id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        showToast("素材库更新成功");
      } else {
        await fetchJson("/api/proxy/admin/api/libraries", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast("素材库创建成功");
      }
      setLibraryModalOpen(false);
      await fetchLibraries();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失败", "error");
    }
  }

  async function deleteLibrary(id: number) {
    if (!confirm("确定要删除该素材库吗？")) return;
    try {
      await fetchJson(`/api/proxy/admin/api/libraries/${id}`, { method: "DELETE" });
      showToast("素材库删除成功");
      await fetchLibraries();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "删除失败", "error");
    }
  }

  async function importLibrary(id: number) {
    try {
      await fetchJson(`/api/proxy/admin/api/libraries/${id}/import`, { method: "POST" });
      showToast("素材库导入请求已提交");
      await fetchLibraries();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "导入失败", "error");
    }
  }

  /* ---- Handlers: Tag Groups ---- */
  function openTagGroupModal(tagGroup?: TagGroup) {
    if (tagGroup) {
      setEditingTagGroup(tagGroup);
      setTagGroupForm({
        asset_library_id: String(tagGroup.asset_library_id),
        group_key: tagGroup.group_key,
        group_name: tagGroup.group_name,
        allow_multi_select: tagGroup.allow_multi_select,
        allow_select_all: tagGroup.allow_select_all,
        source_type: tagGroup.source_type,
        status: tagGroup.status,
      });
    } else {
      setEditingTagGroup(null);
      setTagGroupForm({
        asset_library_id: "",
        group_key: "",
        group_name: "",
        allow_multi_select: false,
        allow_select_all: false,
        source_type: "manual",
        status: "active",
      });
    }
    setTagGroupModalOpen(true);
  }

  async function submitTagGroup(e: FormEvent) {
    e.preventDefault();
    try {
      const payload = {
        asset_library_id: Number(tagGroupForm.asset_library_id),
        group_key: tagGroupForm.group_key,
        group_name: tagGroupForm.group_name,
        allow_multi_select: tagGroupForm.allow_multi_select,
        allow_select_all: tagGroupForm.allow_select_all,
        source_type: tagGroupForm.source_type,
        status: tagGroupForm.status,
      };
      if (editingTagGroup) {
        await fetchJson(`/api/proxy/admin/api/tag-groups/${editingTagGroup.tag_group_id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        showToast("标签组更新成功");
      } else {
        await fetchJson("/api/proxy/admin/api/tag-groups", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast("标签组创建成功");
      }
      setTagGroupModalOpen(false);
      await fetchTagGroups();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失败", "error");
    }
  }

  async function deleteTagGroup(id: number) {
    if (!confirm("确定要删除该标签组吗？（组内标签也会被删除）")) return;
    try {
      await fetchJson(`/api/proxy/admin/api/tag-groups/${id}`, { method: "DELETE" });
      showToast("标签组删除成功");
      if (selectedTagGroupId === id) setSelectedTagGroupId(null);
      await fetchTagGroups();
      await fetchTags();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "删除失败", "error");
    }
  }

  /* ---- Handlers: Tags ---- */
  function openTagModal(tag?: Tag) {
    if (tag) {
      setEditingTag(tag);
      setTagForm({
        asset_library_id: String(tag.asset_library_id),
        tag_group_id: String(tag.tag_group_id),
        tag_key: tag.tag_key,
        tag_name: tag.tag_name,
        filter_condition: tag.filter_condition,
        filter_path: tag.filter_path ?? "",
        source_value: tag.source_value ?? "",
        is_default_selected: tag.is_default_selected,
        status: tag.status,
      });
    } else {
      setEditingTag(null);
      setTagForm({
        asset_library_id: "",
        tag_group_id: "",
        tag_key: "",
        tag_name: "",
        filter_condition: "",
        filter_path: "",
        source_value: "",
        is_default_selected: false,
        status: "active",
      });
    }
    setTagModalOpen(true);
  }

  async function submitTag(e: FormEvent) {
    e.preventDefault();
    try {
      const payload = {
        asset_library_id: Number(tagForm.asset_library_id),
        tag_group_id: Number(tagForm.tag_group_id),
        tag_key: tagForm.tag_key,
        tag_name: tagForm.tag_name,
        filter_condition: tagForm.filter_condition,
        filter_path: tagForm.filter_path || null,
        source_value: tagForm.source_value || null,
        is_default_selected: tagForm.is_default_selected,
        status: tagForm.status,
      };
      if (editingTag) {
        await fetchJson(`/api/proxy/admin/api/tags/${editingTag.tag_id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        showToast("标签更新成功");
      } else {
        await fetchJson("/api/proxy/admin/api/tags", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast("标签创建成功");
      }
      setTagModalOpen(false);
      await fetchTags();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失败", "error");
    }
  }

  async function deleteTag(id: number) {
    if (!confirm("确定要删除该标签吗？")) return;
    try {
      await fetchJson(`/api/proxy/admin/api/tags/${id}`, { method: "DELETE" });
      showToast("标签删除成功");
      await fetchTags();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "删除失败", "error");
    }
  }

  /* ---- Handlers: Custom Groups ---- */
  function openCustomGroupModal(customGroup?: CustomGroup) {
    if (customGroup) {
      setEditingCustomGroup(customGroup);
      setCustomGroupForm({
        company_id: String(customGroup.company_id),
        user_id: String(customGroup.user_id),
        asset_library_id: String(customGroup.asset_library_id),
        group_name: customGroup.group_name,
        description: customGroup.description ?? "",
        status: customGroup.status,
        tag_ids: [...customGroup.tag_ids],
      });
    } else {
      setEditingCustomGroup(null);
      setCustomGroupForm({
        company_id: "",
        user_id: "",
        asset_library_id: "",
        group_name: "",
        description: "",
        status: "active",
        tag_ids: [],
      });
    }
    setCustomGroupModalOpen(true);
  }

  async function submitCustomGroup(e: FormEvent) {
    e.preventDefault();
    try {
      const payload = {
        company_id: Number(customGroupForm.company_id),
        user_id: Number(customGroupForm.user_id),
        asset_library_id: Number(customGroupForm.asset_library_id),
        group_name: customGroupForm.group_name,
        description: customGroupForm.description || null,
        status: customGroupForm.status,
        tag_ids: customGroupForm.tag_ids,
      };
      if (editingCustomGroup) {
        await fetchJson(`/api/proxy/admin/api/custom-groups/${editingCustomGroup.custom_tag_group_id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        showToast("自定义标签组更新成功");
      } else {
        await fetchJson("/api/proxy/admin/api/custom-groups", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast("自定义标签组创建成功");
      }
      setCustomGroupModalOpen(false);
      await fetchCustomGroups();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失败", "error");
    }
  }

  async function deleteCustomGroup(id: number) {
    if (!confirm("确定要删除该自定义标签组吗？")) return;
    try {
      await fetchJson(`/api/proxy/admin/api/custom-groups/${id}`, { method: "DELETE" });
      showToast("自定义标签组删除成功");
      await fetchCustomGroups();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "删除失败", "error");
    }
  }

  function getTagNamesByIds(ids: number[]) {
    return ids.map((id) => tags.find((t) => t.tag_id === id)?.tag_name ?? `ID:${id}`);
  }

  async function handleLogout() {
    await fetch("/api/proxy/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  /* ==================== Render: Companies Tab ==================== */
  function renderCompaniesTab() {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">企业管理</h2>
          <Button onClick={() => openCompanyModal()}>新增企业</Button>
        </div>
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-stone-100/60 text-left">
                <tr>
                  <th className="px-4 py-3 font-semibold">企业名称</th>
                  <th className="px-4 py-3 font-semibold">额度/剩余</th>
                  <th className="px-4 py-3 font-semibold">TTS</th>
                  <th className="px-4 py-3 font-semibold">状态</th>
                  <th className="px-4 py-3 font-semibold text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((c) => (
                  <tr key={c.company_id} className="border-t border-border">
                    <td className="px-4 py-3">{c.company_name}</td>
                    <td className="px-4 py-3">
                      {c.monthly_video_remaining} / {c.monthly_video_quota}
                    </td>
                    <td className="px-4 py-3">{c.tts_enabled ? "是" : "否"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs ${
                          c.status === "active"
                            ? "bg-green-50 text-green-700"
                            : "bg-stone-100 text-stone-500"
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" className="h-8 px-3 text-xs" onClick={() => openCompanyModal(c)}>
                          编辑
                        </Button>
                        <Button variant="ghost" className="h-8 px-3 text-xs text-red-600 hover:text-red-700" onClick={() => deleteCompany(c.company_id)}>
                          删除
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
                {companies.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-stone-400">
                      暂无企业数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  }

  /* ==================== Render: Users Tab ==================== */
  function renderUsersTab() {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">用户管理</h2>
          <Button onClick={() => openUserModal()}>新增用户</Button>
        </div>
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-stone-100/60 text-left">
                <tr>
                  <th className="px-4 py-3 font-semibold">登录账号</th>
                  <th className="px-4 py-3 font-semibold">用户名称</th>
                  <th className="px-4 py-3 font-semibold">所属企业</th>
                  <th className="px-4 py-3 font-semibold">状态</th>
                  <th className="px-4 py-3 font-semibold text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id} className="border-t border-border">
                    <td className="px-4 py-3">{u.login_account}</td>
                    <td className="px-4 py-3">{u.user_name ?? "-"}</td>
                    <td className="px-4 py-3">
                      {companies.find((c) => c.company_id === u.company_id)?.company_name ?? u.company_id}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs ${
                          u.status === "active" ? "bg-green-50 text-green-700" : "bg-stone-100 text-stone-500"
                        }`}
                      >
                        {u.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" className="h-8 px-3 text-xs" onClick={() => openUserModal(u)}>
                          编辑
                        </Button>
                        <Button variant="ghost" className="h-8 px-3 text-xs text-red-600 hover:text-red-700" onClick={() => deleteUser(u.user_id)}>
                          删除
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-stone-400">
                      暂无用户数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  }

  /* ==================== Render: Libraries Tab ==================== */
  function renderLibrariesTab() {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">素材库</h2>
          <Button onClick={() => openLibraryModal()}>新增素材库</Button>
        </div>
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-stone-100/60 text-left">
                <tr>
                  <th className="px-4 py-3 font-semibold">库名称</th>
                  <th className="px-4 py-3 font-semibold">所属企业</th>
                  <th className="px-4 py-3 font-semibold">导入状态</th>
                  <th className="px-4 py-3 font-semibold">状态</th>
                  <th className="px-4 py-3 font-semibold text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {libraries.map((l) => (
                  <tr key={l.asset_library_id} className="border-t border-border">
                    <td className="px-4 py-3">{l.library_name}</td>
                    <td className="px-4 py-3">
                      {companies.find((c) => c.company_id === l.company_id)?.company_name ?? l.company_id}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs ${
                          l.config_import_status === "success"
                            ? "bg-green-50 text-green-700"
                            : l.config_import_status === "pending"
                            ? "bg-yellow-50 text-yellow-700"
                            : l.config_import_status === "importing"
                            ? "bg-blue-50 text-blue-700"
                            : "bg-stone-100 text-stone-500"
                        }`}
                      >
                        {l.config_import_status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs ${
                          l.status === "active" ? "bg-green-50 text-green-700" : "bg-stone-100 text-stone-500"
                        }`}
                      >
                        {l.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" className="h-8 px-3 text-xs" onClick={() => importLibrary(l.asset_library_id)}>
                          导入
                        </Button>
                        <Button variant="ghost" className="h-8 px-3 text-xs" onClick={() => openLibraryModal(l)}>
                          编辑
                        </Button>
                        <Button variant="ghost" className="h-8 px-3 text-xs text-red-600 hover:text-red-700" onClick={() => deleteLibrary(l.asset_library_id)}>
                          删除
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
                {libraries.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-stone-400">
                      暂无素材库数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  }

  /* ==================== Render: Tags Tab ==================== */
  function renderTagsTab() {
    const selectedGroup = tagGroups.find((tg) => tg.tag_group_id === selectedTagGroupId);
    const groupTags = selectedTagGroupId ? tags.filter((t) => t.tag_group_id === selectedTagGroupId) : [];

    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">标签管理</h2>
        <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
          {/* Left: Tag Groups */}
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold">标签组</h3>
              <Button className="h-8 px-3 text-xs" onClick={() => openTagGroupModal()}>
                新增
              </Button>
            </div>
            <div className="space-y-2 max-h-[60vh] overflow-y-auto">
              {tagGroups.map((tg) => {
                const lib = libraries.find((l) => l.asset_library_id === tg.asset_library_id);
                const isSelected = selectedTagGroupId === tg.tag_group_id;
                return (
                  <div
                    key={tg.tag_group_id}
                    onClick={() => setSelectedTagGroupId(tg.tag_group_id)}
                    className={`cursor-pointer rounded-2xl border p-3 transition ${
                      isSelected ? "border-accent bg-accent/5" : "border-border hover:bg-stone-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-sm">{tg.group_name}</p>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteTagGroup(tg.tag_group_id);
                        }}
                        className="text-stone-400 hover:text-red-600"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                    <p className="mt-1 text-xs text-stone-400">
                      {lib?.library_name ?? `库${tg.asset_library_id}`} · {tg.group_key}
                    </p>
                  </div>
                );
              })}
              {tagGroups.length === 0 && <p className="text-sm text-stone-400 py-4 text-center">暂无标签组</p>}
            </div>
          </Card>

          {/* Right: Tags */}
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold">
                {selectedGroup ? `${selectedGroup.group_name} - 标签列表` : "请选择左侧标签组"}
              </h3>
              {selectedGroup && (
                <Button className="h-8 px-3 text-xs" onClick={() => openTagModal()}>
                  新增标签
                </Button>
              )}
            </div>
            {selectedGroup ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-stone-100/60 text-left">
                    <tr>
                      <th className="px-3 py-2 font-semibold">标签名</th>
                      <th className="px-3 py-2 font-semibold">Key</th>
                      <th className="px-3 py-2 font-semibold">筛选条件</th>
                      <th className="px-3 py-2 font-semibold text-right">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupTags.map((t) => (
                      <tr key={t.tag_id} className="border-t border-border">
                        <td className="px-3 py-2">{t.tag_name}</td>
                        <td className="px-3 py-2 text-stone-500">{t.tag_key}</td>
                        <td className="px-3 py-2 text-stone-500 truncate max-w-[200px]">{t.filter_condition}</td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" className="h-7 px-2 text-xs" onClick={() => openTagModal(t)}>
                              编辑
                            </Button>
                            <Button variant="ghost" className="h-7 px-2 text-xs text-red-600 hover:text-red-700" onClick={() => deleteTag(t.tag_id)}>
                              删除
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {groupTags.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 py-8 text-center text-stone-400">
                          该标签组下暂无标签
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex h-48 items-center justify-center text-stone-400 text-sm">点击左侧标签组查看标签</div>
            )}
          </Card>
        </div>
      </div>
    );
  }

  /* ==================== Render: Custom Groups Tab ==================== */
  function renderCustomGroupsTab() {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">自定义标签组</h2>
          <Button onClick={() => openCustomGroupModal()}>新增自定义标签组</Button>
        </div>
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-stone-100/60 text-left">
                <tr>
                  <th className="px-4 py-3 font-semibold">组名称</th>
                  <th className="px-4 py-3 font-semibold">所属用户</th>
                  <th className="px-4 py-3 font-semibold">标签数</th>
                  <th className="px-4 py-3 font-semibold">状态</th>
                  <th className="px-4 py-3 font-semibold text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {customGroups.map((cg) => {
                  const user = users.find((u) => u.user_id === cg.user_id);
                  return (
                    <tr key={cg.custom_tag_group_id} className="border-t border-border">
                      <td className="px-4 py-3">{cg.group_name}</td>
                      <td className="px-4 py-3">{user ? `${user.login_account}${user.user_name ? ` (${user.user_name})` : ""}` : cg.user_id}</td>
                      <td className="px-4 py-3">{cg.tag_ids.length}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs ${
                            cg.status === "active" ? "bg-green-50 text-green-700" : "bg-stone-100 text-stone-500"
                          }`}
                        >
                          {cg.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" className="h-8 px-3 text-xs" onClick={() => setViewingCustomGroup(cg)}>
                            查看
                          </Button>
                          <Button variant="ghost" className="h-8 px-3 text-xs" onClick={() => openCustomGroupModal(cg)}>
                            编辑
                          </Button>
                          <Button variant="ghost" className="h-8 px-3 text-xs text-red-600 hover:text-red-700" onClick={() => deleteCustomGroup(cg.custom_tag_group_id)}>
                            删除
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {customGroups.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-stone-400">
                      暂无自定义标签组数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  }

  /* ==================== Loading ==================== */
  if (!authChecked) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm text-stone-500">
        Loading admin page...
      </main>
    );
  }

  /* ==================== Main Layout ==================== */
  return (
    <main className="min-h-screen p-6 lg:p-8">
      {ToastContainer}

      {/* Header */}
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="flex flex-col gap-4 rounded-[32px] bg-[#2f241f] p-8 text-stone-100 shadow-panel lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-stone-300">Admin Control</p>
            <h1 className="mt-3 text-3xl font-semibold">管理后台</h1>
            <p className="mt-2 text-sm text-stone-300">Signed in as {currentUser?.username}</p>
          </div>
          <Button variant="secondary" onClick={handleLogout}>
            Logout
          </Button>
        </section>

        {/* Tabs */}
        <div className="flex flex-wrap gap-2">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-full px-5 py-2.5 text-sm font-semibold transition ${
                activeTab === tab.key
                  ? "bg-accent text-white"
                  : "bg-white text-foreground ring-1 ring-border hover:bg-stone-50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <section>
          {activeTab === "companies" && renderCompaniesTab()}
          {activeTab === "users" && renderUsersTab()}
          {activeTab === "libraries" && renderLibrariesTab()}
          {activeTab === "tags" && renderTagsTab()}
          {activeTab === "custom-groups" && renderCustomGroupsTab()}
        </section>
      </div>

      {/* ==================== Modals ==================== */}

      {/* Company Modal */}
      <Modal open={companyModalOpen} onClose={() => setCompanyModalOpen(false)} title={editingCompany ? "编辑企业" : "新增企业"}>
        <form onSubmit={submitCompany} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">企业名称</label>
            <Input required value={companyForm.company_name} onChange={(e) => setCompanyForm({ ...companyForm, company_name: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">月度额度</label>
              <Input type="number" required min={0} value={companyForm.monthly_video_quota} onChange={(e) => setCompanyForm({ ...companyForm, monthly_video_quota: Number(e.target.value) })} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">剩余额度</label>
              <Input type="number" required min={0} value={companyForm.monthly_video_remaining} onChange={(e) => setCompanyForm({ ...companyForm, monthly_video_remaining: Number(e.target.value) })} />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">计费周期开始日期</label>
            <Input type="date" value={companyForm.billing_cycle_start_date} onChange={(e) => setCompanyForm({ ...companyForm, billing_cycle_start_date: e.target.value })} />
          </div>
          <div className="flex items-center gap-3">
            <input
              id="tts"
              type="checkbox"
              checked={companyForm.tts_enabled}
              onChange={(e) => setCompanyForm({ ...companyForm, tts_enabled: e.target.checked })}
              className="h-4 w-4 rounded border-border accent-accent"
            />
            <label htmlFor="tts" className="text-sm font-medium">启用 TTS</label>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">状态</label>
            <Select
              value={companyForm.status}
              onChange={(v) => setCompanyForm({ ...companyForm, status: v })}
              options={[
                { value: "active", label: "active" },
                { value: "inactive", label: "inactive" },
                { value: "suspended", label: "suspended" },
              ]}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setCompanyModalOpen(false)}>
              取消
            </Button>
            <Button type="submit">保存</Button>
          </div>
        </form>
      </Modal>

      {/* User Modal */}
      <Modal open={userModalOpen} onClose={() => setUserModalOpen(false)} title={editingUser ? "编辑用户" : "新增用户"}>
        <form onSubmit={submitUser} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">所属企业</label>
            <Select
              required
              value={userForm.company_id}
              onChange={(v) => setUserForm({ ...userForm, company_id: v })}
              placeholder="选择企业"
              options={companyOptions}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">登录账号</label>
            <Input required value={userForm.login_account} onChange={(e) => setUserForm({ ...userForm, login_account: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">
              密码 {editingUser ? "（留空表示不修改）" : ""}
            </label>
            <Input
              type="password"
              autoComplete="new-password"
              required={!editingUser}
              value={userForm.password}
              onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">用户名称</label>
            <Input value={userForm.user_name} onChange={(e) => setUserForm({ ...userForm, user_name: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">角色</label>
            <Select
              value={userForm.role}
              onChange={(v) => setUserForm({ ...userForm, role: v })}
              options={[
                { value: "user", label: "user" },
                { value: "admin", label: "admin" },
              ]}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">状态</label>
            <Select
              value={userForm.status}
              onChange={(v) => setUserForm({ ...userForm, status: v })}
              options={[
                { value: "active", label: "active" },
                { value: "inactive", label: "inactive" },
                { value: "suspended", label: "suspended" },
              ]}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setUserModalOpen(false)}>
              取消
            </Button>
            <Button type="submit">保存</Button>
          </div>
        </form>
      </Modal>

      {/* Library Modal */}
      <Modal open={libraryModalOpen} onClose={() => setLibraryModalOpen(false)} title={editingLibrary ? "编辑素材库" : "新增素材库"}>
        <form onSubmit={submitLibrary} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">所属企业</label>
            <Select
              required
              value={libraryForm.company_id}
              onChange={(v) => setLibraryForm({ ...libraryForm, company_id: v })}
              placeholder="选择企业"
              options={companyOptions}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">库名称</label>
            <Input required value={libraryForm.library_name} onChange={(e) => setLibraryForm({ ...libraryForm, library_name: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">根路径</label>
            <Input required value={libraryForm.root_path} onChange={(e) => setLibraryForm({ ...libraryForm, root_path: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">配置文件路径</label>
            <Input required value={libraryForm.config_path} onChange={(e) => setLibraryForm({ ...libraryForm, config_path: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">描述</label>
            <textarea
              className="min-h-24 w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm text-foreground outline-none transition placeholder:text-stone-400 focus:border-accent focus:ring-2 focus:ring-accent/20"
              value={libraryForm.description}
              onChange={(e) => setLibraryForm({ ...libraryForm, description: e.target.value })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">状态</label>
            <Select
              value={libraryForm.status}
              onChange={(v) => setLibraryForm({ ...libraryForm, status: v })}
              options={[
                { value: "active", label: "active" },
                { value: "inactive", label: "inactive" },
              ]}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setLibraryModalOpen(false)}>
              取消
            </Button>
            <Button type="submit">保存</Button>
          </div>
        </form>
      </Modal>

      {/* Tag Group Modal */}
      <Modal open={tagGroupModalOpen} onClose={() => setTagGroupModalOpen(false)} title={editingTagGroup ? "编辑标签组" : "新增标签组"}>
        <form onSubmit={submitTagGroup} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">所属素材库</label>
            <Select
              required
              value={tagGroupForm.asset_library_id}
              onChange={(v) => setTagGroupForm({ ...tagGroupForm, asset_library_id: v })}
              placeholder="选择素材库"
              options={libraryOptions}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Key</label>
            <Input required value={tagGroupForm.group_key} onChange={(e) => setTagGroupForm({ ...tagGroupForm, group_key: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">组名称</label>
            <Input required value={tagGroupForm.group_name} onChange={(e) => setTagGroupForm({ ...tagGroupForm, group_name: e.target.value })} />
          </div>
          <div className="flex items-center gap-3">
            <input
              id="allowMulti"
              type="checkbox"
              checked={tagGroupForm.allow_multi_select}
              onChange={(e) => setTagGroupForm({ ...tagGroupForm, allow_multi_select: e.target.checked })}
              className="h-4 w-4 rounded border-border accent-accent"
            />
            <label htmlFor="allowMulti" className="text-sm font-medium">允许多选</label>
          </div>
          <div className="flex items-center gap-3">
            <input
              id="allowAll"
              type="checkbox"
              checked={tagGroupForm.allow_select_all}
              onChange={(e) => setTagGroupForm({ ...tagGroupForm, allow_select_all: e.target.checked })}
              className="h-4 w-4 rounded border-border accent-accent"
            />
            <label htmlFor="allowAll" className="text-sm font-medium">允许全选</label>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">来源类型</label>
            <Select
              value={tagGroupForm.source_type}
              onChange={(v) => setTagGroupForm({ ...tagGroupForm, source_type: v })}
              options={[
                { value: "manual", label: "manual" },
                { value: "auto", label: "auto" },
                { value: "config", label: "config" },
              ]}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">状态</label>
            <Select
              value={tagGroupForm.status}
              onChange={(v) => setTagGroupForm({ ...tagGroupForm, status: v })}
              options={[
                { value: "active", label: "active" },
                { value: "inactive", label: "inactive" },
              ]}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setTagGroupModalOpen(false)}>
              取消
            </Button>
            <Button type="submit">保存</Button>
          </div>
        </form>
      </Modal>

      {/* Tag Modal */}
      <Modal open={tagModalOpen} onClose={() => setTagModalOpen(false)} title={editingTag ? "编辑标签" : "新增标签"}>
        <form onSubmit={submitTag} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">所属素材库</label>
            <Select
              required
              value={tagForm.asset_library_id}
              onChange={(v) => setTagForm({ ...tagForm, asset_library_id: v, tag_group_id: "" })}
              placeholder="选择素材库"
              options={libraryOptions}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">所属标签组</label>
            <Select
              required
              value={tagForm.tag_group_id}
              onChange={(v) => setTagForm({ ...tagForm, tag_group_id: v })}
              placeholder={tagForm.asset_library_id ? "选择标签组" : "请先选择素材库"}
              disabled={!tagForm.asset_library_id}
              options={tagGroupOptionsForLibrary}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Key</label>
            <Input required value={tagForm.tag_key} onChange={(e) => setTagForm({ ...tagForm, tag_key: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">标签名称</label>
            <Input required value={tagForm.tag_name} onChange={(e) => setTagForm({ ...tagForm, tag_name: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">筛选条件</label>
            <Input value={tagForm.filter_condition} onChange={(e) => setTagForm({ ...tagForm, filter_condition: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">筛选路径</label>
            <Input value={tagForm.filter_path} onChange={(e) => setTagForm({ ...tagForm, filter_path: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">来源值</label>
            <Input value={tagForm.source_value} onChange={(e) => setTagForm({ ...tagForm, source_value: e.target.value })} />
          </div>
          <div className="flex items-center gap-3">
            <input
              id="tagDefault"
              type="checkbox"
              checked={tagForm.is_default_selected}
              onChange={(e) => setTagForm({ ...tagForm, is_default_selected: e.target.checked })}
              className="h-4 w-4 rounded border-border accent-accent"
            />
            <label htmlFor="tagDefault" className="text-sm font-medium">默认选中</label>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">状态</label>
            <Select
              value={tagForm.status}
              onChange={(v) => setTagForm({ ...tagForm, status: v })}
              options={[
                { value: "active", label: "active" },
                { value: "inactive", label: "inactive" },
              ]}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setTagModalOpen(false)}>
              取消
            </Button>
            <Button type="submit">保存</Button>
          </div>
        </form>
      </Modal>

      {/* Custom Group View Modal */}
      <Modal open={!!viewingCustomGroup} onClose={() => setViewingCustomGroup(null)} title={viewingCustomGroup ? viewingCustomGroup.group_name : "标签详情"} maxWidth="max-w-md">
        {viewingCustomGroup && (
          <div className="space-y-3">
            <p className="text-sm text-stone-500">包含 {viewingCustomGroup.tag_ids.length} 个标签：</p>
            <div className="flex flex-wrap gap-2">
              {getTagNamesByIds(viewingCustomGroup.tag_ids).map((name, i) => (
                <span key={i} className="rounded-full bg-stone-100 px-3 py-1 text-sm text-stone-600">
                  {name}
                </span>
              ))}
            </div>
            {viewingCustomGroup.tag_ids.length === 0 && (
              <p className="text-sm text-stone-400">暂无标签</p>
            )}
            <div className="flex justify-end pt-2">
              <Button variant="secondary" onClick={() => setViewingCustomGroup(null)}>
                关闭
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Custom Group Edit/Create Modal */}
      <Modal open={customGroupModalOpen} onClose={() => setCustomGroupModalOpen(false)} title={editingCustomGroup ? "编辑自定义标签组" : "新增自定义标签组"} maxWidth="max-w-lg">
        <form onSubmit={submitCustomGroup} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">所属企业</label>
            <Select
              required
              value={customGroupForm.company_id}
              onChange={(v) =>
                setCustomGroupForm({
                  ...customGroupForm,
                  company_id: v,
                  user_id: "",
                })
              }
              placeholder="选择企业"
              options={companyOptions}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">所属用户</label>
            <Select
              required
              value={customGroupForm.user_id}
              onChange={(v) => setCustomGroupForm({ ...customGroupForm, user_id: v })}
              placeholder={customGroupForm.company_id ? "选择用户" : "请先选择企业"}
              disabled={!customGroupForm.company_id}
              options={userOptionsForCustom}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">所属素材库</label>
            <Select
              required
              value={customGroupForm.asset_library_id}
              onChange={(v) =>
                setCustomGroupForm({
                  ...customGroupForm,
                  asset_library_id: v,
                  tag_ids: [],
                })
              }
              placeholder="选择素材库"
              options={libraryOptions}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">组名称</label>
            <Input required value={customGroupForm.group_name} onChange={(e) => setCustomGroupForm({ ...customGroupForm, group_name: e.target.value })} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">描述</label>
            <textarea
              className="min-h-20 w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm text-foreground outline-none transition placeholder:text-stone-400 focus:border-accent focus:ring-2 focus:ring-accent/20"
              value={customGroupForm.description}
              onChange={(e) => setCustomGroupForm({ ...customGroupForm, description: e.target.value })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">状态</label>
            <Select
              value={customGroupForm.status}
              onChange={(v) => setCustomGroupForm({ ...customGroupForm, status: v })}
              options={[
                { value: "active", label: "active" },
                { value: "inactive", label: "inactive" },
              ]}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">
              选择标签 {customGroupForm.asset_library_id ? "" : "（请先选择素材库）"}
            </label>
            <div className="max-h-40 overflow-y-auto rounded-2xl border border-border bg-white p-3">
              {availableTagsForCustom.length > 0 ? (
                <div className="grid grid-cols-2 gap-2">
                  {availableTagsForCustom.map((t) => (
                    <label key={t.tag_id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={customGroupForm.tag_ids.includes(t.tag_id)}
                        onChange={(e) => {
                          const next = e.target.checked
                            ? [...customGroupForm.tag_ids, t.tag_id]
                            : customGroupForm.tag_ids.filter((id) => id !== t.tag_id);
                          setCustomGroupForm({ ...customGroupForm, tag_ids: next });
                        }}
                        className="h-4 w-4 rounded border-border accent-accent"
                      />
                      <span className="truncate">{t.tag_name}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-stone-400 py-2">
                  {customGroupForm.asset_library_id ? "该素材库下暂无标签" : "请先选择素材库"}
                </p>
              )}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setCustomGroupModalOpen(false)}>
              取消
            </Button>
            <Button type="submit">保存</Button>
          </div>
        </form>
      </Modal>
    </main>
  );
}
