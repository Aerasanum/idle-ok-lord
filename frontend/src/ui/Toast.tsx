import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { Text, View } from "react-native";
import Animated, { FadeInUp, FadeOutUp } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { fonts, makeStyles } from "@/src/theme";

type Kind = "success" | "error" | "info";
type ToastItem = { id: number; text: string; kind: Kind };
const Ctx = createContext<{ show: (text: string, kind?: Kind) => void }>({ show: () => {} });

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const idRef = useRef(1);
  const show = useCallback((text: string, kind: Kind = "info") => {
    const id = idRef.current++;
    setItems((s) => [...s.slice(-2), { id, text, kind }]);
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), 2600);
  }, []);
  const value = useMemo(() => ({ show }), [show]);
  return (
    <Ctx.Provider value={value}>
      {children}
      <ToastHost items={items} />
    </Ctx.Provider>
  );
}

function ToastHost({ items }: { items: ToastItem[] }) {
  const s = useStyles();
  const insets = useSafeAreaInsets();
  if (!items.length) return null;
  return (
    <View pointerEvents="none" style={[s.host, { top: insets.top + 8 }]} testID="toast-host">
      {items.map((t) => (
        <Animated.View key={t.id} entering={FadeInUp} exiting={FadeOutUp} style={[s.toast, t.kind === "error" && s.error, t.kind === "success" && s.success]} testID={`toast-${t.kind}`}>
          <Text style={s.text}>{t.text}</Text>
        </Animated.View>
      ))}
    </View>
  );
}

export const useToast = () => useContext(Ctx);

const useStyles = makeStyles((c) => ({
  host: { position: "absolute", left: 16, right: 16, alignItems: "center", gap: 6 },
  toast: { backgroundColor: c.surfaceInverse, borderColor: c.borderStrong, borderWidth: 2, borderRadius: 6, paddingHorizontal: 14, paddingVertical: 10, maxWidth: 420 },
  error: { borderColor: c.error },
  success: { borderColor: c.success },
  text: { color: c.onSurfaceInverse, fontFamily: fonts.bodyMedium, fontSize: 14 },
}));
