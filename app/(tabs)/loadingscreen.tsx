import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";
import GifLoader from "../../components/GifLoader"; // 👈 see #2 below

const LoadingScreen = () => {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 13000);
    return () => clearTimeout(timer);
  }, []);


  return (
    <View style={{ flex: 1 }}>
      {isLoading ? (
        <GifLoader />
      ) : (
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
          <Text>Content Loaded!</Text>
        </View>
      )}
    </View>
  );
};

export default LoadingScreen;  // ✅ THIS is what Expo Router needs
