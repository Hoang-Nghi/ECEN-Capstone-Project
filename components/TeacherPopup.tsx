import React, { useEffect, useState } from "react";
import {
  ImageBackground,
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import GifLoader from "./GifLoader";

type TeacherPopupProps = {
  visible: boolean;
  onClose: () => void;
};

export default function TeacherPopup({ visible, onClose }: TeacherPopupProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [page, setPage] = useState<1 | 2>(1);

  useEffect(() => {
    if (visible) {
      setImageLoaded(false);
      setPage(1); // always start on page 1 when popup opens
    }
  }, [visible]);

  const handleNextOrClose = () => {
    if (page === 1) {
      setPage(2);
    } else {
      onClose();
    }
  };

  const isLastPage = page === 2;

  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.backdrop}>
        {/* Loader while the teacher image is loading */}
        {!imageLoaded && (
          <View style={styles.loaderOverlay}>
            <View style={styles.loaderContent}>
              <GifLoader />
            </View>
          </View>
        )}

        <View style={[styles.container, !imageLoaded && { opacity: 0 }]}>
          <View style={styles.popupCard}>
            {/* Close “X” */}
            <TouchableOpacity style={styles.closeButton} onPress={onClose}>
              <Text style={styles.closeButtonText}>×</Text>
            </TouchableOpacity>

            <ImageBackground
              source={require("../app/assets/teacher-popup.png")}
              style={styles.image}
              resizeMode="contain"
              onLoadEnd={() => setImageLoaded(true)}
            >
              {/* Chalkboard text overlay */}
              <View style={styles.textBox}>
                {page === 1 ? (
                  <>
                    <Text style={styles.title}>Howdy!</Text>
                    <Text style={styles.body}>
                      Welcome to Student Savings. This app will help you better
                      understand your spending, build healthy money habits, and
                      make progress toward your goals without feeling overwhelmed.
                    </Text>
                  </>
                ) : (
                  <>
                    <Text style={styles.title}>Link your bank!</Text>
                    <Text style={styles.body}>
                      This is your home page where you can just relax.
                      For real-time analysis and personalized games, link your
                      bank account in Settings (top right icon).
                    </Text>
                  </>
                )}

                {/* Bottom-right Next / Close button inside chalkboard */}
                <TouchableOpacity
                  style={styles.nextButton}
                  onPress={handleNextOrClose}
                >
                  <Text style={styles.nextButtonText}>
                    {isLastPage ? "Close" : "Next"}
                  </Text>
                </TouchableOpacity>
              </View>
            </ImageBackground>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "flex-end", // anchor near bottom
    alignItems: "center",
    paddingBottom: 72, // tweak this to sit right above tab bar
  },

  // --- Loader styles ---
  loaderOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
  },
  loaderContent: {
    justifyContent: "center",
    alignItems: "center",
  },
  loaderText: {
    marginTop: 10,
    fontSize: 16,
    color: "#ffffff",
    textAlign: "center",
  },

  container: {
    width: "100%",
    alignItems: "center",
  },
  popupCard: {
    width: "90%",
    maxWidth: 420,
    alignItems: "center",
  },
  image: {
    width: "100%",
    aspectRatio: 1, // adjust if you want him a bit taller/shorter
    justifyContent: "center",
    alignItems: "flex-end",
  },
  textBox: {
    position: "absolute",
    left: "52%",
    right: "4%",
    top: "12%",
    bottom: "32%",
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  title: {
    fontSize: 21,
    fontWeight: "700",
    color: "#F5F5F5",
  },
  body: {
    marginTop: 4,
    fontSize: 12,
    color: "#F5F5F5",
  },

  // --- Chalkboard "Next / Close" button ---
  nextButton: {
    alignSelf: "flex-end",
    marginTop: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: "rgba(0,0,0,0.35)", // subtle so it feels chalkboard-y
  },
  nextButtonText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#F5F5F5",
  },

  closeButton: {
    position: "absolute",
    top: -8,
    right: -8,
    zIndex: 10,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(0,0,0,0.75)",
    justifyContent: "center",
    alignItems: "center",
  },
  closeButtonText: {
    color: "#ffffff",
    fontSize: 20,
    fontWeight: "700",
  },
});
