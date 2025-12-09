import { Redirect, useRouter } from 'expo-router';
import { getAuth, sendEmailVerification } from 'firebase/auth';
import React, { useEffect } from 'react';
import { Button, StyleSheet, Text, View } from 'react-native';
import Toast from 'react-native-toast-message';
import app from './firebaseConfig';
import { useAuth } from './hooks/useAuth';

const auth = getAuth(app);

export default function VerifyEmailScreen() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();

  useEffect(() => {
    let t = setInterval(async () => {
      await refreshUser();
      if (auth.currentUser?.emailVerified) {
        clearInterval(t);
        router.replace('/home');
      }
    }, 3000);
    return () => clearInterval(t);
  }, []);

  const handleResend = async () => {
    if (!auth.currentUser) return;
    await sendEmailVerification(auth.currentUser);
    Toast.show({
      type: 'success',
      text1: 'Verification email sent again!',
      position: 'bottom',
    });
  };

  if (user?.emailVerified) return <Redirect href="/home" />;

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.icon}>📧</Text>
        <Text style={styles.title}>Verify your email</Text>

        {user?.email ? (
          <Text style={styles.subtitle}>
            We’ve sent a verification link to:
            {'\n'}
            <Text style={styles.email}>{user.email}</Text>
          </Text>
        ) : (
          <Text style={styles.subtitle}>
            We’ve sent a verification link to your email address.
          </Text>
        )}

        <Text style={styles.body}>
          Please tap the link in that email to finish setting up your account.
          {'\n\n'}
          If you don’t see it, check your <Text style={styles.bold}>Spam</Text> or{' '}
          <Text style={styles.bold}>Junk</Text> folder, or any
          “Promotions/Other” tabs your email might have.
        </Text>

        <View style={styles.buttonContainer}>
          <Button title="Resend verification email" onPress={handleResend} />
        </View>

        <Text style={styles.footerText}>
          Once you’ve verified, come back to this app — we’ll automatically move
          you forward when your email is confirmed.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    backgroundColor: '#050816', // or your app's background color
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    width: '100%',
    borderRadius: 16,
    padding: 20,
    backgroundColor: 'white',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 4,
  },
  icon: {
    fontSize: 40,
    marginBottom: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    marginBottom: 8,
    textAlign: 'center',
    color: '#111827',
  },
  subtitle: {
    fontSize: 15,
    textAlign: 'center',
    color: '#4B5563',
    marginBottom: 12,
  },
  email: {
    fontWeight: '600',
    color: '#111827',
  },
  body: {
    fontSize: 14,
    textAlign: 'center',
    color: '#6B7280',
    marginBottom: 20,
    lineHeight: 20,
  },
  bold: {
    fontWeight: '600',
    color: '#111827',
  },
  buttonContainer: {
    width: '100%',
    marginBottom: 12,
  },
  footerText: {
    fontSize: 12,
    textAlign: 'center',
    color: '#9CA3AF',
  },
});
