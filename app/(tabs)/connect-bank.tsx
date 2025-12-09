// app/(tabs)/connect-bank.tsx

import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

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

import { useAuth } from "../hooks/useAuth";
import {
  createLinkToken,
  exchangePublicToken
} from "../services/plaidApi";

export default function ConnectBankScreen() {
  const { user, loading: authLoading } = useAuth();

  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [linked, setLinked] = useState(false);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  const showAlert = (title: string, message: string) => {
    Alert.alert(title, message, [{ text: "OK" }], { cancelable: true });
  };

  const handleLinkSuccess = useCallback(async (success: LinkSuccess) => {
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
  }, []);


  const handleLinkExit = useCallback((exit: LinkExit) => {
    console.log("[Plaid] ℹ️ onExit:", exit);

    const error = exit.error;
    if (error) {
      // NOTE: the correct property is displayMessage (camelCase)
      const message =
        error.displayMessage ||
        error.errorMessage ||
        "Unable to connect. Please try again.";

      showAlert("Plaid error", message);
    } else {
      // User closed the flow without an error
      console.log("[Plaid] User exited without error.");
    }
  }, []);

  const createTokenConfiguration = useCallback(
    (token: string): LinkTokenConfiguration => ({
      token,
      // Hide native spinner if true – we'll show our own
      noLoadingState: false,
    }),
    []
  );

  const createOpenProps = useCallback(
    (): LinkOpenProps => ({
      onSuccess: handleLinkSuccess,
      onExit: handleLinkExit,
      iOSPresentationStyle: LinkIOSPresentationStyle.MODAL,
      logLevel: LinkLogLevel.ERROR,
    }),
    [handleLinkExit, handleLinkSuccess]
  );

  // ---------------------------------------------------------------------------
  // Fetch link token whenever we have a user
  // ---------------------------------------------------------------------------

  const fetchLinkToken = useCallback(async () => {
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
  }, [createTokenConfiguration, user]);

  useEffect(() => {
    if (user) {
      fetchLinkToken();
    }
  }, [user, fetchLinkToken]);

  // ---------------------------------------------------------------------------
  // Button handler – open Plaid
  // ---------------------------------------------------------------------------

  const onConnectPress = useCallback(() => {
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
  }, [createOpenProps, linkToken]);

  // ---------------------------------------------------------------------------
  // UI
  // ---------------------------------------------------------------------------

  if (authLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text style={styles.loadingText}>Loading your account…</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Connect your bank</Text>

      <Text style={styles.subtitle}>
        Securely connect your bank with Plaid so Student Savings can analyze your
        spending and help you hit your money goals.
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Why we use Plaid</Text>
        <Text style={styles.cardBody}>
          Plaid lets you connect your bank without sharing your credentials with
          us. You&apos;ll be redirected to your bank&apos;s secure login and we
          only receive read-only data needed to power your insights.
        </Text>
      </View>

      <Pressable
        style={[styles.button, (busy || !linkToken) && styles.buttonDisabled]}
        onPress={onConnectPress}
        disabled={busy || !linkToken}
      >
        {busy ? (
          <ActivityIndicator size="small" />
        ) : (
          <Text style={styles.buttonText}>
            {linked ? "Reconnect bank" : "Connect bank account"}
          </Text>
        )}
      </Pressable>

      {linked && (
        <Text style={styles.statusText}>
          ✅ Bank connected. You can reconnect at any time if you change
          accounts.
        </Text>
      )}

      {!linkToken && !busy && (
        <Text style={styles.helperText}>
          We&apos;re having trouble getting a link token right now. Pull down to
          refresh or try again in a few minutes.
        </Text>
      )}
    </ScrollView>
  );
}

// -----------------------------------------------------------------------------
// Styles
// -----------------------------------------------------------------------------

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 24,
    backgroundColor: "#050816",
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#050816",
  },
  loadingText: {
    marginTop: 12,
    color: "#e5e7eb",
    fontSize: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#f9fafb",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: "#9ca3af",
    marginBottom: 24,
  },
  card: {
    backgroundColor: "#0b1120",
    borderRadius: 16,
    padding: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: "#1f2937",
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#e5e7eb",
    marginBottom: 6,
  },
  cardBody: {
    fontSize: 14,
    color: "#9ca3af",
    lineHeight: 20,
  },
  button: {
    marginTop: 4,
    paddingVertical: 14,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#22c55e",
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "#022c22",
    fontSize: 16,
    fontWeight: "700",
  },
  statusText: {
    marginTop: 16,
    fontSize: 14,
    color: "#bbf7d0",
  },
  helperText: {
    marginTop: 16,
    fontSize: 13,
    color: "#fbbf24",
  },
});
