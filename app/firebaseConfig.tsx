// app/services/firebaseConfig.tsx
import { initializeApp } from 'firebase/app';
import { Auth, getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: 'AIzaSyBxdN_8IQKtYfZYU9wjvQSmUwK2vd7SP00',
  authDomain: 'fetch-21a0c.firebaseapp.com',
  databaseURL: 'https://fetch-21a0c-default-rtdb.firebaseio.com', // Fixed: removed parentheses
  projectId: 'fetch-21a0c',
  storageBucket: 'fetch-21a0c.firebasestorage.app',
  messagingSenderId: '1041336188288',
  appId: '1:1041336188288:ios:2dc3557dd3ec37e58b5565',
  measurementId: 'G-measurement-id',
};

const app = initializeApp(firebaseConfig);

// Export auth instance - THIS IS CRITICAL
export const auth: Auth = getAuth(app);

export default app;