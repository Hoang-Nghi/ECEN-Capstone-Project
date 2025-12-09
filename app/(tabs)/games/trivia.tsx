// app/(tabs)/games/trivia.tsx
// Themed Smart Saver Quiz using app color palette

import { getAuth } from "firebase/auth";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { AppTheme, useTheme } from "../../../_theme";
import { useXP } from "./xp-context"; // unified XP context

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  "https://capstone-backend-1041336188288.us-central1.run.app";

type Question = {
  id: string;
  type: string;
  question: string;
  choices: string[];
};

type NewSetResponse = {
  ok: boolean;
  can_play: boolean;
  difficulty?: string;
  questions?: Question[];
  instructions?: string;
  insufficient_data?: boolean;
  message?: string;
  xp_awarded?: number;
  total_xp?: number;
  level?: number;
  streak?: number;
};

type AnswerResponse = {
  ok: boolean;
  is_correct: boolean;
  correct_index: number;
  selected_index: number;
  explanation: string;
  xp_earned: number;
  questions_answered: number;
  total_questions: number;
  quiz_complete: boolean;
};

type CompleteResponse = {
  ok: boolean;
  score: number;
  total: number;
  accuracy: number;
  xp_earned: number;
  total_xp: number;
  level: number;
  streak: number;
  streak_maintained: boolean;
  difficulty_before: string;
  difficulty_after: string;
  difficulty_changed: boolean;
};

async function getFirebaseToken(): Promise<string> {
  const auth = getAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new Error("Not authenticated");
  }
  return await user.getIdToken();
}

async function fetchJson<T>(
  input: string,
  init?: RequestInit,
  timeoutMs = 15000
): Promise<T> {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const url = input.startsWith("http") ? input : `${BASE_URL}${input}`;
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers || {}),
      },
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const msg =
        (data && (data.error || data.message)) ||
        `HTTP ${res.status} ${res.statusText}`;
      throw new Error(msg);
    }
    return data as T;
  } catch (e: any) {
    if (e.name === "AbortError")
      throw new Error("Request timed out — check connection or server load.");
    throw e;
  } finally {
    clearTimeout(t);
  }
}

async function startNewQuiz() {
  const token = await getFirebaseToken();
  return fetchJson<NewSetResponse>(`/api/minigame/quiz/new`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

async function answerQuestion(questionId: string, selectedIndex: number) {
  const token = await getFirebaseToken();
  return fetchJson<AnswerResponse>(`/api/minigame/quiz/answer`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      question_id: questionId,
      selected_index: selectedIndex,
    }),
  });
}

