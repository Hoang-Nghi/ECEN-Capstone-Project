// app/services/plaidApi.tsx
import { auth } from "../firebaseConfig";

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  "https://capstone-backend-1041336188288.us-central1.run.app";

/**
 * Get Firebase ID token for authenticated requests
 */
async function getAuthToken(): Promise<string> {
  const user = auth.currentUser;
  if (!user) {
    throw new Error("User not authenticated. Please sign in first.");
  }
  return await user.getIdToken();
}

/**
 * Generic POST request with Firebase auth
 */
async function post<T>(path: string, body?: any): Promise<T> {
  const token = await getAuthToken();
  const url = `${BASE_URL}${path}`;

  console.log("[plaidApi] POST", url);

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body ?? {}),
  });

  const text = await res.text();
  console.log(
    "[plaidApi] status:",
    res.status,
    "response:",
    text.substring(0, 200)
  );

  let data: any = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (e) {
    console.error("[plaidApi] Failed to parse JSON:", e);
  }

  if (!res.ok) {
    const errorMsg =
      data?.error || `Request failed: ${res.status} ${res.statusText}`;
    console.error("[plaidApi] Error:", errorMsg);
    throw new Error(errorMsg);
  }

  return data as T;
}

/**
 * Create Plaid Link Token
 * Endpoint: POST /api/plaid/create_link_token
 */
export async function createLinkToken() {
  const user = auth.currentUser;
  if (!user) {
    throw new Error("User not authenticated. Please sign in first.");
  }

  return post<{ link_token: string }>("/api/plaid/create_link_token", {
    user_id: user.uid,
  });
}

/**
 * Exchange Public Token for Access Token
 * Endpoint: POST /api/plaid/exchange_public_token
 */
export async function exchangePublicToken(publicToken: string) {
  return post<{
    status: string;
    item_id?: string;
    added?: number;
    modified?: number;
  }>("/api/plaid/exchange_public_token", {
    public_token: publicToken,   // ✔ backend expects this ONLY
  });
}


/**
 * Create Sandbox Item (Testing Only)
 * Endpoint: POST /api/plaid/sandbox/instant_item
 */
export async function createSandboxItem() {
  const user = auth.currentUser;
  if (!user) {
    throw new Error("User not authenticated. Please sign in first.");
  }

  return post<{ public_token: string }>("/api/plaid/sandbox/instant_item", {
    user_id: user.uid,
  });
}

/**
 * Manually Sync Transactions
 * Endpoint: POST /api/plaid/transactions/sync
 */
export async function syncTransactions() {
  const user = auth.currentUser;
  if (!user) {
    throw new Error("User not authenticated. Please sign in first.");
  }

  return post<{
    added: number;
    modified: number;
    removed: number;
    cursor?: string;
  }>("/api/plaid/transactions/sync", {
    user_id: user.uid,
  });
}

/**
 * Check Plaid Connection Status
 * Endpoint: POST /api/plaid/status
 */
export async function getPlaidStatus() {
  const user = auth.currentUser;
  if (!user) {
    throw new Error("User not authenticated. Please sign in first.");
  }

  return post<{
    item_id?: string;
    has_connection: boolean;
    last_sync?: string;
  }>("/api/plaid/status", {
    user_id: user.uid,
  });
}
