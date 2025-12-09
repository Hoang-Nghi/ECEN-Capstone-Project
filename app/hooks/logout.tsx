// logout.tsx
import React from 'react';
import { Button, Alert } from 'react-native';
import { useAuth } from './useAuth'; // Adjust the path if needed
import { useRouter } from 'expo-router';

export const LogoutButton = () => {
  const { signOut } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await signOut();
      Alert.alert('Success', 'You have been signed out.');
      router.replace('/signin'); // Redirect to sign-in screen
    } catch (error) {
      Alert.alert('Error', 'Could not sign out.');
    }
  };

  return <Button title="Log Out" onPress={handleLogout} />;
};
