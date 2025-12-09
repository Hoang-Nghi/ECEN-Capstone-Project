// app/settings.tsx
// Settings page with color palette picker + existing settings + Plaid button

import Ionicons from "@expo/vector-icons/Ionicons";
import { Link, useRouter } from "expo-router";
import { deleteUser, getAuth, sendPasswordResetEmail } from "firebase/auth";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Button,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { LogoutButton } from "../hooks/logout";
import { useAuth } from "../hooks/useAuth";

// ⬇️ NEW: Plaid imports
import {
  create,
  LinkExit,
  LinkIOSPresentationStyle,
  LinkLogLevel,
  LinkOpenProps,
  LinkSuccess,
  LinkTokenConfiguration,
  open,
} from "react-native-plaid-link-sdk";

// ⬇️ NEW: Plaid API imports
import { createLinkToken, exchangePublicToken } from "../services/plaidApi";

// ⬇️ NEW: import theme hook + types
import { ThemeName, useTheme } from "../../_theme";

interface SettingItemProps {
  title?: string;
  value: boolean;
  onValueChange: (v: boolean) => void;
}

// Re-usable row with a switch, now themed
const SettingItem: React.FC<SettingItemProps> = ({
  title = "Example title",
  value,
  onValueChange,
}) => {
  const { theme } = useTheme();

  return (
    <View
      style={[
        styles.settingItem,
        { borderBottomColor: theme.subtleText + "33" },
      ]}
    >
      <Text style={[styles.settingTitle, { color: theme.text }]}>{title}</Text>
      <Switch value={value} onValueChange={onValueChange} />
    </View>
  );
};

// ⬇️ Palette options – make sure these match your ThemeName union
const PALETTES: { id: ThemeName; label: string; description: string }[] = [
  {
    id: "green",
    label: "Calm Green",
    description: "Relaxing greens with soft neutrals (default).",
  },
  {
    id: "purple",
    label: "Cozy Purple",
    description: "Soft purples with warm, cozy accents.",
  },
  {
    id: "dark",
    label: "Dark Mode",
    description: "Low-glare theme for night use.",
  },
  // Add more palettes if you define them in theme.ts:
  // { id: "blue", label: "Cool Blue", description: "Cool blues for a focused look." },
];

