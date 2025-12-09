// app/(tabs)/games/spend-detective.tsx
// Updated to finish round when last anomaly is found (2–4 per round)
// Backend contract: /api/minigame/spend-detective/start and /submit (or /guess fallback)

import { Ionicons } from "@expo/vector-icons";
import { getAuth } from "firebase/auth";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Alert,
  Animated,
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
import GifLoader from "../../../components/GifLoader";

if (Platform.OS === "android" && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  "https://capstone-backend-1041336188288.us-central1.run.app";

const START_URL = `${BASE_URL}/api/minigame/spend-detective/start`;
const GUESS_URLS = [
  `${BASE_URL}/api/minigame/spend-detective/guess`,
  `${BASE_URL}/api/minigame/spend-detective/submit`,
  `${BASE_URL}/api/minigame/spend-detective/submit-guess`,
];

type Tx = {
  id: string;
  date: string;
  merchant_name: string;
  amount: number | string;
  category: string;
  logo_url?: string;
};

async function getFirebaseIdToken(): Promise<string | null> {
  try {
    const u = getAuth().currentUser;
    return u ? await u.getIdToken() : null;
  } catch {
    return null;
  }
}

async function postJsonWithFallback<T>(
  urls: string[],
  body: any,
  token: string | null
): Promise<T> {
  let lastErr: any = null;
  for (const url of urls) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
      });
      const raw = await res.text();
      const data = raw ? JSON.parse(raw) : null;
      if (!res.ok) {
        if (res.status === 404) {
          lastErr = new Error(data?.error || `404 at ${url}`);
          continue;
        }
        throw new Error(data?.error || `HTTP ${res.status} ${res.statusText}`);
      }
      return data as T;
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr ?? new Error("No working endpoint for Spend Detective submit.");
}

const BG = "#f2f2f2";
const CARD = "#fff";
const TEXT = "#222";
const SUBTLE = "#666";
const ACCENT = "#00b140";
const BORDER = "#1f2937";

