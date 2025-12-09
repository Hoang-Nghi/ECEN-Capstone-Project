// hooks/piechart.tsx
import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { PieChart } from 'react-native-gifted-charts';
import GifLoader from '../../components/GifLoader';
import { useAuth } from './useAuth';

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  'https://capstone-backend-1041336188288.us-central1.run.app';

// Category colors
const CATEGORY_COLORS: Record<string, string> = {
  'Food & Dining': '#4B9CD3',
  Shopping: '#76D7C4',
  Transportation: '#F5B041',
  Entertainment: '#D1A5E2',
  Travel: '#F1948A',
  Healthcare: '#85C1E2',
  Home: '#F8B88B',
  'Rent & Utilities': '#BB8FCE',
  'Personal Care': '#FAD7A0',
  Other: '#AEB6BF',
};

function toFriendlyCategory(raw: string): string {
  if (!raw) return 'Other';
  const up = raw.toUpperCase().trim();
  if (up === 'FOOD_AND_DRINK') return 'Food & Dining';
  if (up === 'TRANSPORTATION') return 'Transportation';
  if (up === 'ENTERTAINMENT') return 'Entertainment';
  if (up === 'TRAVEL') return 'Travel';
  if (up === 'HEALTHCARE') return 'Healthcare';
  if (up === 'HOME') return 'Home';
  if (up.includes('RENT') || up.includes('UTILIT')) return 'Rent & Utilities';
  if (up.includes('PERSONAL')) return 'Personal Care';
  if (up.includes('SHOP')) return 'Shopping';
  const nice = up
    .split('_')
    .map((w) => w[0] + w.slice(1).toLowerCase())
    .join(' ');
  return CATEGORY_COLORS[nice] ? nice : 'Other';
}

interface UiCategory {
  category: string;
  amount: number;
  percent: number;
  count: number;
}
interface SpendingUiShape {
  ok: boolean;
  period_days: number;
  period_label: string;
  total_spent: number;
  categories: UiCategory[];
}
type PeriodOption = 7 | 30 | 365;

