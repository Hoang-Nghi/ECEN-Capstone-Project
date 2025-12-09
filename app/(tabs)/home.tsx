import React, { useEffect, useRef, useState } from "react";
import {
  Animated,
  Easing,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useTheme } from "../../_theme";
import TeacherPopup from "../../components/TeacherPopup";
import { useAuth } from "../hooks/useAuth";

export default function HomeScreen() {
  const { user } = useAuth();
  const displayName =
    user?.displayName || user?.email?.split("@")[0] || "friend";

  const [showPopup, setShowPopup] = useState(true);
  const { theme } = useTheme();

  const BG = theme.background;
  const TEXT = theme.text;
  const SUBTLE = theme.subtleText;
  const ACCENT = theme.accent;
  const CARD = theme.card || "#f4f8f4";

  /**
   * Breathing circle setup
   */
  const SIZE = 250;
  const RADIUS = SIZE / 2;
  const MIN_SCALE = 0.7;
  const MAX_SCALE = 1.1;
  const BREATH_MS = 4000;
  const HOLD_MS = 4000;

  const scale = useRef(new Animated.Value(MIN_SCALE)).current;
  const opacity = useRef(new Animated.Value(0.18)).current;

  const translateY = scale.interpolate({
    inputRange: [MIN_SCALE, MAX_SCALE],
    outputRange: [RADIUS * (1 - MIN_SCALE), RADIUS * (1 - MAX_SCALE)],
    extrapolate: "clamp",
  });

  useEffect(() => {
    const inhale = Animated.parallel([
      Animated.timing(scale, {
        toValue: MAX_SCALE,
        duration: BREATH_MS,
        easing: Easing.inOut(Easing.quad),
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 0.28,
        duration: BREATH_MS,
        easing: Easing.inOut(Easing.quad),
        useNativeDriver: true,
      }),
    ]);

    const exhale = Animated.parallel([
      Animated.timing(scale, {
        toValue: MIN_SCALE,
        duration: BREATH_MS,
        easing: Easing.inOut(Easing.quad),
        useNativeDriver: true,
      }),
      Animated.timing(opacity, {
        toValue: 0.15,
        duration: BREATH_MS,
        easing: Easing.inOut(Easing.quad),
        useNativeDriver: true,
      }),
    ]);

    const seq = Animated.sequence([
      inhale,
      Animated.delay(HOLD_MS),
      exhale,
      Animated.delay(HOLD_MS),
    ]);

    const loop = Animated.loop(seq, { resetBeforeIteration: false });
    loop.start();
    return () => loop.stop();
  }, []);

  /**
   * Starter Tips – rotates every 10s
   */
  const starterTips = [
    "Small shifts matter. Check yesterday’s spending to stay grounded.",
    "Pick one category this week to quietly observe — no pressure.",
    "Wait 24 hours before a big purchase. Most things can wait.",
    "5-minute weekly money check-ins build real momentum.",
    "Saving $5 still counts — consistency > perfection 💚",
  ];

  const [tipIndex, setTipIndex] = useState(0);
  const tipOpacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const interval = setInterval(() => {
      Animated.sequence([
        Animated.timing(tipOpacity, { toValue: 0, duration: 250, useNativeDriver: true }),
        Animated.delay(80),
        Animated.timing(tipOpacity, { toValue: 1, duration: 250, useNativeDriver: true }),
      ]).start();

      setTipIndex((prev) => (prev + 1) % starterTips.length);
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  /**
   * ---------- MAIN RENDER ----------
   */
  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: BG }]}>
      <View style={styles.container}>

        {/* HEADER */}
        <Text style={[styles.eyebrow, { color: ACCENT }]}>Welcome back,</Text>
        <Text style={[styles.title, { color: TEXT }]}>{displayName}</Text>

        <Text style={[styles.subtitle, { color: SUBTLE }]}>
          A calm place to check in with your money — one step at a time.
        </Text>


        {/* ============================ */}
        {/* OPTION A — TIP ABOVE CIRCLE */}
        {/* ============================ */}
        {/* 
        <View style={[styles.card, { backgroundColor: CARD }]}>
          <Text style={[styles.cardTitle, { color: TEXT }]}>Tip of the Day</Text>
          <Animated.Text
            style={[styles.cardBody, { color: SUBTLE, opacity: tipOpacity }]}
          >
            {starterTips[tipIndex]}
          </Animated.Text>
        </View>
        */}


        {/* BREATHING CIRCLE */}
        {/* BREATHING CIRCLE */}
        <View style={styles.breatheContainer}>
          <View
            style={[
              styles.breatheRing,
              {
                width: SIZE,
                height: SIZE,
                borderColor: ACCENT,
                borderRadius: SIZE / 2, // ensure outer ring stays circular
              },
            ]}
          >
            <Animated.View
              style={[
                {
                  width: SIZE,
                  height: SIZE,
                  backgroundColor: ACCENT,
                  opacity,
                  borderRadius: SIZE / 2,  // <-- this is the FIX (keeps it round)
                  transform: [{ translateY }, { scale }],
                },
              ]}
            />
          </View>
        </View>



        {/* ============================ */}
        {/* OPTION B — TIP BELOW CIRCLE */}
        {/* ============================ */}
        {/* UNCOMMENT this block instead if you want the tip BELOW */}
         
        <View style={[styles.card, { backgroundColor: CARD }]}>
          <Text style={[styles.cardTitle, { color: TEXT }]}>Tip of the Day</Text>
          <Animated.Text
            style={[styles.cardBody, { color: SUBTLE, opacity: tipOpacity }]}
          >
            {starterTips[tipIndex]}
          </Animated.Text>
        </View>
       


        {/* NAVIGATION HINT */}
        <Text style={[styles.bottomHint, { color: SUBTLE }]}>
          Swipe left for analysis · Swipe right for games
        </Text>
      </View>

      <TeacherPopup visible={showPopup} onClose={() => setShowPopup(false)} />
    </SafeAreaView>
  );
}

/* STYLES */

const styles = StyleSheet.create({
  safe: { flex: 1 },
  container: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 50,
    alignItems: "center",
  },

  eyebrow: {
    textTransform: "uppercase",
    fontSize: 22,
    letterSpacing: 1.2,
    marginBottom: 4,
    fontWeight: "600",
  },
  title: {
    fontSize: 34,
    fontWeight: "800",
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 15,
    lineHeight: 22,
    marginBottom: 20,
    textAlign: "center",
    maxWidth: 320,
  },

  /* Tip Card */
  card: {
    width: "90%",
    padding: 20,
    borderRadius: 18,
    marginTop: 16,
    marginBottom: 20,
    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 6,
    shadowOffset: { height: 3, width: 0 },
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 8,
  },
  cardBody: {
    fontSize: 14,
    lineHeight: 20,
  },

  /* Breathing Circle */
  breatheContainer: {
    justifyContent: "center",
    alignItems: "center",
    marginVertical: 8,
  },
  breatheRing: {
    borderWidth: 2,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "flex-end",
    overflow: "hidden",
  },
  breatheFill: {},

  bottomHint: {
    textAlign: "center",
    marginTop: "auto",
    fontSize: 13,
    paddingBottom: 20,
  },
});
