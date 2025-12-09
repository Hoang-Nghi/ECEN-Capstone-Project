// hooks/spending.tsx
import React, { useEffect, useState } from 'react';
import {
  Dimensions,
  StyleSheet,
  Text,
  TouchableOpacity,
  View
} from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import GifLoader from '../../components/GifLoader';
import { useAuth } from './useAuth';

const screenWidth = Dimensions.get('window').width;
const baseChartWidth = screenWidth - 32;
const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  'https://capstone-backend-1041336188288.us-central1.run.app';

type ViewOpt = 'Day' | 'Week' | 'Month';
const viewOptions: ViewOpt[] = ['Day', 'Week', 'Month'];

const viewToParam: Record<ViewOpt, 'day' | 'week' | 'month'> = {
  Day: 'day',
  Week: 'week',
  Month: 'month',
};

const defaultPeriods: Record<ViewOpt, number> = {
  Day: 7,
  Week: 6,
  Month: 6,
};

const WeeklySpendingChart = () => {
  const { user } = useAuth();
  const [view, setView] = useState<ViewOpt>('Week');
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [labels, setLabels] = useState<string[]>([]);
  const [values, setValues] = useState<number[]>([]);

  useEffect(() => {
    let cancel = false;
    (async () => {
      if (!user) {
        setErr('No authenticated user');
        setLoading(false);
        return;
      }
      setLoading(true);
      setErr(null);
      try {
        const token = await user.getIdToken();
        const v = viewToParam[view];
        const periods = defaultPeriods[view];
        const res = await fetch(
          `${BASE_URL}/api/analytics/spending/over-time?view=${v}&periods=${periods}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              Accept: 'application/json',
            },
          }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        const lbls: string[] = (json.data ?? []).map((d: any) => `${d.label}`);
        const vals: number[] = (json.data ?? []).map((d: any) =>
          Number(d.amount || 0)
        );
        if (!cancel) {
          setLabels(lbls);
          setValues(vals);
        }
      } catch (e: any) {
        if (!cancel) setErr(e.message || 'Failed to load');
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [view, user]);

  if (loading) {
    return (
      <View style={[styles.container, { alignItems: 'center' }]}>
        <GifLoader />
        <Text style={styles.loading}>Loading trend…</Text>
      </View>
    );
  }

  if (err) {
    return (
      <View style={[styles.container, { alignItems: 'center' }]}>
        <Text style={styles.error}>⚠️ {err}</Text>
      </View>
    );
  }

// Fit chart inside card width
const dynamicWidth = baseChartWidth - 24;

// Condense labels
const condensedLabels = labels.map((l) =>
  l.length > 3 ? l.slice(0, 3) : l
);

const chartData = {
  labels: condensedLabels,
  datasets: [{ data: values }],
};

const chartCore = (
  <LineChart
    data={chartData}
    width={dynamicWidth}
    height={200}
    yAxisLabel="$"
    fromZero
    withShadow={false}
    withInnerLines
    withOuterLines={false}
    segments={4}
    chartConfig={{
      backgroundColor: "#fff",
      backgroundGradientFrom: "#fff",
      backgroundGradientTo: "#fff",
      decimalPlaces: 0,
      color: (opacity = 1) => `rgba(0, 122, 255, ${opacity})`,
      labelColor: () => "#666",
      propsForDots: { r: "4", strokeWidth: "2", stroke: "#007AFF" },
      propsForBackgroundLines: { strokeDasharray: "4,4" },
    }}
    bezier
    style={[styles.chart, { marginLeft: -4, marginRight: 0 }]}
  />
);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Spending Overview</Text>

      <View style={styles.toggleContainer}>
        {viewOptions.map((option) => (
          <TouchableOpacity
            key={option}
            onPress={() => setView(option)}
            style={[
              styles.toggleButton,
              view === option && styles.toggleButtonActive,
            ]}
          >
            <Text
              style={[
                styles.toggleText,
                view === option && styles.toggleTextActive,
              ]}
            >
              {option}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {chartCore}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { marginBottom: 24, width: '100%' },
  title: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
  },
  toggleContainer: {
    flexDirection: 'row',
    marginBottom: 8,
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#eee',
    alignSelf: 'flex-start',
    marginLeft: 8,
  },
  toggleButton: { paddingVertical: 8, paddingHorizontal: 16 },
  toggleButtonActive: { backgroundColor: '#007AFF' },
  toggleText: { fontSize: 16, color: '#555' },
  toggleTextActive: { color: '#fff', fontWeight: 'bold' },
  chart: { marginTop: 8, marginLeft: 8, borderRadius: 16 },
  loading: { marginTop: 8, color: '#666' },
  error: { color: '#c0392b' },
});

export default WeeklySpendingChart;
