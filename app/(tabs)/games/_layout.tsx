// app/(tabs)/games/_layout.tsx
import { Stack } from "expo-router";
import { XPProvider } from "./xp-context";

export default function GamesStack() {
  return (
    <XPProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />              {/* hub */}
        <Stack.Screen name="trivia" />
        <Stack.Screen name="connections" />
        <Stack.Screen name="spend-detective" />
        {/* add new games later as more <Stack.Screen />s */}
      </Stack>
    </XPProvider>
  );
}
