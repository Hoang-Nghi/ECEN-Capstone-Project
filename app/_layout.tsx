import { Stack } from 'expo-router';
import { getAuth } from 'firebase/auth';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import Toast from 'react-native-toast-message';
import { ThemeProvider } from "../_theme"; // uses index.tsx
import app from './firebaseConfig';
import { registerForPushNotificationsAsync } from './hooks/notifications';
import { AuthProvider, useAuth } from './hooks/useAuth';

const auth = getAuth(app);

export default function RootLayout() {
  return (
    <ThemeProvider>
      <AuthProvider>
      <RootLayoutNav />
      <Toast />
    </AuthProvider>
    </ThemeProvider>
  );
}

function RootLayoutNav() {
  const { user, loading, refreshUser } = useAuth();
  const [emailChecked, setEmailChecked] = useState(false);
  const [showToast, setShowToast] = useState(false);

  useEffect(() => {
    registerForPushNotificationsAsync().catch(console.warn);
    
    let interval: NodeJS.Timeout;

    const checkEmailVerified = async () => {
      // If there is no user, then we're done; allow the stack to render so that the index screen can handle the sign in redirect.
      if (!user) {
        setEmailChecked(true);
        return;
      }

      if (user && !user.emailVerified) {
        await refreshUser();
        const updatedUser = auth.currentUser;

        if (!updatedUser?.emailVerified) {
          interval = setInterval(async () => {
            await refreshUser();
            const refreshedUser = auth.currentUser;

            if (refreshedUser?.emailVerified) {
              clearInterval(interval);
              setShowToast(false);
              setEmailChecked(true); // Mark as checked when verified
            }
          }, 3000);
          return;
        }
      }

      if (user?.emailVerified) {
        if (!showToast) {
          Toast.show({
            type: 'success',
            text1: "You're verified!",
            position: 'bottom',
          });

          try {
            await registerForPushNotificationsAsync();
          } catch (e) {
            console.warn('Push notification registration failed:', e);
          }

          setShowToast(true);
        }

        setEmailChecked(true);
      }
    };

    if (!loading) {
      checkEmailVerified();
    }

    return () => clearInterval(interval);
  }, [user, loading]);

  if (loading || !emailChecked) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      {/* These screens are declared for navigation */}
      <Stack.Screen name="index" />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="signin" options={{ title: 'Sign In' }} />
      <Stack.Screen name="signup" options={{ title: 'Create Account' }} />
      <Stack.Screen name="verify-email" options={{ title: 'Verify Email' }} />
      <Stack.Screen name="settings" options={{ title: 'Settings' }} />
      <Stack.Screen name="+not-found" options={{ title: 'Oops! Not Found' }} />
    </Stack>
  );
}
