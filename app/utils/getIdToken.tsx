import { getAuth } from "firebase/auth";

export async function getFirebaseIdToken() {
  const auth = getAuth();
  const user = auth.currentUser;
  if (!user) throw new Error("Not logged in");
  return user.getIdToken(/* forceRefresh */ true);
}
