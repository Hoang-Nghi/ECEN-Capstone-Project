import { Text, View, SafeAreaView } from "react-native";
import React from 'react';
import FinancialEducationList from '../hooks/educationlist';

export default function Index() {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <FinancialEducationList />
    </SafeAreaView>
  );
}
