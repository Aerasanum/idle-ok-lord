import { BottomSheetBackdrop, BottomSheetModal, BottomSheetScrollView } from "@gorhom/bottom-sheet";
import React, { forwardRef, useCallback } from "react";
import { View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { spacing, useTheme } from "@/src/theme";
import { Txt } from "@/src/ui";

export type SheetRef = BottomSheetModal;

/** Ornate parchment bottom sheet (Building Detail, tile info, item detail...). */
export const Sheet = forwardRef<BottomSheetModal, { title?: string; children: React.ReactNode; snap?: (string | number)[]; testID?: string }>(({ title, children, snap = ["60%", "90%"], testID }, ref) => {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const backdrop = useCallback((props: any) => <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} opacity={0.6} />, []);
  return (
    <BottomSheetModal ref={ref} snapPoints={snap} enablePanDownToClose backdropComponent={backdrop} backgroundStyle={{ backgroundColor: colors.surfaceSecondary, borderWidth: 2, borderColor: colors.gold, borderRadius: 12 }} handleIndicatorStyle={{ backgroundColor: colors.gold, width: 56 }}>
      <BottomSheetScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 24, gap: spacing.md }} testID={testID}>
        {title ? (
          <View style={{ borderBottomWidth: 1, borderColor: colors.divider, paddingBottom: 8 }}>
            <Txt v="h2">{title}</Txt>
          </View>
        ) : null}
        {children}
      </BottomSheetScrollView>
    </BottomSheetModal>
  );
});
Sheet.displayName = "Sheet";
