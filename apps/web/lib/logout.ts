export async function logoutUser(username?: string | null) {
  if (username) {
    try {
      await fetch("/api/proxy/api/smart-cut/tasks/draft/current/abandon-all", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_id: username }),
      });
    } catch {
      // Logout should remain available even if hidden-draft abandonment fails.
    }
  }

  await fetch("/api/proxy/auth/logout", { method: "POST" });
}
