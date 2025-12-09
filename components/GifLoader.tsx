import React from "react";
import { Image, StyleSheet, View } from "react-native";

type GifLoaderProps = {
  message?: string;
};

const GifLoader = () => {
  return (
    <View style={styles.container}>
      <Image
        source={require("../app/assets/loading.gif")}
        style={styles.gif}
      />
    </View>
  );
};

export default GifLoader; // <– default export only

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  gif: {
    width: 140,
    height: 140,
  },
  text: {
    marginTop: 8,
    fontSize: 14,
    color: "#e5e7eb",
    fontWeight: "500",
  },
});
