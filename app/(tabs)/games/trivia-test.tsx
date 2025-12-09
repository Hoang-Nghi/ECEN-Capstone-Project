

/////////////




// app/(tabs)/games/trivia-test.tsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FlatList, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";

/* ----------------------------- Types ----------------------------- */
type UIQuestion = { id: string; question: string; choices: string[]; correctIndex: number; explanation?: string; };
type SubmitResult = { score: number; total: number; accuracy: number; xpEarned: number; level: number; streak: number; explanations: string[]; };

/* --------------------- Financial trivia (local) ------------------- */
const bank: UIQuestion[] = [
  {
    id: "q1",
    question: "You put $600 into an emergency fund each month. About how much after 6 months (no interest)?",
    choices: ["$2,400", "$3,600", "$4,200", "$6,000"],
    correctIndex: 1,
    explanation: "$600 × 6 = $3,600."
  },
  {
    id: "q2",
    question: "Your credit card shows 20% APR. What does APR best describe?",
    choices: ["Annual interest rate", "Monthly late fee", "Card limit", "Cash-back rate"],
    correctIndex: 0,
    explanation: "APR is the yearly interest rate on balances."
  },
  {
    id: "q3",
    question: "Your take-home pay is $3,000. A 50/30/20 budget suggests how much for savings/debt?",
    choices: ["$300", "$450", "$600", "$900"],
    correctIndex: 2,
    explanation: "20% of $3,000 = $600."
  },
  {
    id: "q4",
    question: "You owe $1,200 at 1% monthly interest and pay only $12 this month. What happens?",
    choices: ["Balance unchanged", "Balance increases", "Balance drops to $1,188", "Account closes"],
    correctIndex: 1,
    explanation: "$12 covers interest only → principal remains; more fees may accrue."
  },
  {
    id: "q5",
    question: "A savings account pays 4% APY. Roughly how much interest on $1,000 after one year?",
    choices: ["$4", "$40", "$400", "$140"],
    correctIndex: 1,
    explanation: "≈ 4% of $1,000 = $40 (ignoring compounding nuance)."
  },
  {
    id: "q6",
    question: "You finance a $20,000 car for 5 years at a fixed rate. Lower monthly payment usually means…",
    choices: ["Shorter loan term", "More interest over life", "Higher credit score", "Higher down payment"],
    correctIndex: 1,
    explanation: "Longer term → lower monthly but more total interest."
  },
  {
    id: "q7",
    question: "Which action most quickly improves your credit score?",
    choices: ["Lower credit utilization", "Open many new cards", "Only make minimums", "Ignore old collections"],
    correctIndex: 0,
    explanation: "Keeping balances low vs. limits improves utilization."
  },
  {
    id: "q8",
    question: "You earn $1,200 and spend $900 this week. Savings rate?",
    choices: ["15%", "20%", "25%", "30%"],
    correctIndex: 2,
    explanation: "Saved $300 → 300/1200 = 25%."
  }
];

const shuffle = <T,>(a: T[]) => { const c = a.slice(); for (let i=c.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1)); [c[i],c[j]]=[c[j],c[i]];} return c; };

function sampleQuestions(n=6): UIQuestion[] {
  const picked = shuffle(bank).slice(0, n);
  return picked.map(q => {
    const pairs = q.choices.map((c,i)=>({c,i}));
    const s = shuffle(pairs);
    return { ...q, choices: s.map(p=>p.c), correctIndex: s.findIndex(p=>p.i===q.correctIndex) };
  });
}

