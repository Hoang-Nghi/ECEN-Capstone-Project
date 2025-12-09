// app/start.tsx
import { Redirect } from 'expo-router';
import { getAuth } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import app from './firebaseConfig';
import { useAuth } from './hooks/useAuth';

const auth = getAuth(app);

export default function StartScreen() {
  const { user, refreshUser, loading } = useAuth();
  const [emailChecked, setEmailChecked] = useState(false);

  useEffect(() => {
    const checkEmail = async () => {
      if (user && !user.emailVerified) {
        await refreshUser();
      }
      setEmailChecked(true);
    };

    if (!loading) {
      checkEmail();
    }
  }, [loading]);

  if (loading || !emailChecked) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!user) return <Redirect href="/signin" />;
  if (!user.emailVerified) return <Redirect href="/verify-email" />;
  return <Redirect href="/home" />;
}
