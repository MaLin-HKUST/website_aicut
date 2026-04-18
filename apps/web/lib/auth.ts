export type SessionUser = {
  id: number;
  username: string;
  role: "admin" | "user";
  company_id: number | null;
  company_name: string | null;
};

export type AuthResponse = {
  user: SessionUser;
};