/* ---------------------------- Component --------------------------- */
export default function TriviaTestScreen() {
  const [questions, setQuestions] = useState<UIQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const [answers, setAnswers] = useState<number[]>([]);
  const [explanations, setExplanations] = useState<string[]>([]);
  const [result, setResult] = useState<SubmitResult | null>(null);

  const q = useMemo(()=>questions[index], [questions,index]);
  const done = index >= questions.length;
  const pressLock = useRef(false);

  const load = useCallback(() => {
    setQuestions(sampleQuestions(6));
    setIndex(0); setSelected(null); setChecked(false);
    setAnswers([]); setExplanations([]); setResult(null);
  }, []);
  useEffect(()=>{ load(); },[load]);
  useEffect(()=>{ setSelected(null); setChecked(false); },[index]);

  const onCheck = useCallback(() => {
    if (pressLock.current || selected==null || !q) return;
    pressLock.current = true; setTimeout(()=> (pressLock.current=false), 250);
    setChecked(true);
    if (q.explanation?.trim()) setExplanations(prev=>[...prev, q.explanation!]);
  },[q,selected]);

  const onNextOrSubmit = useCallback(() => {
    if (pressLock.current) return;
    pressLock.current = true; setTimeout(()=> (pressLock.current=false), 250);

    setAnswers(prev => { const next = prev.slice(); if (selected!=null) next[index]=selected; return next; });
    const isLast = index === questions.length - 1;
    if (isLast) {
      const total = questions.length;
      const earlier = questions.reduce((acc,qq,i)=> acc + (answers[i]===qq.correctIndex ? 1:0), 0);
      const score = earlier + (selected===q.correctIndex ? 1:0) - (answers[index]===q.correctIndex ? 1:0);
      const accuracy = total ? score/total : 0;
      setResult({
        score, total, accuracy, xpEarned: score*20,
        level: Math.max(1, Math.floor(1+accuracy*10)),
        streak: accuracy>=0.6 ? 3 : 0,
        explanations
      });
      setIndex(i=>i+1);
    } else {
      setIndex(i=>i+1);
    }
  },[answers,explanations,index,q,questions,selected]);

  const onRestart = () => load();

  const progressPct = useMemo(() => questions.length ? Math.round((index/questions.length)*100) : 0, [index,questions.length]);

  /* ------------------------------- Result View ------------------------------ */
  if (done && result) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.container}>
          <Text style={styles.header}>Financial Trivia (Test)</Text>
          <View style={[styles.card, styles.cardTall, styles.cardWithBottomClear]}>
            <View style={{flexGrow:1, justifyContent:"center"}}>
              <Text style={styles.resultTitle}>
                {result.accuracy >= 0.8 ? "🎉 Excellent!" : result.accuracy >= 0.6 ? "👍 Nice Work!" : "📚 Keep Practicing!"}
              </Text>
              <Text style={styles.resultText}>
                Score: <Text style={styles.bold}>{result.score}</Text> / {result.total} ({Math.round(result.accuracy*100)}%)
              </Text>
              <View style={styles.rewardBox}>
                <Text style={{ color:"#00b140", fontWeight:"700", fontSize:18 }}>+{result.xpEarned} XP</Text>
                <Text style={{ color:"#666", marginTop:4 }}>Level {result.level} • Demo streak {result.streak ? `${result.streak}🔥`:"reset"}</Text>
              </View>
              {result.explanations?.length>0 && (
                <View style={{marginTop:12}}>
                  <Text style={{fontWeight:"700", marginBottom:8, fontSize:16}}>💡 Explanations</Text>
                  <FlatList data={result.explanations} keyExtractor={(s,i)=>`exp-${i}`} renderItem={({item})=>(
                    <Text style={{marginBottom:6, color:"#333", fontSize:14}}>• {item}</Text>
                  )}/>
                </View>
              )}
            </View>
            <Pressable style={[styles.primaryBtn,{marginTop:10}]} onPress={onRestart}>
              <Text style={styles.primaryBtnText}>Play Again</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  /* --------------------------------- Quiz View -------------------------------- */
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.header}>Financial Trivia (Test)</Text>

        <View style={styles.progressTrack}><View style={[styles.progressFill,{width:`${progressPct}%`}]} /></View>
        <Text style={styles.progressLabel}>Question {Math.min(index+1, questions.length)} of {questions.length}</Text>

        <View style={[styles.card, styles.cardTall, styles.cardWithBottomClear]}>
          <ScrollView contentContainerStyle={{paddingBottom:8}} style={{flex:1}}>
            <Text style={styles.prompt}>{q?.question}</Text>

            {q?.choices?.map((choice, i) => {
              const isSelected = selected === i;
              const isCorrect = checked && q?.correctIndex === i;
              const isWrong = checked && isSelected && q?.correctIndex !== i;
              return (
                <Pressable
                  key={i}
                  onPress={() => !checked && setSelected(i)}
                  hitSlop={8}
                  style={[
                    styles.optionBtn,
                    isSelected && !checked && styles.optionSelected,
                    isCorrect && styles.optionCorrect,
                    isWrong && styles.optionWrong,
                    checked && !isCorrect && !isWrong && styles.optionDisabled,
                  ]}
                >
                  <Text style={[
                    styles.optionText,
                    (isSelected && !checked) && styles.optionTextSelected,
                    isCorrect && styles.optionTextCorrect,
                    isWrong && styles.optionTextWrong,
                  ]}>
                    {choice}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>

          {/* Button pulled a bit closer to the choices */}
          {!checked ? (
            <Pressable style={[styles.primaryBtn,(selected==null)&&styles.primaryBtnDisabled, { marginTop: 6 }]} disabled={selected==null} onPress={onCheck}>
              <Text style={styles.primaryBtnText}>Check</Text>
            </Pressable>
          ) : (
            <Pressable style={[styles.secondaryBtn, { marginTop: 6 }]} onPress={onNextOrSubmit}>
              <Text style={styles.secondaryBtnText}>
                {index === questions.length - 1 ? "Next / Submit" : "Next"}
              </Text>
            </Pressable>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}

/* ----------------------------------- Styles ---------------------------------- */
const BG = "#f2f2f2";            // matches your other screens
const CARD = "#fff";
const TEXT = "#222";
const SUBTLE = "#666";
const ACCENT = "#00b140";        // primary green
const BORDER = "#d9d9d9";
const DARK = "#111827";          // secondary button bg
const GREEN = "#16a34a";
const RED = "#ef4444";

const styles = StyleSheet.create({
  safe: { flex:1, backgroundColor: BG },
  container: { flex:1, paddingHorizontal:18, paddingTop:8, alignItems:"center" },

  header: { fontSize:24, fontWeight:"800", marginVertical:12, textAlign:"center", color: TEXT },

  progressTrack:{ width:"100%", height:8, backgroundColor:"#e5e7eb", borderRadius:999, overflow:"hidden" },
  progressFill:{ height:"100%", backgroundColor: ACCENT },
  progressLabel:{ marginTop:6, marginBottom:10, color: SUBTLE, fontSize:13, fontWeight:"600" },

  card:{ width:"100%", backgroundColor: CARD, borderRadius:20, padding:18, borderWidth:1, borderColor: "#1f2937" },
  // tall but leaves breathing room above the tab bar:
  cardTall:{ flex:1, alignSelf:"stretch" },
  cardWithBottomClear:{ marginBottom: 10 }, // << adds space above tabs

  prompt:{ fontSize:22, lineHeight:28, fontWeight:"800", color: TEXT, marginBottom:14 },

  optionBtn:{
    borderWidth:1,
    borderColor: BORDER,
    borderRadius:16,
    paddingVertical:16,
    paddingHorizontal:16,
    marginVertical:8,
    minHeight:60,
    justifyContent:"center",
    backgroundColor:"#fafafa",
  },
  optionSelected:{ borderColor: ACCENT, backgroundColor:"#eefaf2" },   // selected before check
  optionDisabled:{ opacity:0.7 },
  optionCorrect:{ backgroundColor:"#e7f7ec", borderColor: GREEN },
  optionWrong:{ backgroundColor:"#fff7f7", borderColor: RED },

  optionText:{ fontSize:18, fontWeight:"700", color: TEXT },
  optionTextSelected:{ color:"#0a7d36" },
  optionTextCorrect:{ color:"#0a7d36" },
  optionTextWrong:{ color:"#b91c1c" },

  primaryBtn:{ marginTop:8, backgroundColor: ACCENT, borderRadius:16, alignItems:"center", paddingVertical:14 },
  primaryBtnDisabled:{ opacity:0.6 },
  primaryBtnText:{ color:"#fff", fontWeight:"800", fontSize:18 },

  secondaryBtn:{ marginTop:8, backgroundColor: DARK, borderRadius:16, alignItems:"center", paddingVertical:14 },
  secondaryBtnText:{ color:"#fff", fontWeight:"800", fontSize:18 },

  resultTitle:{ fontSize:22, fontWeight:"800", marginBottom:6, color: TEXT, textAlign:"center" },
  resultText:{ fontSize:16, color: SUBTLE, marginBottom:12, textAlign:"center" },
  bold:{ fontWeight:"900" },
  rewardBox:{ backgroundColor:"#f8f8f8", padding:12, borderRadius:14, marginTop:8, alignItems:"center" },
});

