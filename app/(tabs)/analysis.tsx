// app/(tabs)/analysis.tsx

import React from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { AppTheme, useTheme } from "../../_theme";
import HorizontalStackedBarChart from "../hooks/graph";
import { PieChartTest } from "../hooks/piechart";
import RecentPurchases from "../hooks/purchases";
import SpendingChart from "../hooks/spending";

export default function AnalysisScreen() {
  const { theme } = useTheme();
  const styles = createStyles(theme);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.header}>Your Spending Analysis</Text>

        {/* Monthly/Category Mix (stacked bar) */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Budget Progress</Text>
          <HorizontalStackedBarChart />
        </View>

        {/* Trend over time */}
        <View style={styles.card}>
          <SpendingChart />
        </View>

        {/* Category split */}
        <View style={styles.card}>
          <PieChartTest />
        </View>

        {/* Recent transactions */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Most Recent Transactions</Text>
          <RecentPurchases maxVisible={5} compact />
        </View>

        {/* Gentle nudge */}
        <View style={styles.noteCard}>
          <Text style={styles.noteText}>
            Use this screen to reflect on habits and spot places to save. Tap a
            category for details in future versions.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const BG_FALLBACK = "#f2f2f2";
const CARD_FALLBACK = "#ffffff";
const TEXT_FALLBACK = "#222222";
const SUBTLE_FALLBACK = "#666666";

function createStyles(theme: AppTheme) {
  const bg = theme?.background ?? BG_FALLBACK;
  const card = theme?.card ?? CARD_FALLBACK;
  const text = theme?.text ?? TEXT_FALLBACK;
  const subtle = theme?.subtleText ?? SUBTLE_FALLBACK;

  return StyleSheet.create({
    safe: { flex: 1, backgroundColor: bg },
    container: { padding: 16, gap: 16 },
    header: {
      fontSize: 28,
      fontWeight: "800",
      color: text,
      textAlign: "center",
      marginBottom: 4,
    },
    card: {
      backgroundColor: card,
      borderRadius: 20,
      padding: 16,
      shadowColor: "#000",
      shadowOpacity: 0.08,
      shadowOffset: { width: 0, height: 4 },
      shadowRadius: 10,
      elevation: 3,
    },
    cardTitle: {
      fontSize: 18,
      fontWeight: "700",
      color: text,
      marginBottom: 10,
    },
    noteCard: {
      backgroundColor: card,
      borderRadius: 20,
      padding: 16,
      borderWidth: 1,
      borderColor: "#e6e6e6",
    },
    noteText: { color: subtle, fontSize: 14, lineHeight: 20 },
  });
}
