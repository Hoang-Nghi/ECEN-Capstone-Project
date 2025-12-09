// hooks/graph.tsx
import { doc, getFirestore, onSnapshot } from 'firebase/firestore';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Text as RnText, View } from 'react-native';
import Svg, { ClipPath, Defs, G, Line, Rect } from 'react-native-svg';
import GifLoader from '../../components/GifLoader';
import app from '../firebaseConfig';
import { useAuth } from './useAuth';

const db = getFirestore(app);
const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  'https://capstone-backend-1041336188288.us-central1.run.app';

// Palette
const CLR_UNDER = '#00b140'; // spent within pace
const CLR_OVER = '#e74c3c'; // overspent
const CLR_PACE_GAP = '#CDEBFF'; // under pace (cushion)
const CLR_REMAIN = '#C6D8E7'; // remaining to month max
const CLR_STROKE = '#4f6f62';
const CLR_DIVIDER = '#3D7D57';
const CLR_TEXT = '#334';

const USE_API = true;

const money = (n: number) => `$${Math.round(n).toLocaleString('en-US')}`;
const clamp0 = (n: number) => Math.max(0, n);

const HorizontalStackedBarChart: React.FC = () => {
  const { user, loading: authLoading } = useAuth();
  const [dataLoaded, setDataLoaded] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [currentlySpent, setCurrentlySpent] = useState(0);
  const [shouldHaveSpentByNow, setShouldHaveSpentByNow] = useState(0);
  const [maximumToSpendThisMonth, setMaximumToSpendThisMonth] = useState(0);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setErrorMsg('No authenticated user');
      setDataLoaded(true);
      return;
    }

    const load = async () => {
      try {
        if (USE_API) {
          const token = await user.getIdToken();
          const res = await fetch(
            `${BASE_URL}/api/analytics/budget/progress`,
            {
              headers: {
                Authorization: `Bearer ${token}`,
                Accept: 'application/json',
              },
            }
          );
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const d = await res.json();
          setCurrentlySpent(d.currently_spent || 0);
          setShouldHaveSpentByNow(d.should_have_spent_by_now || 0);
          setMaximumToSpendThisMonth(d.maximum_to_spend_this_month || 0);
          setDataLoaded(true);
        } else {
          const refDoc = doc(db, 'budgets', user.uid);
          const unsub = onSnapshot(
            refDoc,
            (snap) => {
              if (snap.exists()) {
                const d = snap.data() as any;
                setCurrentlySpent(d.currentlySpent || 0);
                setShouldHaveSpentByNow(d.shouldHaveSpentByNow || 0);
                setMaximumToSpendThisMonth(d.maximumToSpendThisMonth || 0);
              }
              setDataLoaded(true);
            },
            (err) => {
              setErrorMsg(err.message);
              setDataLoaded(true);
            }
          );
          return () => unsub();
        }
      } catch (e: any) {
        setErrorMsg(e.message || 'Failed to load budget data');
        setDataLoaded(true);
      }
    };

    load();
  }, [user, authLoading]);

  if (errorMsg) {
    return (
      <View style={{ padding: 16 }}>
        <RnText style={{ color: '#c0392b' }}>
          Error loading chart: {errorMsg}
        </RnText>
      </View>
    );
  }

  // 🌟 Use GIF while auth/data is loading
  if (authLoading || !dataLoaded) {
    return <GifLoader />;
  }

  // Derived segments
  const spent = clamp0(currentlySpent);
  const pace = clamp0(shouldHaveSpentByNow);
  const maxMonth = Math.max(clamp0(maximumToSpendThisMonth), 1);

  const spentWithinPace = Math.min(spent, pace);
  const overspent = clamp0(spent - pace);
  const paceGap = clamp0(pace - spentWithinPace); // under your suggested pace (good cushion)
  const remaining = clamp0(maxMonth - Math.max(spent, pace)); // to month cap

  // Layout
  const chartHeight = 124;
  const barHeight = 56;
  const rx = 14;
  const padX = 18;
  const innerWidth = Math.max(0, containerWidth - padX * 2);

  const segments = [
    { value: spentWithinPace, fill: CLR_UNDER },
    { value: overspent, fill: CLR_OVER },
    { value: paceGap, fill: CLR_PACE_GAP },
    { value: remaining, fill: CLR_REMAIN },
  ];

  // Build rectangles
  const rects: JSX.Element[] = [];
  let accForX = 0;
  segments.forEach((seg, i) => {
    const x = padX + (accForX / maxMonth) * innerWidth;
    const w = (seg.value / maxMonth) * innerWidth;
    if (w > 0) {
      rects.push(
        <Rect
          key={i}
          x={x}
          y={(chartHeight - barHeight) / 2}
          width={w}
          height={barHeight}
          fill={seg.fill}
        />
      );
    }
    accForX += seg.value;
  });

  // Guide lines at spent & pace (clamped inside right edge)
  const guideXs = [spent, pace].map((v) => {
    const xRaw = padX + (v / maxMonth) * innerWidth;
    return Math.min(xRaw, padX + innerWidth - 1);
  });

  // Friendly summary
  let summary: string;
  if (spent === 0 && pace > 0) {
    summary =
      'You have not spent anything yet this period — a strong start below your budget pace.';
  } else if (overspent > 0) {
    summary = `You are about ${money(
      overspent
    )} above your suggested pace so far. Try to slow down a bit to stay within budget.`;
  } else if (paceGap > 0) {
    summary = `You are about ${money(
      paceGap
    )} under your suggested pace so far — nice job staying below budget.`;
  } else {
    summary = 'You are right on your suggested spending pace so far.';
  }

  return (
    <View
      style={{ width: '100%', paddingHorizontal: 16, alignItems: 'center' }}
      onLayout={(e) => setContainerWidth(e.nativeEvent.layout.width)}
    >
      {/* Description above chart */}
      <RnText
        style={{
          color: CLR_TEXT,
          fontSize: 16,
          marginBottom: 8,
          alignSelf: 'flex-start',
        }}
      >
        This chart shows how your{' '}
        <RnText style={{ fontWeight: '700' }}>current spending</RnText> compares
        to your monthly budget and a gentle pacing line.
      </RnText>

      {containerWidth === 0 ? (
        <ActivityIndicator size="small" color="#00b140" />
      ) : (
        <Svg
          width={innerWidth + padX * 2}
          height={chartHeight}
          style={{ alignSelf: 'center' }}
        >
          <Defs>
            <ClipPath id="barClip">
              <Rect
                x={padX}
                y={(chartHeight - barHeight) / 2}
                width={innerWidth}
                height={barHeight}
                rx={rx}
                ry={rx}
              />
            </ClipPath>
          </Defs>

          <G clipPath="url(#barClip)">
            <Rect
              x={padX}
              y={(chartHeight - barHeight) / 2}
              width={innerWidth}
              height={barHeight}
              fill="#F7F9F8"
            />
            {rects}
          </G>

          {/* Outline */}
          <Rect
            x={padX}
            y={(chartHeight - barHeight) / 2}
            width={innerWidth}
            height={barHeight}
            rx={rx}
            ry={rx}
            fill="none"
            stroke={CLR_STROKE}
            strokeWidth={2}
          />

          {/* Guide lines */}
          {guideXs.map((x, i) => (
            <Line
              key={i}
              x1={x}
              y1={(chartHeight - barHeight) / 2}
              x2={x}
              y2={(chartHeight + barHeight) / 2}
              stroke={CLR_DIVIDER}
              strokeDasharray="3,3"
              strokeWidth={1}
            />
          ))}
        </Svg>
      )}

      {/* Friendly summary under chart */}
      <View style={{ marginTop: 6, alignSelf: 'flex-start' }}>
        <RnText style={{ color: CLR_TEXT, fontSize: 13 }}>{summary}</RnText>
      </View>

      {/* Legend with values */}
      <View style={{ marginTop: 10, gap: 8, width: '100%' }}>
        <LegendSwatch
          color={CLR_UNDER}
          label={`Spent so far (on/under pace)`}
          value={money(spent)}
        />
        {overspent > 0 && (
          <LegendSwatch
            color={CLR_OVER}
            label={`Over your suggested pace`}
            value={money(overspent)}
          />
        )}
        {paceGap > 0 && (
          <LegendSwatch
            color={CLR_PACE_GAP}
            label={`Under your pace so far (cushion)`}
            value={money(paceGap)}
          />
        )}
        <LegendSwatch
          color={CLR_REMAIN}
          label={`Left in monthly budget`}
          value={money(remaining)}
        />
        <LegendItem icon="🎯" label="Monthly limit" value={money(maxMonth)} />
        <LegendItem
          icon="⏱️"
          label="Suggested pace by today"
          value={money(pace)}
        />
      </View>
    </View>
  );
};

const LegendSwatch = ({
  color,
  label,
  value,
}: {
  color: string;
  label: string;
  value: string;
}) => (
  <View
    style={{
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}
  >
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
      <View
        style={{ width: 14, height: 14, borderRadius: 4, backgroundColor: color }}
      />
      <RnText style={{ color: '#445', fontSize: 14 }}>{label}</RnText>
    </View>
    <RnText style={{ color: '#111', fontSize: 14, fontWeight: '700' }}>
      {value}
    </RnText>
  </View>
);

const LegendItem = ({
  icon,
  label,
  value,
}: {
  icon?: string;
  label: string;
  value: string;
}) => (
  <View
    style={{
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}
  >
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
      {!!icon && <RnText style={{ fontSize: 14 }}>{icon}</RnText>}
      <RnText style={{ color: '#445', fontSize: 14 }}>{label}</RnText>
    </View>
    <RnText style={{ color: '#111', fontSize: 14, fontWeight: '700' }}>
      {value}
    </RnText>
  </View>
);

export default HorizontalStackedBarChart;