export default function SpendDetective() {
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [canPlay, setCanPlay] = useState(false);
  const [lowMsg, setLowMsg] = useState<string | null>(null);
  const [tries, setTries] = useState(3);
  const [transactions, setTransactions] = useState<Tx[]>([]);
  const [roundId, setRoundId] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [locked, setLocked] = useState<Record<string, boolean>>({});

  // Track totals from backend
  const [totalAnomalies, setTotalAnomalies] = useState<number | null>(null);
  const [totalCorrect, setTotalCorrect] = useState<number>(0);

  // Completed state / reveal & stats
  const [completed, setCompleted] = useState(false);
  const [reveal, setReveal] = useState<any[] | null>(null);
  const [finalStats, setFinalStats] = useState<any | null>(null);

  const badPulse = useRef(new Animated.Value(0)).current;
  const pulseWrong = () => {
    Animated.sequence([
      Animated.timing(badPulse, {
        toValue: 1,
        duration: 110,
        useNativeDriver: false,
      }),
      Animated.timing(badPulse, {
        toValue: 0,
        duration: 110,
        useNativeDriver: false,
      }),
    ]).start();
  };

  const startRound = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelectedId(null);
    setLocked({});
    setCompleted(false);
    setReveal(null);
    setFinalStats(null);
    setTotalAnomalies(null);
    setTotalCorrect(0);

    try {
      const token = await getFirebaseIdToken();
      const res = await fetch(START_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      const json = await res.json();

      if (!json?.ok) throw new Error(json?.error || "Unexpected response.");

      if (json.insufficient_data === true) {
        setCanPlay(false);
        setLowMsg(json.message || "Not enough data yet.");
        setTries(0);
        setTransactions([]);
        setRoundId(null);
        setFinalStats((s: any) => ({
          ...s,
          xp: json.xp_awarded ?? 0,
          level: json.level,
          streak: json.streak,
        }));
        return;
      }

      setCanPlay(true);
      setLowMsg(null);
      setTransactions(json.transactions ?? json.round ?? []);
      setRoundId(json.round_id ?? null);
      setTries(json.tries_remaining ?? 3);
    } catch (e: any) {
      setError(e?.message || "Failed to start round.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    startRound();
  }, [startRound]);

  const foundCount = useMemo(
    () =>
      typeof totalCorrect === "number"
        ? totalCorrect
        : Object.values(locked).filter(Boolean).length,
    [totalCorrect, locked]
  );
  const canSubmit = !!selectedId;

  const maybeFinishLocally = (
    j: any,
    nextCorrect: number,
    nextTotalAnoms: number | null
  ) => {
    if (j?.round_complete) return;
    if (nextTotalAnoms != null && nextCorrect >= nextTotalAnoms) {
      setReveal(j?.reveal ?? []);
      setFinalStats({
        xp: j?.xp_earned ?? nextCorrect * 20,
        total_xp: j?.total_xp,
        level: j?.level,
        streak: j?.streak,
        accuracy:
          j?.accuracy ??
          (nextTotalAnoms > 0
            ? +(nextCorrect / nextTotalAnoms).toFixed(2)
            : undefined),
        streak_maintained: j?.streak_maintained,
        summary: j?.summary,
      });
      setCompleted(true);
    }
  };

  const onSubmit = useCallback(
    async () => {
      if (!selectedId) return;
      try {
        const token = await getFirebaseIdToken();
        const json = await postJsonWithFallback<any>(
          GUESS_URLS,
          {
            round_id: roundId || undefined,
            selected_ids: [selectedId],
          },
          token
        );

        if (typeof json.tries_remaining === "number") {
          setTries((prev) => Math.min(prev, Number(json.tries_remaining)));
        }

        if (typeof json.total_correct === "number") {
          setTotalCorrect(json.total_correct);
        } else if (json.new_correct && json.new_correct > 0) {
          setTotalCorrect((prev) => prev + Number(json.new_correct));
        }

        if (typeof json.total_anomalies === "number") {
          setTotalAnomalies(Number(json.total_anomalies));
        }

        const wasCorrect = !!(json.new_correct && json.new_correct > 0);
        if (wasCorrect) {
          LayoutAnimation.configureNext?.(
            LayoutAnimation.Presets?.easeInEaseOut || {}
          );
          setLocked((prev) => ({ ...prev, [selectedId]: true }));
        } else {
          pulseWrong();
        }

        setSelectedId(null);

        if (json.round_complete) {
          setReveal(json.reveal || []);
          setFinalStats({
            xp: json.xp_earned,
            total_xp: json.total_xp,
            level: json.level,
            streak: json.streak,
            accuracy: json.accuracy,
            streak_maintained: json.streak_maintained,
            summary: json.summary,
            feedback: json.feedback,
          });
          setCompleted(true);
          return;
        }

        const nextCorrect =
          typeof json.total_correct === "number"
            ? Number(json.total_correct)
            : foundCount + (wasCorrect ? 1 : 0);

        const nextTotal =
          typeof json.total_anomalies === "number"
            ? Number(json.total_anomalies)
            : totalAnomalies;

        maybeFinishLocally(json, nextCorrect, nextTotal);
      } catch (e: any) {
        Alert.alert("Error", e?.message || "Could not submit guess.");
      }
    },
    [selectedId, roundId, foundCount, totalAnomalies]
  );

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.header}>Spend Detective</Text>
        <Text style={styles.subheader}>
          Tap ONE suspect, then Submit. Correct ones lock green.
        </Text>

        {loading && (
          <View style={styles.center}>
            <GifLoader />
            <Text style={styles.muted}>Loading round…</Text>
          </View>
        )}

        {!!error && !loading && (
          <View style={styles.center}>
            <Text style={styles.errorText}>❌ {error}</Text>
            <Pressable style={styles.primaryBtn} onPress={startRound}>
              <Text style={styles.primaryBtnText}>Try Again</Text>
            </Pressable>
          </View>
        )}

        {!loading && !error && lowMsg && (
          <View style={styles.card}>
            <Text style={styles.celebrate}>🌟</Text>
            <Text style={styles.bodyText}>{lowMsg}</Text>
            {!!finalStats?.xp && (
              <Text style={styles.muted}>
                We still awarded XP (+{finalStats.xp}).
              </Text>
            )}
            <Pressable
              style={[styles.primaryBtn, { marginTop: 12 }]}
              onPress={startRound}
            >
              <Text style={styles.primaryBtnText}>Check Again</Text>
            </Pressable>
          </View>
        )}

        {!loading && !error && canPlay && !completed && (
          <>
            <View style={styles.metaRow}>
              <View style={styles.pill}>
                <Text style={styles.pillText}>Tries: {tries}</Text>
              </View>
              <View style={styles.pill}>
                <Text style={styles.pillText}>
                  Found: {foundCount}
                  {totalAnomalies != null ? ` / ${totalAnomalies}` : ""}
                </Text>
              </View>
              {!!selectedId && (
                <View style={[styles.pill, { borderColor: "#00b140" }]}>
                  <Text
                    style={[styles.pillText, { color: "#00b140" }]}
                  >{`Selected: 1`}</Text>
                </View>
              )}
            </View>

            <ScrollView contentContainerStyle={{ paddingBottom: 96 }}>
              <View style={{ gap: 10 }}>
                {transactions.map((t) => {
                  const isLocked = !!locked[t.id];
                  const isSelected = selectedId === t.id;
                  return (
                    <Pressable
                      key={t.id}
                      onPress={() => {
                        if (!isLocked)
                          setSelectedId(isSelected ? null : t.id);
                      }}
                      style={[
                        styles.txCard,
                        isLocked && styles.txCardLocked,
                        isSelected && !isLocked && styles.txCardSelected,
                      ]}
                    >
                      <View style={styles.txRow}>
                        <View style={styles.iconWrap}>
                          <Ionicons
                            name={
                              isLocked
                                ? "checkmark-circle"
                                : isSelected
                                ? "alert-circle"
                                : "ellipse-outline"
                            }
                            size={22}
                            color={
                              isLocked
                                ? "#16a34a"
                                : isSelected
                                ? "#ef4444"
                                : "#00b140"
                            }
                          />
                        </View>
                        <View style={{ flex: 1 }}>
                          <Text
                            style={[
                              styles.txMerchant,
                              isLocked && { color: "#16a34a" },
                            ]}
                            numberOfLines={1}
                          >
                            {t.merchant_name}
                          </Text>
                          <Text style={styles.txSub} numberOfLines={1}>
                            {t.category} • {t.date}
                          </Text>
                        </View>
                        <Text
                          style={[
                            styles.txAmount,
                            isLocked && { color: "#16a34a" },
                          ]}
                        >
                          ${Number(t.amount).toFixed(2)}
                        </Text>
                      </View>
                    </Pressable>
                  );
                })}
              </View>
            </ScrollView>

            <View style={styles.footerBar}>
              <Animated.View
                style={[
                  styles.errorPulse,
                  {
                    opacity: badPulse.interpolate({
                      inputRange: [0, 1],
                      outputRange: [0, 0.9],
                    }),
                  },
                ]}
              />
              <Pressable
                style={[styles.secondaryBtn, !canSubmit && { opacity: 0.5 }]}
                disabled={!canSubmit}
                onPress={onSubmit}
              >
                <Text style={styles.secondaryBtnText}>Submit</Text>
              </Pressable>
              <Pressable style={styles.primaryBtn} onPress={startRound}>
                <Text style={styles.primaryBtnText}>New Round</Text>
              </Pressable>
            </View>
          </>
        )}

        {!loading && !error && completed && (
          <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
            <View style={styles.card}>
              <Text style={styles.resultTitle}>Completed!</Text>
              {finalStats && (
                <Text style={styles.muted}>
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

              {finalStats?.feedback && (
                <View
                  style={{
                    marginTop: 12,
                    backgroundColor: "#f0fdf4",
                    borderRadius: 12,
                    padding: 12,
                  }}
                >
                  <Text
                    style={{
                      color: "#14532d",
                      fontSize: 15,
                      textAlign: "center",
                    }}
                  >
                    💬 {finalStats.feedback}
                  </Text>
                </View>
              )}

              {finalStats?.summary && (
                <View style={{ marginTop: 12, gap: 6 }}>
                  <Text style={styles.summaryText}>
                    Correct: {finalStats.summary.correct}
                  </Text>
                  <Text style={styles.summaryText}>
                    Missed: {finalStats.summary.missed}
                  </Text>
                  <Text style={styles.summaryText}>
                    False positives: {finalStats.summary.false_positives}
                  </Text>
                </View>
              )}

              {Array.isArray(reveal) && reveal.length > 0 && (
                <View style={[styles.card, { padding: 0, marginTop: 12 }]}>
                  {reveal.map((r: any, i: number) => (
                    <View
                      key={i}
                      style={[
                        styles.revealRow,
                        i > 0 && styles.revealDivider,
                      ]}
                    >
                      <Ionicons
                        name={
                          r.found_by_user
                            ? "checkmark-circle"
                            : "alert-circle"
                        }
                        size={18}
                        color={r.found_by_user ? "#16a34a" : "#ef4444"}
                      />
                      <Text style={styles.revealText}>
                        {r.reasons && r.reasons.length
                          ? r.reasons.join(" • ")
                          : "Unusual pattern detected"}
                      </Text>
                    </View>
                  ))}
                </View>
              )}

              <Pressable
                style={[styles.primaryBtn, { marginTop: 12 }]}
                onPress={startRound}
              >
                <Text style={styles.primaryBtnText}>Play Again</Text>
              </Pressable>
            </View>
          </ScrollView>
        )}
      </View>
    </SafeAreaView>
  );
}

function createStyles(theme: AppTheme) {
  const bg = theme?.background ?? BG;
  const card = theme?.card ?? CARD;
  const text = theme?.text ?? TEXT;
  const subtle = theme?.subtleText ?? SUBTLE;
  const accent = theme?.accent ?? ACCENT;

  return StyleSheet.create({
    safe: { flex: 1, backgroundColor: bg },
    container: { flex: 1, padding: 16 },
    header: {
      fontSize: 28,
      fontWeight: "800",
      color: text,
      textAlign: "center",
    },
    subheader: {
      color: subtle,
      textAlign: "center",
      marginTop: 4,
      marginBottom: 8,
    },
    center: { alignItems: "center", justifyContent: "center", paddingVertical: 24 },
    muted: { color: subtle, marginTop: 6, textAlign: "center" },
    errorText: {
      color: "crimson",
      marginBottom: 12,
      fontWeight: "600",
      textAlign: "center",
    },
    celebrate: { fontSize: 42, textAlign: "center", marginBottom: 6 },
    bodyText: { color: text, fontSize: 16, textAlign: "center" },
    card: {
      backgroundColor: card,
      borderRadius: 16,
      padding: 16,
      borderWidth: 1,
      borderColor: BORDER,
    },

    metaRow: {
      flexDirection: "row",
      gap: 8,
      marginBottom: 8,
      alignItems: "center",
    },
    pill: {
      backgroundColor: card,
      borderRadius: 999,
      paddingVertical: 6,
      paddingHorizontal: 10,
      borderColor: BORDER,
      borderWidth: 1,
    },
    pillText: {
      color: subtle,
      fontSize: 12,
      fontWeight: "600",
      letterSpacing: 0.15,
    },

    txCard: {
      backgroundColor: card,
      borderColor: "#d9d9d9",
      borderWidth: 1,
      borderRadius: 14,
      padding: 12,
    },
    txCardSelected: { backgroundColor: "#fff7f7", borderColor: "#ef4444" },
    txCardLocked: { backgroundColor: "#e7f7ec", borderColor: "#16a34a" },
    txRow: { flexDirection: "row", alignItems: "center", gap: 10 },
    iconWrap: { width: 26, alignItems: "center" },
    txMerchant: { fontWeight: "800", color: text },
    txSub: { color: subtle, fontSize: 12 },
    txAmount: { fontWeight: "800", color: text },

    footerBar: {
      position: "absolute",
      left: 16,
      right: 16,
      bottom: 16,
      flexDirection: "row",
      gap: 12,
    },
    primaryBtn: {
      backgroundColor: accent,
      borderRadius: 14,
      alignItems: "center",
      paddingVertical: 12,
      paddingHorizontal: 16,
      flex: 1,
    },
    primaryBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
    secondaryBtn: {
      backgroundColor: "#111827",
      borderRadius: 14,
      alignItems: "center",
      paddingVertical: 12,
      paddingHorizontal: 16,
      flex: 1,
    },
    secondaryBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
    errorPulse: {
      position: "absolute",
      left: 0,
      right: 0,
      bottom: 0,
      top: 0,
      borderRadius: 14,
      backgroundColor: "#fee2e2",
      zIndex: -1,
    },

    revealRow: {
      flexDirection: "row",
      alignItems: "center",
      gap: 8,
      paddingHorizontal: 12,
      paddingVertical: 10,
    },
    revealDivider: {
      borderTopColor: "#e5e7eb",
      borderTopWidth: StyleSheet.hairlineWidth,
    },
    revealText: { color: text, flex: 1 },

    resultTitle: {
      fontSize: 22,
      fontWeight: "800",
      color: text,
      textAlign: "center",
      marginBottom: 6,
    },
    summaryText: { color: text, fontSize: 14 },
  });
}
