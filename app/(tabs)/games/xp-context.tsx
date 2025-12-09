// app/(tabs)/games/xp-context.tsx
import { getAuth } from "firebase/auth";
import React, {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useState,
} from "react";

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  "https://capstone-backend-1041336188288.us-central1.run.app";

const PROFILE_URL = `${BASE_URL}/api/minigame/profile`;

type Rank = {
  name: string;
  color: string;
  tier?: string;
  progress?: number;       // 0–1 between this rank and next
  xp_for_next_rank?: number;
};

type NextRank = {
  name: string;
  xp_needed: number;
};

export type XPProfile = {
  total_xp: number;
  level: number;
  rank: Rank;
  next_rank?: NextRank;
  games_played?: number;
};

type XPContextValue = {
  profile: XPProfile | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const XPContext = createContext<XPContextValue | undefined>(undefined);

async function getFirebaseIdToken(): Promise<string | null> {
  try {
    const auth = getAuth();
    const user = auth.currentUser;
    if (!user) return null;
    return await user.getIdToken();
  } catch {
    return null;
  }
}

export const XPProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [profile, setProfile] = useState<XPProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = await getFirebaseIdToken();
      if (!token) {
        setProfile(null);
        return;
      }

      const res = await fetch(PROFILE_URL, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const text = await res.text();
      const json = text ? JSON.parse(text) : null;

      if (!res.ok) {
        throw new Error(
          json?.error || json?.message || `HTTP ${res.status} ${res.statusText}`
        );
      }

      setProfile(json as XPProfile);
    } catch (e: any) {
      console.error("[XPProvider] Failed to load profile:", e);
      setError(e?.message || "Failed to load XP profile");
    } finally {
      setLoading(false);
    }
  }, []);

  // Load once when Games stack mounts
  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <XPContext.Provider value={{ profile, loading, error, refresh }}>
      {children}
    </XPContext.Provider>
  );
};

export function useXP() {
  const ctx = useContext(XPContext);
  if (!ctx) {
    throw new Error("useXP must be used within an <XPProvider> inside Games stack.");
  }
  return ctx;
}
