import React, { useState } from "react";
import { View } from "react-native";

import { QK, useAchievements, useAction } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Chip, ChipRow, Icon, Loading, Panel, Progress, Row, Screen, Txt, fmt } from "@/src/ui";

export default function AchievementsScreen() {
  const { colors } = useTheme();
  const { data: a, isLoading } = useAchievements();
  const [cat, setCat] = useState("all");
  const claim = useAction("post", "/achievements/claim", [QK.achievements], { success: (d) => `+${d.rubies} Rubini` });
  if (isLoading || !a) return <Loading />;
  const list = a.achievements.filter((x: any) => cat === "all" || x.category === cat);
  const claimed = a.achievements.filter((x: any) => x.claimed).reduce((s: number, x: any) => s + x.rubies, 0);
  return (
    <Screen title="Imprese" subtitle={`${claimed}/${a.total_rubies} Rubini raccolti`} testID="achievements-screen">
      <View style={{ marginHorizontal: -16 }}>
        <ChipRow>
          <Chip label="Tutte" selected={cat === "all"} onPress={() => setCat("all")} testID="ach-filter-all" />
          {a.categories.map((c: string) => <Chip key={c} label={a.category_labels?.[c] ?? c} selected={cat === c} onPress={() => setCat(c)} testID={`ach-filter-${c}`} />)}
        </ChipRow>
      </View>
      {list.map((x: any) => (
        <Panel key={x.key} variant={x.claimed ? "wood" : "iron"} testID={`achievement-${x.key}`}>
          <Row style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
            <Icon name={x.claimed ? "trophy" : x.unlocked ? "trophy-outline" : "lock-outline"} size={22} color={x.claimed ? colors.goldBright : x.unlocked ? colors.success : colors.muted} />
            <View style={{ flex: 1, gap: 2 }}>
              <Row style={{ justifyContent: "space-between" }}>
                <Txt v="h3" testID={`ach-title-${x.key}`}>{x.title}</Txt>
                <Txt v="small" color={colors.muted}>{x.category_label}</Txt>
              </Row>
              <Txt v="small" testID={`ach-desc-${x.key}`}>{x.description}</Txt>
              <Progress value={x.value} max={x.threshold} label={`${fmt(x.value)} / ${fmt(x.threshold)} ${x.unit_label}`} height={6} />
              <Txt v="small" color={x.claimed ? colors.muted : x.unlocked ? colors.success : colors.warning} testID={`ach-status-${x.key}`}>{x.status}</Txt>
            </View>
            <Btn title={x.claimed ? "✓" : x.unlocked ? `Ritira ${x.rubies}` : `${x.rubies}`} icon={x.claimed ? undefined : "diamond-stone"} small variant={x.unlocked && !x.claimed ? "gold" : "secondary"} disabled={!x.unlocked || x.claimed} onPress={() => claim.mutate({ key: x.key })} testID={`claim-${x.key}`} />
          </Row>
        </Panel>
      ))}
    </Screen>
  );
}