async function completeQuiz() {
  const token = await getFirebaseToken();
  return fetchJson<CompleteResponse>(`/api/minigame/quiz/complete`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export default function SmartSaverQuiz() {
  const { theme } = useTheme();
  const styles = createStyles(theme);

  // Quiz state
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [difficulty, setDifficulty] = useState<string>("basic");

  // Selection & feedback state
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [feedbackState, setFeedbackState] = useState<{
    isCorrect: boolean;
    correctIndex: number;
    explanation: string;
  } | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Results state
  const [finalResults, setFinalResults] = useState<CompleteResponse | null>(
    null
  );

  // Low data scenario
  const [lowDataMessage, setLowDataMessage] = useState<{
    message: string;
    xp_awarded: number;
    level: number;
    streak: number;
  } | null>(null);

  // unified XP context
  const { refresh } = useXP();

  const currentQuestion = questions[currentIndex] || null;
  const isLastQuestion = currentIndex === questions.length - 1;
  const progress = questions.length
    ? ((currentIndex + 1) / questions.length) * 100
    : 0;

  const loadQuiz = useCallback(async () => {
    setLoading(true);
    setError(null);
    setCurrentIndex(0);
    setSelectedIndex(null);
    setFeedbackState(null);
    setFinalResults(null);
    setLowDataMessage(null);

    try {
      const res = await startNewQuiz();

      if (!res.ok) {
        throw new Error("Failed to start quiz");
      }

      if (!res.can_play) {
        if (res.insufficient_data && res.message) {
          setLowDataMessage({
            message: res.message,
            xp_awarded: res.xp_awarded || 0,
            level: res.level || 1,
            streak: res.streak || 0,
          });

          if ((res.xp_awarded ?? 0) > 0) {
            refresh();
          }

          return;
        }
        throw new Error(res.message || "Cannot play quiz at this time");
      }

      if (!res.questions || res.questions.length === 0) {
        throw new Error("No questions returned");
      }

      setQuestions(res.questions);
      setDifficulty(res.difficulty || "basic");
    } catch (e: any) {
      console.error("[SmartSaverQuiz] Load error:", e);
      setError(e?.message || "Failed to load quiz");
    } finally {
      setLoading(false);
    }
  }, [refresh]);

  useEffect(() => {
    loadQuiz();
  }, [loadQuiz]);

  const handleSubmitAnswer = useCallback(async () => {
    if (selectedIndex === null || !currentQuestion || feedbackState) return;

    setSubmitting(true);
    setError(null);

    try {
      const res = await answerQuestion(currentQuestion.id, selectedIndex);

      if (!res.ok) {
        throw new Error("Failed to submit answer");
      }

      setFeedbackState({
        isCorrect: res.is_correct,
        correctIndex: res.correct_index,
        explanation: res.explanation,
      });
    } catch (e: any) {
      console.error("[SmartSaverQuiz] Submit answer error:", e);
      setError(e?.message || "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  }, [selectedIndex, currentQuestion, feedbackState]);

  const handleNext = useCallback(async () => {
    if (!feedbackState) return;

    if (isLastQuestion) {
      setSubmitting(true);
      try {
        const res = await completeQuiz();
        if (!res.ok) {
          throw new Error("Failed to complete quiz");
        }
        setFinalResults(res);
        await refresh();
      } catch (e: any) {
        console.error("[SmartSaverQuiz] Complete error:", e);
        setError(e?.message || "Failed to complete quiz");
      } finally {
        setSubmitting(false);
      }
    } else {
      setCurrentIndex((i) => i + 1);
      setSelectedIndex(null);
      setFeedbackState(null);
    }
  }, [feedbackState, isLastQuestion, refresh]);

  const handleRestart = () => {
    loadQuiz();
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={[styles.container, { justifyContent: "center" }]}>
          <ActivityIndicator size="large" color={styles.accentColor} />
          <Text style={{ marginTop: 12, color: styles.subtleColor }}>
            Loading your quiz...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error && !currentQuestion && !lowDataMessage && !finalResults) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.container}>
          <Text style={styles.header}>Smart Saver Quiz</Text>
          <View style={styles.card}>
            <Text style={styles.errorStandalone}>{error}</Text>
            <Pressable style={styles.primaryBtn} onPress={loadQuiz}>
              <Text style={styles.primaryBtnText}>Try Again</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  if (lowDataMessage) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.container}>
          <Text style={styles.header}>Smart Saver Quiz</Text>
          <View style={styles.card}>
            <Text style={styles.lowDataTitle}>🎉 Great News!</Text>
            <Text style={styles.lowDataMessage}>{lowDataMessage.message}</Text>
            <View style={styles.rewardBox}>
              <Text style={styles.rewardText}>
                +{lowDataMessage.xp_awarded} XP
              </Text>
              <Text style={styles.rewardSubtext}>
                Level {lowDataMessage.level} • {lowDataMessage.streak} week
                streak
              </Text>
            </View>
            <Pressable
              style={[styles.primaryBtn, { marginTop: 16 }]}
              onPress={handleRestart}
            >
              <Text style={styles.primaryBtnText}>Check Again</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  if (finalResults) {
    const { score, total, accuracy, xp_earned, level, streak } = finalResults;
    const percentage = Math.round(accuracy * 100);

    return (
      <SafeAreaView style={styles.safe}>
        <ScrollView style={styles.scrollView}>
          <View style={styles.container}>
            <Text style={styles.header}>Smart Saver Quiz</Text>

            <View style={styles.card}>
              <Text style={styles.resultTitle}>
                {percentage >= 80
                  ? "🎉 Excellent!"
                  : percentage >= 60
                  ? "👍 Good Job!"
                  : "💪 Keep Learning!"}
              </Text>

              <View style={styles.scoreBox}>
                <Text style={styles.scoreText}>
                  {score} / {total}
                </Text>
                <Text style={styles.scoreSubtext}>{percentage}% correct</Text>
              </View>

              <View style={styles.statsGrid}>
                <View style={styles.statItem}>
                  <Text style={styles.statValue}>+{xp_earned}</Text>
                  <Text style={styles.statLabel}>XP Earned</Text>
                </View>
                <View style={styles.statItem}>
                  <Text style={styles.statValue}>{level}</Text>
                  <Text style={styles.statLabel}>Level</Text>
                </View>
                <View style={styles.statItem}>
                  <Text style={styles.statValue}>{streak}</Text>
                  <Text style={styles.statLabel}>Streak</Text>
                </View>
              </View>

              {finalResults.difficulty_changed && (
                <View style={styles.difficultyChange}>
                  <Text style={styles.difficultyText}>
                    Difficulty: {finalResults.difficulty_before} →{" "}
                    {finalResults.difficulty_after}
                  </Text>
                </View>
              )}

              <Pressable
                style={[styles.primaryBtn, { marginTop: 20 }]}
                onPress={handleRestart}
              >
                <Text style={styles.primaryBtnText}>Play Again</Text>
              </Pressable>
            </View>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView style={styles.scrollView}>
        <View style={styles.container}>
          <Text style={styles.header}>Smart Saver Quiz</Text>
          <Text style={styles.difficultyBadge}>
            Difficulty:{" "}
            {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}
          </Text>

          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${progress}%` }]} />
          </View>
          <Text style={styles.progressLabel}>
            Question {currentIndex + 1} of {questions.length}
          </Text>

          <View style={styles.card}>
            <Text style={styles.questionText}>{currentQuestion?.question}</Text>

            {currentQuestion?.choices.map((choice, index) => {
              const isSelected = selectedIndex === index;
              const isCorrectAnswer =
                feedbackState && feedbackState.correctIndex === index;
              const isWrongSelection =
                feedbackState &&
                !feedbackState.isCorrect &&
                selectedIndex === index;

              let buttonStyle = [styles.optionBtn];
              let textStyle = [styles.optionText];

              if (feedbackState) {
                if (isCorrectAnswer) {
                  buttonStyle.push(styles.optionCorrect);
                  textStyle.push(styles.optionTextCorrect);
                } else if (isWrongSelection) {
                  buttonStyle.push(styles.optionWrong);
                  textStyle.push(styles.optionTextWrong);
                }
              } else if (isSelected) {
                buttonStyle.push(styles.optionSelected);
                textStyle.push(styles.optionTextSelected);
              }

              return (
                <Pressable
                  key={index}
                  onPress={() => !feedbackState && setSelectedIndex(index)}
                  style={buttonStyle}
                  disabled={!!feedbackState}
                >
                  <Text style={textStyle}>{choice}</Text>
                </Pressable>
              );
            })}

            {feedbackState && (
              <View
                style={[
                  styles.feedbackBox,
                  feedbackState.isCorrect
                    ? styles.feedbackCorrect
                    : styles.feedbackWrong,
                ]}
              >
                <Text style={styles.feedbackTitle}>
                  {feedbackState.isCorrect ? "✅ Correct!" : "❌ Incorrect"}
                </Text>
                <Text style={styles.feedbackExplanation}>
                  {feedbackState.explanation}
                </Text>
              </View>
            )}

            {error && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            {!feedbackState ? (
              <Pressable
                onPress={handleSubmitAnswer}
                style={[
                  styles.primaryBtn,
                  (selectedIndex === null || submitting) &&
                    styles.primaryBtnDisabled,
                ]}
                disabled={selectedIndex === null || submitting}
              >
                <Text style={styles.primaryBtnText}>
                  {submitting ? "Checking..." : "Check Answer"}
                </Text>
              </Pressable>
            ) : (
              <Pressable
                onPress={handleNext}
                style={[
                  styles.primaryBtn,
                  submitting && styles.primaryBtnDisabled,
                ]}
                disabled={submitting}
              >
                <Text style={styles.primaryBtnText}>
                  {submitting
                    ? "Loading..."
                    : isLastQuestion
                    ? "See Results"
                    : "Next Question"}
                </Text>
              </Pressable>
            )}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function createStyles(theme: AppTheme) {
  const bg = theme?.background ?? "#f8f9fa";
  const card = theme?.card ?? "#fff";
  const text = theme?.text ?? "#1a1a1a";
  const subtle = theme?.subtleText ?? "#666";
  const accent = theme?.accent ?? "#00b140";

  return StyleSheet.create({
    // helpers so we can reference colors in component
    accentColor: accent as any,
    subtleColor: subtle as any,

    safe: { flex: 1, backgroundColor: bg },
    scrollView: { flex: 1 },
    container: { flex: 1, padding: 16, alignItems: "center" },
    header: {
      fontSize: 28,
      fontWeight: "bold",
      marginVertical: 12,
      textAlign: "center",
      color: text,
    },
    difficultyBadge: {
      fontSize: 14,
      color: subtle,
      marginBottom: 12,
      fontWeight: "600",
    },
    progressTrack: {
      width: "100%",
      height: 8,
      backgroundColor: "#e0e0e0",
      borderRadius: 999,
      overflow: "hidden",
      marginBottom: 8,
    },
    progressFill: { height: "100%", backgroundColor: accent },
    progressLabel: {
      marginBottom: 16,
      color: subtle,
      fontSize: 14,
      fontWeight: "600",
    },
    card: {
      width: "100%",
      backgroundColor: card,
      borderRadius: 16,
      padding: 20,
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.08,
      shadowRadius: 8,
      elevation: 3,
    },
    questionText: {
      fontSize: 18,
      fontWeight: "600",
      color: text,
      marginBottom: 20,
      lineHeight: 26,
    },
    optionBtn: {
      borderWidth: 2,
      borderColor: "#e0e0e0",
      borderRadius: 12,
      paddingVertical: 14,
      paddingHorizontal: 16,
      marginVertical: 6,
      backgroundColor: "#fafafa",
    },
    optionSelected: {
      borderColor: accent,
      backgroundColor: accent + "15",
    },
    optionCorrect: {
      borderColor: accent,
      backgroundColor: accent + "22",
    },
    optionWrong: {
      borderColor: "#dc3545",
      backgroundColor: "#ffe6e9",
    },
    optionText: { fontSize: 16, color: text, fontWeight: "500" },
    optionTextSelected: { color: accent, fontWeight: "700" },
    optionTextCorrect: { color: accent, fontWeight: "700" },
    optionTextWrong: { color: "#dc3545", fontWeight: "700" },

    feedbackBox: {
      marginTop: 16,
      padding: 16,
      borderRadius: 12,
      borderWidth: 2,
    },
    feedbackCorrect: {
      backgroundColor: accent + "22",
      borderColor: accent,
    },
    feedbackWrong: {
      backgroundColor: "#ffe6e9",
      borderColor: "#dc3545",
    },
    feedbackTitle: {
      fontSize: 16,
      fontWeight: "700",
      marginBottom: 8,
      color: text,
    },
    feedbackExplanation: {
      fontSize: 15,
      color: text,
      lineHeight: 22,
    },

    errorBox: {
      marginTop: 12,
      padding: 12,
      backgroundColor: "#ffe6e9",
      borderRadius: 8,
    },
    errorText: { color: "#dc3545", fontSize: 14 },
    errorStandalone: {
      color: "#dc3545",
      marginBottom: 12,
      fontSize: 16,
    },

    primaryBtn: {
      marginTop: 16,
      backgroundColor: accent,
      borderRadius: 12,
      alignItems: "center",
      paddingVertical: 14,
    },
    primaryBtnDisabled: { opacity: 0.5 },
    primaryBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },

    // Low Data styles
    lowDataTitle: {
      fontSize: 24,
      fontWeight: "700",
      marginBottom: 12,
      textAlign: "center",
      color: text,
    },
    lowDataMessage: {
      fontSize: 16,
      color: subtle,
      textAlign: "center",
      lineHeight: 24,
      marginBottom: 16,
    },
    rewardBox: {
      backgroundColor: accent + "22",
      padding: 16,
      borderRadius: 12,
      alignItems: "center",
    },
    rewardText: {
      fontSize: 28,
      fontWeight: "800",
      color: accent,
      marginBottom: 4,
    },
    rewardSubtext: {
      fontSize: 14,
      color: subtle,
      fontWeight: "600",
    },

    // Results styles
    resultTitle: {
      fontSize: 24,
      fontWeight: "700",
      textAlign: "center",
      marginBottom: 16,
      color: text,
    },
    scoreBox: {
      alignItems: "center",
      marginBottom: 20,
      paddingVertical: 16,
      borderBottomWidth: 1,
      borderBottomColor: "#e0e0e0",
    },
    scoreText: {
      fontSize: 48,
      fontWeight: "800",
      color: accent,
      marginBottom: 4,
    },
    scoreSubtext: {
      fontSize: 16,
      color: subtle,
      fontWeight: "600",
    },
    statsGrid: {
      flexDirection: "row",
      justifyContent: "space-around",
      marginBottom: 12,
    },
    statItem: {
      alignItems: "center",
    },
    statValue: {
      fontSize: 24,
      fontWeight: "700",
      color: accent,
      marginBottom: 4,
    },
    statLabel: {
      fontSize: 12,
      color: subtle,
      fontWeight: "600",
    },
    difficultyChange: {
      backgroundColor: accent + "15",
      padding: 12,
      borderRadius: 8,
      marginTop: 12,
    },
    difficultyText: {
      fontSize: 14,
      color: accent,
      fontWeight: "600",
      textAlign: "center",
    },
  });
}
