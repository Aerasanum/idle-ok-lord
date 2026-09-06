// RevenueCat bridge. Native-only (react-native-purchases requires a dev/production build). No fake success: when the
// native module is unavailable we report "unavailable" and the UI explains that the store requires the native build.
import Constants from "expo-constants";
import { Platform } from "react-native";

const isExpoGo = Constants.executionEnvironment === "storeClient";
let Purchases: any = null;
if (!isExpoGo && Platform.OS !== "web") {
  try {
    Purchases = require("react-native-purchases").default;
  } catch {
    Purchases = null;
  }
}

export const billingAvailable = !!Purchases;

export async function configureBilling(playerId: string): Promise<boolean> {
  if (!Purchases) return false;
  const key = Platform.OS === "ios" ? process.env.EXPO_PUBLIC_RC_IOS_KEY : process.env.EXPO_PUBLIC_RC_ANDROID_KEY;
  if (!key) return false;
  Purchases.configure({ apiKey: key, appUserID: playerId });
  return true;
}

export async function fetchStorePrices(skus: string[]): Promise<Record<string, string>> {
  if (!Purchases) return {};
  const products = await Purchases.getProducts(skus);
  const out: Record<string, string> = {};
  for (const p of products) out[p.identifier] = p.priceString;
  return out;
}

export async function purchaseSku(sku: string): Promise<{ ok: boolean; cancelled?: boolean; transactionId?: string }> {
  if (!Purchases) return { ok: false };
  try {
    const products = await Purchases.getProducts([sku]);
    if (!products.length) return { ok: false };
    const res = await Purchases.purchaseStoreProduct(products[0]);
    return { ok: true, transactionId: res?.transaction?.transactionIdentifier };
  } catch (e: any) {
    if (e?.userCancelled) return { ok: false, cancelled: true };
    throw e;
  }
}

export async function restoreNative(): Promise<boolean> {
  if (!Purchases) return false;
  await Purchases.restorePurchases();
  return true;
}
