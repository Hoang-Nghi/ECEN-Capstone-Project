// app/(tabs)/games/index.tsx
import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect } from "@react-navigation/native";
import { useRouter } from "expo-router";
import { getAuth } from "firebase/auth";
import React, { useCallback, useMemo, useState } from "react";
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { AppTheme, useTheme } from "../../../_theme";

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  "https://capstone-backend-1041336188288.us-central1.run.app";

/** Get Firebase ID token (or null if not signed in) */
async function getFirebaseIdToken(): Promise<string | null> {
  try {
    const auth = getAuth();
    const user = auth.currentUser;
    if (!user) return null;
    return await user.getIdToken();
  } catch (e) {
    console.warn("[GamesHome] Failed to get Firebase ID token:", e);
    return null;
  }
}

/** XP hook – loads from /api/minigame/profile and refreshes on focus */
const useXP = () => {
  const [xp, setXp] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);

  const loadProfile = useCallback(async () => {
    try {
      setLoading(true);
      const token = await getFirebaseIdToken();
      const res = await fetch(`${BASE_URL}/api/minigame/profile`, {
        headers: {
          Accept: "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      const text = await res.text();
      if (!text) {
        setXp(0);
        return;
      }

      const data = JSON.parse(text) as {
        total_xp?: number;
      };

      if (!res.ok) {
        throw new Error(`Failed to load profile: ${res.status}`);
      }

      setXp(data.total_xp ?? 0);
    } catch (e) {
      console.warn("[GamesHome] Failed to load XP profile:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  // Refresh XP every time the Games tab comes into focus
  useFocusEffect(
    useCallback(() => {
      loadProfile();
    }, [loadProfile])
  );

  return { xp, loading, reload: loadProfile };
};

export default function GamesHome() {
  const router = useRouter();
  const { xp } = useXP();
  const { theme } = useTheme();
  const styles = createStyles(theme);

  // 6 unified ranks from backend
  const tiers = useMemo(
    () => [
      { key: "Penny Pincher", min: 0, color: "#B87333" }, // copper
      { key: "Savvy Saver", min: 500, color: "#CD7F32" }, // bronze
      { key: "Budget Master", min: 1500, color: "#C0C0C0" }, // silver
      { key: "Portfolio Pro", min: 3500, color: "#FFD700" }, // gold
      { key: "Investment Expert", min: 7000, color: "#E5E4E2" }, // platinum
      { key: "Finance Legend", min: 12000, color: "#B9F2FF" }, // diamond
    ],
    []
  );

  const currentTierIndex =
    [...tiers].reverse().findIndex((t) => xp >= t.min) >= 0
      ? tiers.length - 1 - [...tiers].reverse().findIndex((t) => xp >= t.min)
      : 0;

  const currentTier = tiers[currentTierIndex];
  const nextTier = tiers[currentTierIndex + 1];
  const toNext = nextTier ? Math.max(0, nextTier.min - xp) : 0;

  const tierStart = currentTier.min;
  const tierEnd = nextTier ? nextTier.min : Math.max(tierStart + 1, xp);
  const tierProgress = (xp - tierStart) / Math.max(1, tierEnd - tierStart);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.header}>Games</Text>

        {/* XP BADGES – 6 ranks, all fit across top */}

        <View style={styles.badgesRow}>
          {tiers.map((t) => {
            const achieved = xp >= t.min;
            return (
              <View key={t.key} style={styles.badgeWrap}>
                <View
                  style={[
                    styles.badge,
                    { borderColor: achieved ? t.color : theme.subtleText + "55" },
                    achieved && { backgroundColor: theme.card },
                  ]}
                >
                  <Ionicons
                    name={achieved ? "trophy" : "trophy-outline"}
                    size={20}
                    color={achieved ? t.color : theme.subtleText}
                  />
                </View>
                <Text
                  style={[
                    styles.badgeLabel,
                    achieved && { color: theme.text, fontWeight: "600" },
                  ]}
                  numberOfLines={2}
                >
                  {t.key}
                </Text>
              </View>
            );
          })}
        </View>

        {/* XP CARD */}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>
            XP: <Text style={styles.bold}>{xp}</Text>
          </Text>

          <View style={styles.progressTrack}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${Math.max(0, Math.min(1, tierProgress)) * 100}%`,
                  backgroundColor: currentTier.color,
                },
              ]}
            />
          </View>

          <Text style={styles.progressText}>
            {nextTier
              ? `Current: ${currentTier.key}. ${toNext} XP to ${nextTier.key}.`
              : `Max rank reached: ${currentTier.key}!`}
          </Text>
        </View>

        {/* GAMES GRID */}

        <View style={styles.grid}>
          {/* Smart Saver Quiz */}
          <Pressable
            style={styles.tile}
            onPress={() => router.push("/games/trivia")}
          >
            <View style={styles.tileIcon}>
              <Ionicons name="help-buoy" size={28} color={theme.accent} />
            </View>
            <Text style={styles.tileTitle}>Smart Saver Quiz</Text>
            <Text style={styles.tileDesc}>
              Guess past spending + quick tips. 5 questions, 4 choices.
            </Text>
          </Pressable>

          {/* Financial Categories */}
          <Pressable
            style={styles.tile}
            onPress={() => router.push("/games/connections")}
          >
            <View style={styles.tileIcon}>
              <Ionicons name="calendar" size={28} color={theme.accent} />
            </View>
            <Text style={styles.tileTitle}>Financial Categories</Text>
            <Text style={styles.tileDesc}>
              “Don’t spend over __ on __ this week.” Track progress & earn XP.
            </Text>
          </Pressable>

          {/* Spend Detective */}
          <Pressable
            style={styles.tile}
            onPress={() => router.push("/games/spend-detective")}
          >
            <View style={styles.tileIcon}>
              <Ionicons name="search" size={28} color={theme.accent} />
            </View>
            <Text style={styles.tileTitle}>Spend Detective</Text>
            <Text style={styles.tileDesc}>
              Find unusual transactions. 3 tries. +20 XP per catch.
            </Text>
          </Pressable>

          {/* Coming Soon */}
          <View style={[styles.tile, styles.tileDisabled]}>
            <View style={styles.tileIcon}>
              <Ionicons name="hourglass" size={28} color={theme.subtleText} />
            </View>
            <Text style={styles.tileTitle}>Coming Soon</Text>
            <Text style={styles.tileDesc}>
              A fourth game unlocks here. Stay tuned!
            </Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

//
// THEMED STYLES
//
function createStyles(theme: AppTheme) {
  return StyleSheet.create({
    safe: { flex: 1, backgroundColor: theme.background },
    container: { padding: 16 },
    header: {
      fontSize: 28,
      fontWeight: "800",
      color: theme.text,
      textAlign: "center",
      marginBottom: 12,
    },

    // 6 badges, even spacing including edges
    badgesRow: {
      flexDirection: "row",
      justifyContent: "space-evenly",
      alignItems: "center",
      marginBottom: 12,
    },
    badgeWrap: {
      alignItems: "center",
      flex: 1,
      paddingHorizontal: 2,
    },
    badge: {
      width: 44,
      height: 44,
      borderRadius: 999,
      backgroundColor: theme.card,
      borderWidth: 2,
      alignItems: "center",
      justifyContent: "center",
      shadowColor: "#000",
      shadowOpacity: 0.06,
      shadowOffset: { width: 0, height: 2 },
      shadowRadius: 4,
      elevation: 2,
    },
    badgeLabel: {
      marginTop: 4,
      fontSize: 10,
      lineHeight: 12,
      color: theme.subtleText,
      textAlign: "center",
    },

    card: {
      backgroundColor: theme.card,
      borderRadius: 20,
      padding: 16,
      marginBottom: 16,
      shadowColor: "#000",
      shadowOpacity: 0.08,
      shadowOffset: { width: 0, height: 4 },
      shadowRadius: 10,
      elevation: 3,
    },
    cardTitle: {
      fontSize: 18,
      fontWeight: "700",
      color: theme.text,
      marginBottom: 10,
    },

    progressTrack: {
      height: 10,
      backgroundColor: theme.subtleText + "22",
      borderRadius: 999,
      overflow: "hidden",
    },
    progressFill: {
      height: "100%",
      borderRadius: 999,
    },
    progressText: {
      marginTop: 8,
      color: theme.subtleText,
      fontSize: 13,
    },

    grid: {
      gap: 12,
    },
    tile: {
      backgroundColor: theme.card,
      borderRadius: 20,
      padding: 16,
      shadowColor: "#000",
      shadowOpacity: 0.08,
      shadowOffset: { width: 0, height: 3 },
      shadowRadius: 8,
      elevation: 3,
    },
    tileDisabled: {
      opacity: 0.5,
    },
    tileIcon: {
      width: 48,
      height: 48,
      borderRadius: 12,
      backgroundColor: theme.accent + "22",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 10,
    },
    tileTitle: {
      fontSize: 16,
      fontWeight: "700",
      color: theme.text,
      marginBottom: 4,
    },
    tileDesc: {
      fontSize: 13,
      color: theme.subtleText,
      lineHeight: 18,
    },
    bold: { fontWeight: "800" },
  });
}