const SettingsPage: React.FC = () => {

  // ⬇️ NEW: Plaid state
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [linked, setLinked] = useState(false);

  const { user } = useAuth();
  const auth = getAuth();
  const router = useRouter();

  const { theme, setThemeName } = useTheme(); // 👈 from ThemeProvider

  // ---------------------------------------------------------------------------
  // Plaid helpers
  // ---------------------------------------------------------------------------

  const showAlert = (title: string, message: string) => {
    Alert.alert(title, message, [{ text: "OK" }], { cancelable: true });
  };

  const handleLinkSuccess = async (success: LinkSuccess) => {
    try {
      setBusy(true);
      console.log("[Plaid] ✅ onSuccess:", success);

      const publicToken = success.publicToken;
      if (!publicToken) {
        showAlert("Connection error", "No public token returned from Plaid.");
        return;
      }

      // send token to backend
      const resp = await exchangePublicToken(publicToken);
      console.log("[Plaid] exchangePublicToken response:", resp);

      setLinked(true);
      showAlert("Bank connected", "Your bank account is now connected!");
    } catch (err) {
      console.error("[Plaid] ❌ Error handling success:", err);
      showAlert("Connection error", "Something went wrong saving your bank.");
    } finally {
      setBusy(false);
    }
  };

  const handleLinkExit = (exit: LinkExit) => {
    console.log("[Plaid] ℹ️ onExit:", exit);

    const error = exit.error;
    if (error) {
      const message =
        error.displayMessage ||
        error.errorMessage ||
        "Unable to connect. Please try again.";

      showAlert("Plaid error", message);
    } else {
      // User closed the flow without an error
      console.log("[Plaid] User exited without error.");
    }
  };

  const createTokenConfiguration = (
    token: string
  ): LinkTokenConfiguration => ({
    token,
    noLoadingState: false, // we'll still let Plaid show its native spinner
  });

  const createOpenProps = (): LinkOpenProps => ({
    onSuccess: handleLinkSuccess,
    onExit: handleLinkExit,
    iOSPresentationStyle: LinkIOSPresentationStyle.MODAL,
    logLevel: LinkLogLevel.ERROR,
  });

  const fetchLinkToken = async () => {
    if (!user) return;
    try {
      setBusy(true);
      console.log("[Plaid] 🎯 Requesting link token for user:", user.uid);
      const res = await createLinkToken();
      console.log("[Plaid] ✅ createLinkToken response:", res);

      if (!res?.link_token) {
        throw new Error("No link_token returned from backend");
      }

      setLinkToken(res.link_token);

      // Preload Plaid using the link token
      const tokenConfig = createTokenConfiguration(res.link_token);
      create(tokenConfig);
      console.log("[Plaid] ✅ Link preloaded via create()");
    } catch (err) {
      console.error("[Plaid] ❌ Failed to create link token:", err);
      showAlert(
        "Connection error",
        "We couldn't start the bank connection right now. Please try again in a minute."
      );
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    fetchLinkToken();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const onConnectPress = () => {
    if (!linkToken) {
      showAlert(
        "Missing link token",
        "We couldn't prepare the bank connection. Please try again."
      );
      return;
    }

    console.log("[Plaid] 🔓 Opening Plaid Link…");
    const openProps = createOpenProps();
    open(openProps);
  };

  // ---------------------------------------------------------------------------
  // Non-Plaid handlers
  // ---------------------------------------------------------------------------


  const handleChangePassword = async () => {
    try {
      if (user?.email) {
        await sendPasswordResetEmail(auth, user.email);
        Alert.alert(
          "Password Reset Email Sent",
          `Check your inbox at ${user.email}`
        );
      }
    } catch (error: any) {
      Alert.alert("Error", error.message);
    }
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      "Are you sure?",
      "This will permanently delete your account.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              const currentUser = auth.currentUser;
              if (currentUser) {
                await deleteUser(currentUser);
                Alert.alert("Account deleted");
                router.replace("/signup");
              }
            } catch (error: any) {
              Alert.alert("Error", error.message);
            }
          },
        },
      ],
      { cancelable: true }
    );
  };

  // Optional: later you can wire darkMode toggle to a "dark" palette:
  // const handleDarkModeToggle = (value: boolean) => {
  //   setDarkModeEnabled(value);
  //   setThemeName(value ? "dark" : "green");
  // };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.background }]}
      contentInsetAdjustmentBehavior="automatic"
    >
      {/* Back to Home */}
      <Link href="/" asChild>
        <TouchableOpacity
          style={[
            styles.backButton,
            {
              backgroundColor: theme.card,
              borderColor: theme.subtleText + "33",
            },
          ]}
        >
          <Ionicons name="arrow-back" size={20} color={theme.text} />
          <Text style={[styles.backButtonText, { color: theme.text }]}>
            Home
          </Text>
        </TouchableOpacity>
      </Link>

      <Text style={[styles.header, { color: theme.text }]}>Settings</Text>

      {/* 🎨 App Color Palette section */}
      <Text style={[styles.sectionLabel, { color: theme.subtleText }]}>
        Appearance
      </Text>

      <View style={styles.paletteList}>
        {PALETTES.map((palette) => {
          const isActive = theme.name === palette.id;
          return (
            <TouchableOpacity
              key={palette.id}
              style={[
                styles.paletteCard,
                {
                  backgroundColor: theme.card,
                  borderColor: isActive
                    ? theme.accent
                    : theme.subtleText + "33",
                },
              ]}
              onPress={() => setThemeName(palette.id)}
            >
              <View style={styles.paletteHeaderRow}>
                <Text style={[styles.paletteLabel, { color: theme.text }]}>
                  {palette.label}
                </Text>
                {isActive && (
                  <View
                    style={[
                      styles.activeBadge,
                      { backgroundColor: theme.accent },
                    ]}
                  >
                    <Text style={styles.activeBadgeText}>Active</Text>
                  </View>
                )}
              </View>
              <Text
                style={[
                  styles.paletteDescription,
                  { color: theme.subtleText },
                ]}
              >
                {palette.description}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* 💳 Bank connections section – Plaid button lives here now */}
      <Text style={[styles.sectionLabel, { color: theme.subtleText }]}>
        Bank Connections
      </Text>

      <View
        style={[
          styles.bankCard,
          {
            backgroundColor: theme.card,
            borderColor: theme.subtleText + "33",
          },
        ]}
      >
        <Text style={[styles.bankTitle, { color: theme.text }]}>
          Connect your bank
        </Text>
        <Text
          style={[styles.bankDescription, { color: theme.subtleText }]}
        >
          Securely connect your bank with Plaid so Student Savings can
          analyze your spending and help you hit your money goals.
        </Text>

        <TouchableOpacity
          style={[
            styles.bankButton,
            (busy || !linkToken) && styles.bankButtonDisabled,
          ]}
          onPress={onConnectPress}
          disabled={busy || !linkToken}
        >
          {busy ? (
            <ActivityIndicator size="small" />
          ) : (
            <Text style={styles.bankButtonText}>
              {linked ? "Reconnect bank" : "Connect bank account"}
            </Text>
          )}
        </TouchableOpacity>

        {linked && (
          <Text style={[styles.bankStatusText, { color: theme.accent }]}>
            ✅ Bank connected. You can reconnect at any time if you change
            accounts.
          </Text>
        )}

        {!linkToken && !busy && (
          <Text
            style={[
              styles.bankHelperText,
              { color: theme.subtleText },
            ]}
          >
            We&apos;re having trouble getting a link token right now. Try
            again in a minute or pull down to refresh.
          </Text>
        )}
      </View>

      {/* Buttons */}
      <View style={styles.buttonGroup}>
        <Button
          title="Change Password"
          onPress={handleChangePassword}
          color={theme.accent}
        />
      </View>
      <View style={styles.buttonGroup}>
        <Button
          title="Delete Account"
          onPress={handleDeleteAccount}
          color="#cc0000"
        />
      </View>

      <LogoutButton />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
  },
  backButton: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 20,
    padding: 8,
    borderRadius: 6,
    alignSelf: "flex-start",
    borderWidth: 1,
  },
  backButtonText: {
    marginLeft: 8,
    fontSize: 16,
  },
  header: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 16,
  },
  sectionLabel: {
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  paletteList: {
    marginBottom: 24,
  },
  paletteCard: {
    borderRadius: 12,
    padding: 12,
    borderWidth: 1.5,
    marginBottom: 10,
  },
  paletteHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  paletteLabel: {
    fontSize: 16,
    fontWeight: "600",
  },
  paletteDescription: {
    fontSize: 13,
  },
  activeBadge: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  activeBadgeText: {
    color: "#fff",
    fontSize: 11,
    fontWeight: "600",
    textTransform: "uppercase",
  },
  // OLD navRow removed – Plaid lives inline now
  navRow: {
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
  },
  navRowText: {
    fontSize: 16,
  },
  settingItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 15,
    borderBottomWidth: 1,
  },
  settingTitle: {
    fontSize: 16,
  },
  buttonGroup: {
    marginVertical: 10,
  },
  // 💳 Bank connect styles
  bankCard: {
    borderRadius: 12,
    padding: 14,
    borderWidth: 1.5,
    marginBottom: 20,
  },
  bankTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 4,
  },
  bankDescription: {
    fontSize: 13,
    marginBottom: 12,
  },
  bankButton: {
    marginTop: 4,
    paddingVertical: 12,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
    color: "#000",
  },
  bankButtonDisabled: {
    opacity: 0.6,
  },
  bankButtonText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#ffffff",
  },
  bankStatusText: {
    marginTop: 10,
    fontSize: 13,
  },
  bankHelperText: {
    marginTop: 10,
    fontSize: 12,
  },
});

export default SettingsPage;
