// app/signin.tsx
import { LinearGradient } from 'expo-linear-gradient';
import { Link, Redirect } from 'expo-router';
import { getAuth, sendPasswordResetEmail, signInWithEmailAndPassword } from 'firebase/auth';
import React, { useState } from 'react';
import {
  KeyboardAvoidingView, Platform,
  StyleSheet,
  Text, TextInput, TouchableOpacity,
  View
} from 'react-native';
import app from './firebaseConfig';
import { useAuth } from './hooks/useAuth';

const auth = getAuth(app);

export default function SignInScreen() {
  const { user } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user && user.emailVerified) return <Redirect href="/home" />;

  const onSignIn = async () => {
    setError(null);
    setBusy(true);
    try {
      await signInWithEmailAndPassword(auth, email.trim(), password);
    } catch (e: any) {
      setError(e?.message ?? 'Sign in failed');
    } finally {
      setBusy(false);
    }
  };

  const onForgot = async () => {
    if (!email) { setError('Enter your email to reset your password.'); return; }
    try {
      await sendPasswordResetEmail(auth, email.trim());
      setError('Password reset email sent.');
    } catch (e: any) {
      setError(e?.message ?? 'Could not send reset email');
    }
  };

  return (
    <LinearGradient colors={['#E8F5E9', '#C8E6C9', '#B2DFDB']} style={{ flex: 1 }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.wrap}>
        <View style={styles.card}>
          <Text style={styles.title}>Sign In</Text>

          <TextInput
            style={styles.input}
            placeholder="Email"
            placeholderTextColor="#7A8F85"
            autoCapitalize="none"
            keyboardType="email-address"
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

          <TouchableOpacity style={[styles.cta, busy && { opacity: 0.7 }]} onPress={onSignIn} disabled={busy}>
            <Text style={styles.ctaText}>{busy ? 'Signing in…' : 'Sign In'}</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={onForgot} disabled={busy}>
            <Text style={styles.linkSm}>Forgot password?</Text>
          </TouchableOpacity>

          <View style={styles.bottomRow}>
            <Text style={styles.muted}>Don’t have an account?</Text>
            <Link href="/signup" asChild>
              <TouchableOpacity><Text style={styles.link}> Sign Up</Text></TouchableOpacity>
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
  linkSm: { textAlign: 'center', marginTop: 10, color: '#2C7A59' },
  muted: { color: '#54675F' },
  link: { color: '#0E8F62', fontWeight: '700' },
  bottomRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: 14 },
  error: { color: '#A12727', textAlign: 'center', marginBottom: 8 },
});
