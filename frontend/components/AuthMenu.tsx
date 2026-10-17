"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { getSupabase, migrateBrowserData } from "@/lib/supabase";

export default function AuthMenu() {
  const supabase = getSupabase();
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        migrateBrowserData(session.user.id)
          .then(() => window.dispatchEvent(new Event("culture-auth-changed")))
          .catch(() => setMessage("브라우저 저장값 이전에 실패했습니다. 잠시 후 다시 시도해 주세요."));
      } else window.dispatchEvent(new Event("culture-auth-changed"));
    });
    return () => data.subscription.unsubscribe();
  }, [supabase]);

  if (!supabase) return null;
  if (user) return <button className="authButton" onClick={() => supabase.auth.signOut()} title={user.email}>로그아웃</button>;

  return (
    <div className="authMenu">
      <button className="authButton" onClick={() => setOpen((value) => !value)}>로그인</button>
      {open && <form className="authPanel" onSubmit={async (event) => {
        event.preventDefault();
        setMessage("전송 중…");
        const { error } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.origin } });
        setMessage(error ? "로그인 메일을 보내지 못했습니다." : "이메일로 보낸 로그인 링크를 확인해 주세요.");
      }}>
        <strong>이메일로 로그인</strong>
        <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" aria-label="로그인 이메일" />
        <button type="submit">로그인 링크 받기</button>
        {message && <small>{message}</small>}
      </form>}
    </div>
  );
}
