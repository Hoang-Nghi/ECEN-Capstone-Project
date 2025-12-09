// app/(tabs)/games/connections.tsx — backend-linked UI, styled like the test page
import { getAuth } from "firebase/auth";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  LayoutAnimation,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  UIManager,
  View,
} from "react-native";
import { AppTheme, useTheme } from "../../../_theme";

if (Platform.OS === "android" && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  "https://capstone-backend-1041336188288.us-central1.run.app";

const START_URL = `${BASE_URL}/api/minigame/financial-categories/start`;
const SUBMIT_URL = `${BASE_URL}/api/minigame/financial-categories/match`;

// ----------------------------- Types -----------------------------
type TileCategory = { id: string; label: string; category?: string };
type TileAmount = { id: string; label: string; value?: number };

type StartPlayable = {
  ok: true;
  can_play: true;
  round_id: string;
  tries_remaining: number;
  category_tiles?: TileCategory[];
  amount_tiles?: (TileAmount | string)[];
  categories?: string[];
};
type StartLow = {
  ok: true;
  can_play: false;
  message?: string;
  xp_awarded?: number;
  total_xp?: number;
  level?: number;
  streak?: number;
};
type StartResp = StartPlayable | StartLow;

type SubmitResp = {
  ok: boolean;
  correct?: boolean;
  tries_remaining?: number;
  round_complete?: boolean;
  xp_earned?: number;
  total_xp?: number;
  level?: number;
  streak?: number;
  accuracy?: number;
  reveal?: { category: string; amount: number; label: string }[];
  all_correct?: boolean;
  error?: string;
};

// ---------------------------- Helpers ----------------------------
async function getFirebaseIdToken(): Promise<string | null> {
  try {
    const u = getAuth().currentUser;
    return u ? await u.getIdToken() : null;
  } catch {
    return null;
  }
}

// Normalize backend payload to 5×2 board
function normalizePlayable(s: StartPlayable) {
  const cats: TileCategory[] = Array.isArray(s.category_tiles)
    ? s.category_tiles
    : (s.categories || []).map((c, i) => ({
        id: `cat_${i}`,
        label: String(c).replace(/\b\w/g, (m) => m.toUpperCase()),
        category: String(c),
      }));

  const amts: TileAmount[] = Array.isArray(s.amount_tiles)
    ? s.amount_tiles.map((a, i) =>
        typeof a === "string"
          ? ({
              id: `amt_${i}`,
              label: a,
              value: Number(a.replace(/[^0-9.\-]/g, "")) || 0,
            } as TileAmount)
          : (a as TileAmount)
      )
    : [];

  return { cats: cats.slice(0, 5), amts: amts.slice(0, 5) };
}

// fallback palette (used if theme doesn't supply something)
const BG = "#f2f2f2";
const CARD = "#fff";
const TEXT = "#222";
const SUBTLE = "#666";
const ACCENT = "#00b140";
const BORDER = "#1f2937";
const DARK = "#111827";
const GREEN = "#16a34a";
const RED = "#ef4444";

// ---------------------------- Screen ----------------------------
export default function Connections() {
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);

  // Data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lowMsg, setLowMsg] = useState<string | null>(null);
  const [tries, setTries] = useState(3);
  const [canPlay, setCanPlay] = useState(false);
  const [roundId, setRoundId] = useState<string | null>(null);

  const [categories, setCategories] = useState<TileCategory[]>([]);
  const [amounts, setAmounts] = useState<TileAmount[]>([]);

  // Selection + visual feedback (to mimic the test UI)
  const [selCatId, setSelCatId] = useState<string | null>(null);
  const [selAmtId, setSelAmtId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<"correct" | "wrong" | null>(null);

  // Solved “pills” (in order solved)
  type Pair = { cat: TileCategory; amt: TileAmount };
  const [solved, setSolved] = useState<Pair[]>([]);

  // Completion & final reveal/stats
  const [completed, setCompleted] = useState(false);
  const [reveal, setReveal] = useState<SubmitResp["reveal"] | null>(null);
  const [finalStats, setFinalStats] = useState<{
    xp?: number;
    level?: number;
    streak?: number;
    accuracy?: number;
  } | null>(null);

  const solvedCount = solved.length;
  const total = 5;
  const done = completed || tries <= 0;

  const startRound = useCallback(async () => {
    setLoading(true);
    setError(null);
    setLowMsg(null);
    setReveal(null);
    setFinalStats(null);
    setCompleted(false);
    setSelCatId(null);
    setSelAmtId(null);
    setFeedback(null);
    setSolved([]);

    try {
      const token = await getFirebaseIdToken();
      const res = await fetch(START_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      const json: StartResp = await res.json();
      if (!(json as any)?.ok)
        throw new Error((json as any)?.error || "Unexpected response");

      if ((json as StartLow).can_play === false) {
        const low = json as StartLow;
        setCanPlay(false);
        setLowMsg(
          low.message ||
            "You received XP for a low-spend period. Come back soon!"
        );
        setTries(0);
        setCategories([]);
        setAmounts([]);
        setRoundId(null);
      } else {
        const playable = json as StartPlayable;
        const { cats, amts } = normalizePlayable(playable);
        setCanPlay(true);
        setTries(playable.tries_remaining ?? 3);
        setRoundId(playable.round_id);
        setCategories(cats);
        setAmounts(amts);
      }
    } catch (e: any) {
      setError(e?.message || "Failed to start round.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    startRound();
  }, [startRound]);

  const catMap = useMemo(
    () => Object.fromEntries(categories.map((c) => [c.id, c])),
    [categories]
  );
  const amtMap = useMemo(
    () => Object.fromEntries(amounts.map((a) => [a.id, a])),
    [amounts]
  );

  const unsolvedCategories = useMemo(
    () => categories.filter((c) => !solved.some((p) => p.cat.id === c.id)),
    [categories, solved]
  );
  const unsolvedAmounts = useMemo(
    () => amounts.filter((a) => !solved.some((p) => p.amt.id === a.id)),
    [amounts, solved]
  );

  const onCheck = useCallback(
    async () => {
      if (!selCatId || !selAmtId || feedback) return;
      try {
        const token = await getFirebaseIdToken();
        const resp = await fetch(SUBMIT_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            category_id: selCatId,
            amount_id: selAmtId,
            round_id: roundId || undefined,
          }),
        });
        const json: SubmitResp = await resp.json();

        if (typeof json.tries_remaining === "number")
          setTries(json.tries_remaining);

        if (!json.ok || !json.correct) {
          setFeedback("wrong");
          setTimeout(() => {
            setFeedback(null);
            setSelCatId(null);
            setSelAmtId(null);
          }, 600);
          return;
        }

        const cat = catMap[selCatId];
        const amt = amtMap[selAmtId];
        if (cat && amt) {
          LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
          setSolved((prev) => [...prev, { cat, amt }]);
        }
        setFeedback("correct");
        setTimeout(() => {
          setFeedback(null);
          setSelCatId(null);
          setSelAmtId(null);
        }, 450);

        const nowSolved = solvedCount + 1;
        const reachedAll = nowSolved >= total;
        if (json.round_complete || reachedAll) {
          setCompleted(true);
          if (json.round_complete) {
            setReveal(json.reveal || null);
            setFinalStats({
              xp: json.xp_earned,
              level: json.level,
              streak: json.streak,
              accuracy: json.accuracy,
            });
          }
        }
      } catch (e: any) {
        Alert.alert("Error", e?.message || "Could not submit match.");
      }
    },
    [selCatId, selAmtId, roundId, feedback, catMap, amtMap, solvedCount]
  );

  const progressPct = useMemo(
    () => Math.round((solvedCount / total) * 100),
    [solvedCount]
  );

  const Tile = ({
    id,
    label,
    selected,
    state,
    onPress,
  }: {
    id: string;
    label: string;
    selected?: boolean;
    state?: "correct" | "wrong" | "default";
    onPress?: () => void;
  }) => {
    const rightSel = state === "correct" && selected;
    const wrongSel = state === "wrong" && selected;
    return (
      <Pressable
        onPress={onPress}
        style={[
          styles.tile,
          selected && styles.tileSelected,
          rightSel && styles.tileCorrect,
          wrongSel && styles.tileWrong,
        ]}
      >
        <Text
          style={[
            styles.tileText,
            selected && styles.tileTextSelected,
            rightSel && styles.tileTextCorrect,
            wrongSel && styles.tileTextWrong,
          ]}
        >
          {label}
        </Text>
      </Pressable>
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.header}>Financial Categories</Text>

        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: `${progressPct}%` }]} />
        </View>
        <Text style={styles.meta}>
          Solved {solvedCount}/{total} • Tries left {tries}
        </Text>

        {loading && (
          <View style={[styles.card, styles.center, styles.cardTall]}>
            <ActivityIndicator size="large" color={styles.accentColor} />
            <Text style={styles.bodyText}>Loading…</Text>
          </View>
        )}

        {!!error && !loading && (
          <View style={[styles.card, styles.center]}>
            <Text style={styles.errorText}>❌ {error}</Text>
            <Pressable style={styles.primaryBtn} onPress={startRound}>
              <Text style={styles.primaryBtnText}>Try Again</Text>
            </Pressable>
          </View>
        )}

        {!loading && !error && lowMsg && (
          <View style={[styles.card, styles.center]}>
            <Text style={styles.resultTitle}>🌟</Text>
            <Text style={styles.muted}>{lowMsg}</Text>
            <Pressable
              style={[styles.primaryBtn, { marginTop: 12 }]}
              onPress={startRound}
            >
              <Text style={styles.primaryBtnText}>Check Again</Text>
            </Pressable>
          </View>
        )}

        {!loading && !error && canPlay && (
          <View style={[styles.card, styles.cardTall, styles.cardWithBottomClear]}>
            <ScrollView
              contentContainerStyle={{ paddingBottom: 96 }}
              keyboardShouldPersistTaps="handled"
            >
              {!!solved.length && (
                <View style={{ marginBottom: 10 }}>
                  <Text style={styles.solvedTitle}>Solved</Text>
                  {solved.map((p, idx) => (
                    <View
                      key={`solv-${p.cat.id}-${idx}`}
                      style={styles.solvedRow}
                    >
                      <Text style={[styles.solvedPill, styles.solvedLeft]}>
                        {p.cat.label}
                      </Text>
                      <Text style={[styles.solvedPill, styles.solvedRight]}>
                        {p.amt.label}
                      </Text>
                    </View>
                  ))}
                </View>
              )}

              {!done ? (
                <View style={styles.columns}>
                  <View style={styles.col}>
                    <Text style={styles.colTitle}>Category</Text>
                    {unsolvedCategories.map((c) => {
                      const selected = selCatId === c.id;
                      return (
                        <Tile
                          key={c.id}
                          id={c.id}
                          label={c.label}
                          selected={selected}
                          state={feedback || "default"}
                          onPress={() =>
                            setSelCatId((s) => (s === c.id ? null : c.id))
                          }
                        />
                      );
                    })}
                  </View>

                  <View style={styles.col}>
                    <Text style={styles.colTitle}>Amount</Text>
                    {unsolvedAmounts.map((a) => {
                      const selected = selAmtId === a.id;
                      return (
                        <Tile
                          key={a.id}
                          id={a.id}
                          label={a.label}
                          selected={selected}
                          state={feedback || "default"}
                          onPress={() =>
                            setSelAmtId((s) => (s === a.id ? null : a.id))
                          }
                        />
                      );
                    })}
                  </View>
                </View>
              ) : (
                <View
                  style={{
                    flex: 1,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Text style={styles.endTitle}>
                    {solvedCount === total
                      ? "🎉 Great matching!"
                      : "📚 Out of tries"}
                  </Text>
                  <Text style={styles.endSub}>
                    {solvedCount === total
                      ? "Nice! All categories matched."
                      : `You solved ${solvedCount} of ${total}.`}
                  </Text>
                </View>
              )}

              {done && Array.isArray(reveal) && reveal.length > 0 && (
                <View style={[styles.card, { padding: 0, marginTop: 12 }]}>
                  {reveal.map((r, i) => (
                    <View
                      key={`${r.category}-${i}`}
                      style={[
                        styles.groupRow,
                        i > 0 && styles.groupRowDivider,
                      ]}
                    >
                      <Text style={styles.groupCat}>{r.category}</Text>
                      <Text style={styles.groupAmt}>{r.label}</Text>
                    </View>
                  ))}
                </View>
              )}
            </ScrollView>

            {!done ? (
              <View style={{ marginTop: 6 }}>
                <Pressable
                  onPress={onCheck}
                  disabled={!selCatId || !selAmtId}
                  style={[
                    styles.primaryBtn,
                    (!selCatId || !selAmtId) && styles.primaryBtnDisabled,
                  ]}
                >
                  <Text style={styles.primaryBtnText}>Check</Text>
                </Pressable>
                <Pressable onPress={startRound} style={styles.secondaryBtn}>
                  <Text style={styles.secondaryBtnText}>
                    Shuffle / Restart
                  </Text>
                </Pressable>
              </View>
            ) : (
              <Pressable
                onPress={startRound}
                style={[styles.primaryBtn, { marginTop: 8 }]}
              >
                <Text style={styles.primaryBtnText}>Play Again</Text>
              </Pressable>
            )}

            {done && !!finalStats && (
              <Text style={[styles.muted, { textAlign: "center", marginTop: 8 }]}>
                {typeof finalStats.accuracy === "number"
                  ? `Accuracy ${Math.round(
                      finalStats.accuracy * 100
                    )}% • `
                  : ""}
                XP +{finalStats.xp ?? 0}
                {typeof finalStats.level === "number"
                  ? ` • LV ${finalStats.level}`
                  : ""}
                {typeof finalStats.streak === "number"
                  ? ` • Streak ${finalStats.streak}`
                  : ""}
              </Text>
            )}
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}

// ---------------------------- Styles ----------------------------
function createStyles(theme: AppTheme) {
  const bg = theme?.background ?? BG;
  const card = theme?.card ?? CARD;
  const text = theme?.text ?? TEXT;
  const subtle = theme?.subtleText ?? SUBTLE;
  const accent = theme?.accent ?? ACCENT;

  return StyleSheet.create({
    // small helper to expose accent to ActivityIndicator
    accentColor: accent as any,

    safe: { flex: 1, backgroundColor: bg },
    container: { flex: 1, paddingHorizontal: 18, paddingTop: 8, alignItems: "center" },

    header: {
      fontSize: 24,
      fontWeight: "800",
      marginVertical: 12,
      textAlign: "center",
      color: text,
    },

    progressTrack: {
      width: "100%",
      height: 8,
      backgroundColor: "#e5e7eb",
      borderRadius: 999,
      overflow: "hidden",
    },
    progressFill: { height: "100%", backgroundColor: accent },
    meta: {
      marginTop: 6,
      marginBottom: 10,
      color: subtle,
      fontSize: 13,
      fontWeight: "600",
    },

    card: {
      width: "100%",
      backgroundColor: card,
      borderRadius: 20,
      padding: 16,
      borderWidth: 1,
      borderColor: BORDER,
    },
    cardTall: { flex: 1, alignSelf: "stretch" },
    cardWithBottomClear: { marginBottom: 10 },

    center: { alignItems: "center", justifyContent: "center", paddingVertical: 24 },
    errorText: {
      color: "crimson",
      marginBottom: 12,
      fontWeight: "600",
      textAlign: "center",
    },
    muted: { color: subtle },

    solvedTitle: { fontWeight: "800", color: text, marginBottom: 8, fontSize: 16 },
    solvedRow: { flexDirection: "row", gap: 10, marginBottom: 8 },
    solvedPill: {
      flex: 1,
      borderRadius: 12,
      paddingVertical: 10,
      paddingHorizontal: 12,
      fontWeight: "700",
      overflow: "hidden",
    },
    solvedLeft: { backgroundColor: "#eefaf2", color: "#0a7d36" } as any,
    solvedRight: { backgroundColor: "#f3f4f6", color: "#111827" } as any,

    columns: { flexDirection: "row", gap: 12, flex: 1 },
    col: { flex: 1 },
    colTitle: {
      fontSize: 14,
      color: subtle,
      fontWeight: "700",
      marginBottom: 6,
    },

    tile: {
      borderWidth: 1,
      borderColor: "#d9d9d9",
      borderRadius: 14,
      paddingVertical: 16,
      paddingHorizontal: 14,
      marginBottom: 10,
      minHeight: 56,
      justifyContent: "center",
      backgroundColor: "#fafafa",
    },
    tileSelected: { borderColor: accent, backgroundColor: "#eefaf2" },
    tileCorrect: { backgroundColor: "#e7f7ec", borderColor: GREEN },
    tileWrong: { backgroundColor: "#fff7f7", borderColor: RED },

    tileText: { fontSize: 16, fontWeight: "700", color: text },
    tileTextSelected: { color: "#0a7d36" },
    tileTextCorrect: { color: "#0a7d36" },
    tileTextWrong: { color: "#b91c1c" },

    endTitle: {
      fontSize: 22,
      fontWeight: "800",
      color: DARK,
      textAlign: "center",
      marginBottom: 6,
    },

    endSub: {
      fontSize: 16,
      color: "#555",
      textAlign: "center",
    },

    bodyText: {
      fontSize: 16,
      color: "#333",
      textAlign: "center",
      lineHeight: 22,
      fontWeight: "500",
    },

    primaryBtn: {
      marginTop: 8,
      backgroundColor: accent,
      borderRadius: 16,
      alignItems: "center",
      paddingVertical: 14,
    },
    primaryBtnDisabled: { opacity: 0.6 },
    primaryBtnText: { color: "#fff", fontWeight: "800", fontSize: 16 },

    secondaryBtn: {
      marginTop: 8,
      backgroundColor: DARK,
      borderRadius: 16,
      alignItems: "center",
      paddingVertical: 14,
    },
    secondaryBtnText: { color: "#fff", fontWeight: "800", fontSize: 16 },

    resultTitle: {
      fontSize: 22,
      fontWeight: "800",
      color: text,
      textAlign: "center",
      marginBottom: 6,
    },

    groupRow: {
      flexDirection: "row",
      justifyContent: "space-between",
      paddingHorizontal: 12,
      paddingVertical: 12,
    },
    groupRowDivider: {
      borderTopColor: "#e5e7eb",
      borderTopWidth: StyleSheet.hairlineWidth,
    },
    groupCat: { color: "#0a7d36", fontWeight: "700" },
    groupAmt: { color: "#b45309", fontWeight: "700" },
  });
}
