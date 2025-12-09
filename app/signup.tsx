// app/signup.tsx
import { LinearGradient } from 'expo-linear-gradient';
import { Link, useRouter } from 'expo-router';
import { createUserWithEmailAndPassword, getAuth, sendEmailVerification } from 'firebase/auth';
import { doc, getFirestore, serverTimestamp, setDoc } from 'firebase/firestore';
import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import app from './firebaseConfig';

const auth = getAuth(app);
const db = getFirestore(app);

export default function SignUpScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onCreate = async () => {
    setError(null);
    setBusy(true);
    try {
      const cred = await createUserWithEmailAndPassword(auth, email.trim(), password);
      const u = cred.user;

      // starter docs (same intent as your current file)
      await setDoc(doc(db, 'users', u.uid), {
        displayName: email.split('@')[0],
        email: u.email,
        createdAt: serverTimestamp(),
      });
      await setDoc(doc(db, 'budgets', u.uid), {
        currentlySpent: 0,
        shouldHaveSpentByNow: 0,
        maximumToSpendThisMonth: 1000,
        createdAt: serverTimestamp(),
      });

      await sendEmailVerification(u);
      router.replace('/verify-email');
    } catch (e: any) {
      setError(e?.message ?? 'Sign up failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <LinearGradient colors={['#E8F5E9', '#C8E6C9', '#B2DFDB']} style={{ flex: 1 }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.wrap}>
        <View style={styles.card}>
          <Text style={styles.title}>Create Account</Text>

          <TextInput
            style={styles.input}
            placeholder="Email"
            placeholderTextColor="#7A8F85"
            keyboardType="email-address"
            autoCapitalize="none"
            value={email}
            onChangeText={setEmail}
            editable={!busy}
          />
          <TextInput
            style={styles.input}
            placeholder="Password"
            placeholderTextColor="#7A8F85"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
            editable={!busy}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity style={[styles.cta, busy && { opacity: 0.7 }]} onPress={onCreate} disabled={busy}>
            <Text style={styles.ctaText}>{busy ? 'Creating…' : 'Sign Up'}</Text>
          </TouchableOpacity>

          <View style={styles.bottomRow}>
            <Text style={styles.muted}>Already have an account?</Text>
            <Link href="/signin" asChild>
              <TouchableOpacity><Text style={styles.link}> Sign In</Text></TouchableOpacity>
            </Link>
          </View>
        </View>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, justifyContent: 'center', paddingHorizontal: 24 },
  card: {
    backgroundColor: 'rgba(255,255,255,0.85)',
    borderRadius: 24,
    padding: 20,
    shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 16, shadowOffset: { width: 0, height: 8 },
  },
  title: { fontSize: 28, fontWeight: '700', color: '#2C3E36', textAlign: 'center', marginBottom: 16 },
  input: {
    backgroundColor: '#F0F7F3', borderRadius: 14, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#D5E7DE'
  },
  cta: { backgroundColor: '#00b140', borderRadius: 14, paddingVertical: 14, alignItems: 'center', marginTop: 4 },
  ctaText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  muted: { color: '#54675F' },
  link: { color: '#0E8F62', fontWeight: '700' },
  bottomRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: 14 },
  error: { color: '#A12727', textAlign: 'center', marginBottom: 8 },
});