export const PieChartTest = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SpendingUiShape | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodOption>(7);

  const periodOptions = [
    { days: 7 as PeriodOption, label: 'Week' },
    { days: 30 as PeriodOption, label: 'Month' },
    { days: 365 as PeriodOption, label: 'Year' },
  ];

  useEffect(() => {
    (async () => {
      if (!user) {
        setError('No authenticated user');
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const token = await user.getIdToken();
        const res = await fetch(
          `${BASE_URL}/api/analytics/spending/by-category?days=${selectedPeriod}`,
          { headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' } }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const backend = await res.json();
        const ui: SpendingUiShape = {
          ok: !!backend.ok,
          period_days: backend.days,
          period_label:
            backend.days === 7 ? 'Week' : backend.days === 30 ? 'Month' : 'Year',
          total_spent: backend.total ?? 0,
          categories: (backend.categories ?? []).map((c: any) => ({
            category: toFriendlyCategory(c.name),
            amount: Number(c.amount || 0),
            percent: Number(c.percentage || 0),
            count: 0,
          })),
        };
        ui.categories.sort((a, b) => b.amount - a.amount);
        setData(ui);
      } catch (e: any) {
        setError(e.message || 'Failed to load spending data');
      } finally {
        setLoading(false);
      }
    })();
  }, [user, selectedPeriod]);

  if (loading) {
    return (
      <View style={styles.container}>
        <GifLoader />
        <Text style={styles.loadingText}>Loading spending data...</Text>
      </View>
    );
  }
  if (error) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>⚠️ {error}</Text>
        <Text style={styles.hintText}>
          Add transactions to see your spending breakdown
        </Text>
      </View>
    );
  }
  if (!data || !data.categories || data.categories.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Spending by Category</Text>
        <PeriodToggle
          selected={selectedPeriod}
          setSelected={setSelectedPeriod}
          options={periodOptions}
        />
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No spending data yet</Text>
          <Text style={styles.hintText}>
            Start tracking your expenses to see insights!
          </Text>
        </View>
      </View>
    );
  }

  // Top 4 + Other
  const top = data.categories.slice(0, 4);
  const rest = data.categories.slice(4);
  if (rest.length) {
    const otherAmount = rest.reduce((s, c) => s + c.amount, 0);
    const otherPercent =
      data.total_spent > 0 ? (otherAmount / data.total_spent) * 100 : 0;
    top.push({
      category: 'Other',
      amount: otherAmount,
      percent: otherPercent,
      count: 0,
    });
  }

  const pieData = top.map((cat) => ({
    value: cat.amount,
    color: CATEGORY_COLORS[cat.category] || CATEGORY_COLORS['Other'],
  }));

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Spending by Category</Text>
      <PeriodToggle
        selected={selectedPeriod}
        setSelected={setSelectedPeriod}
        options={periodOptions}
      />

      <PieChart
        data={pieData}
        donut
        radius={110}
        innerRadius={65}
        innerCircleColor="#ffffff"
        showText={false}
        strokeWidth={3}
        strokeColor="#fff"
        centerLabelComponent={() => (
          <View style={styles.centerLabel}>
            <Text style={styles.totalText}>
              {`$${Math.round(data.total_spent).toLocaleString('en-US')}`}
            </Text>
            <Text style={styles.totalLabel}>Total</Text>
          </View>
        )}
      />

      {/* Legend */}
      <View style={styles.legend}>
        {top.map((cat, i) => (
          <View key={i} style={styles.legendItem}>
            <View
              style={[styles.legendColor, { backgroundColor: pieData[i].color }]}
            />
            <Text style={styles.legendText}>
              {cat.category} · {Math.round(cat.percent)}%
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
};

const PeriodToggle = ({
  selected,
  setSelected,
  options,
}: {
  selected: PeriodOption;
  setSelected: (v: PeriodOption) => void;
  options: { days: PeriodOption; label: string }[];
}) => (
  <View style={styles.periodToggle}>
    {options.map((option) => (
      <TouchableOpacity
        key={option.days}
        onPress={() => setSelected(option.days)}
        style={[
          styles.periodButton,
          selected === option.days && styles.periodButtonActive,
        ]}
      >
        <Text
          style={[
            styles.periodButtonText,
            selected === option.days && styles.periodButtonTextActive,
          ]}
        >
          {option.label}
        </Text>
      </TouchableOpacity>
    ))}
  </View>
);

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    marginBottom: 24,
    width: '100%',
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
    alignSelf: 'flex-start',
  },
  periodToggle: {
    flexDirection: 'row',
    marginBottom: 16,
    alignSelf: 'center',
  },
  periodButton: {
    paddingVertical: 6,
    paddingHorizontal: 16,
    marginHorizontal: 4,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
  },
  periodButtonActive: { backgroundColor: '#4B9CD3' },
  periodButtonText: { fontSize: 14, color: '#666', fontWeight: '500' },
  periodButtonTextActive: { color: '#fff', fontWeight: '600' },
  centerLabel: { alignItems: 'center' },
  totalText: { fontSize: 28, fontWeight: 'bold', color: '#333' },
  totalLabel: { fontSize: 14, color: '#888' },
  legend: { width: '100%', marginTop: 24 },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  legendColor: { height: 16, width: 16, borderRadius: 4, marginRight: 8 },
  legendText: { fontSize: 16, color: '#444' },
  loadingText: { marginTop: 8, color: '#666', fontSize: 14 },
  errorText: { color: '#e74c3c', fontSize: 16, marginBottom: 8 },
  emptyContainer: { paddingVertical: 40, alignItems: 'center' },
  emptyText: { color: '#333', fontSize: 18, fontWeight: '600', marginBottom: 8 },
  hintText: { color: '#888', fontSize: 14, textAlign: 'center' },
});

export default PieChartTest;
