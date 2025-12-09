import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs, useRouter } from 'expo-router';
import React from 'react';
import { Text, TouchableOpacity } from 'react-native';

export default function TabLayout() {
  const router = useRouter();

  interface ButtonProps {
    title: string;
    onPress: () => void;
    color: string;
    icon: React.ReactNode; // Add the icon prop
  }
  const CustomButton: React.FC<ButtonProps> = ({ title, onPress, color, icon }) => (
    <TouchableOpacity style={{ backgroundColor: color, padding: 10 }} onPress={onPress}>
      {icon}
      <Text style={{ color: 'white' }}>{title}</Text>
    </TouchableOpacity>
  );


  return (
    <Tabs
      initialRouteName="home"
      screenOptions={{
        tabBarActiveTintColor: '#ffd33d',
        headerStyle: {
            backgroundColor: '#25292e',
        },
        headerShadowVisible: false,
        headerTintColor: '#fff',
        tabBarStyle: {
        backgroundColor: '#25292e',
        },
      }}
    >
      <Tabs.Screen
        name="analysis"
        options={{
          title: 'Analysis',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'bar-chart-sharp' : 'bar-chart-outline'} color={color} size={24}/>
          ),
        }}
      />
      <Tabs.Screen
        name="home"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'home-sharp' : 'home-outline'} color={color} size={24} />
          ),
          headerRight: () => (
            <TouchableOpacity
              onPress={() => router.push('/settings')}
              style={{
                backgroundColor: '#ddd',    // light gray
                width: 32,                   // square
                height: 32,
                borderRadius: 6,             // slightly rounded
                justifyContent: 'center',
                alignItems: 'center',
                marginRight: 12,             // spacing from edge
              }}
            >
              <Ionicons
                name="settings-outline"
                size={20}
                color="#333"                // dark icon color
              />
            </TouchableOpacity>
          ),
        }}
      />
      <Tabs.Screen
        name="api-debug"
        options={{
          title: 'API Debug',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'book-sharp' : 'book-outline'} color={color} size={24}/>
          ),
          tabBarItemStyle: { display: 'none' },
        }}
      />
      <Tabs.Screen
        name="connect-bank"
        options={{
          title: 'Connect Bank',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'book-sharp' : 'book-outline'} color={color} size={24}/>
          ),
          tabBarItemStyle: { display: 'none' },
        }}
      />
      <Tabs.Screen
        name="loadingscreen"
        options={{
          title: 'Loading Screen',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'book-sharp' : 'book-outline'} color={color} size={24}/>
          ),
          tabBarItemStyle: { display: 'none' },
        }}
      />
      <Tabs.Screen
        name="education"
        options={{
          title: 'Education',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name={focused ? 'book-sharp' : 'book-outline'} color={color} size={24}/>
          ),
          tabBarItemStyle: { display: 'none' },
        }}
      />
      <Tabs.Screen
        name="games"
        options={{
          title: 'Games',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons name="game-controller" color={color} size={24}/>
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
            title: 'Settings',
            tabBarItemStyle: { display: 'none' },
            headerTitle: 'Settings',
        }}
      />
    </Tabs>
  );
}
