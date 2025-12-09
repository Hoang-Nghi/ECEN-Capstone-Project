// QuickTestScreen.js (add this to your mobile app)
import React, { useState } from 'react';
import { View, Button, Text, ScrollView } from 'react-native';

const BACKEND_URL = 'https://capstone-backend-1041336188288.us-central1.run.app';

export default function QuickTestScreen() {
  const [results, setResults] = useState([]);

  const runTests = async () => {
    setResults([]);
    
    // Test 1: Health
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      const data = await res.json();
      setResults(prev => [...prev, `Health: ${data.service} v${data.version}`]);
    } catch (e) {
      setResults(prev => [...prev, `Health: ${e.message}`]);
    }

    // Test 2: Echo
    try {
      const res = await fetch(`${BACKEND_URL}/api/test/echo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'From mobile app!' })
      });
      const data = await res.json();
      setResults(prev => [...prev, `Echo: ${data.message}`]);
    } catch (e) {
      setResults(prev => [...prev, `Echo: ${e.message}`]);
    }
  };

  return (
    <View style={{ padding: 20 }}>
      <Button title="Test Backend Connection" onPress={runTests} />
      <ScrollView style={{ marginTop: 20 }}>
        {results.map((r, i) => <Text key={i}>{r}</Text>)}
      </ScrollView>
    </View>
  );
}
