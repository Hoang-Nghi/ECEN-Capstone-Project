// hooks/notifications.ts
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { getAuth } from 'firebase/auth';
import { doc, getFirestore, serverTimestamp, setDoc } from 'firebase/firestore';
import { Platform } from 'react-native';
import app from '../firebaseConfig';

const db = getFirestore(app);

export async function registerForPushNotificationsAsync() {
  let token: string | null = null;

  // Only attempt on physical devices; otherwise silently skip.
  if (!Constants.isDevice) {
    console.warn('[push] Skipping registration: requires a physical device.');
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }
  if (finalStatus !== 'granted') {
    console.warn('[push] Permission not granted.');
    return null;
  }

  const tokenData = await Notifications.getExpoPushTokenAsync();
  token = tokenData.data;
  console.log('[push] Expo token:', token);

  // Save token to Firestore under users/{uid}/tokens/{token}
  const { currentUser } = getAuth(app);
  if (currentUser && token) {
    await setDoc(doc(db, 'users', currentUser.uid, 'tokens', token), {
      token,
      createdAt: serverTimestamp(),
    });
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF231F7C',
    });
  }

  return token;
}
