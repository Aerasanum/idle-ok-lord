import React, { useRef, useState } from "react";
import { ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useDomain, useProfile } from "@/src/api/hooks";
import { DomainMap } from "@/src/domain/DomainMap";
import { useTheme } from "@/src/theme";
import { Loading, Panel, Progress, ResourceBar, Row, Stat, Txt } from "@/src/ui";
import { Sheet, SheetRef } from "@/src/ui/Sheet";

const GROWTH_LABEL: Record<string, string> = { camp: "Accampamento", hamlets: "Borghi", roads_and_farms: "Strade e fattorie", towers_and_forts: "Torri e forti", cities: "Città", imperial: "Dominio imperiale" };
const TERRAIN_LABEL: Record<string, string> = { plains: "Pianura", forest: "Foresta", hills: "Colline", river: "Fiume", mountains: "Montagne", village: "Villaggio", mine: "Miniera", ruins: "Rovine", fort: "Forte", city: "Città" };

export default function DomainTab() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { data: d, isLoading } = useDomain();
  const { data: profile } = useProfile();
  const sheet = useRef<SheetRef>(null);
  const [tile, setTile] = useState<any>(null);
  if (isLoading || !d || !profile) return <Loading label="Disegno la mappa..." />;
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }} testID="domain-screen">
      <View style={{ paddingTop: insets.top, backgroundColor: colors.surfaceSecondary }}>
        <ResourceBar resources={profile.resources} compact />
      </View>
      <ScrollView contentContainerStyle={{ padding: 12, paddingBottom: 24, gap: 12 }} showsVerticalScrollIndicator={false}>
        <Row style={{ justifyContent: "space-between" }}>
          <View>
            <Txt v="h1">Dominio personale</Txt>
            <Txt v="caption">{GROWTH_LABEL[d.growth_stage]} · colore araldico</Txt>
          </View>
          <View style={{ width: 28, height: 28, backgroundColor: d.heraldic_color, borderWidth: 2, borderColor: colors.gold }} />
        </Row>
        <DomainMap tiles={d.tiles} ownedCount={d.owned} heraldicColor={d.heraldic_color} growth={d.growth_stage} selected={tile?.index} onSelect={(t) => { setTile(t); sheet.current?.present(); }} />
        <Panel testID="domain-stats">
          <Row style={{ justifyContent: "space-around" }}>
            <Stat label="Tessere" value={`${d.owned}/${d.total}`} testID="domain-owned" />
            <Stat label="Bonus produzione" value={`+${d.production_bonus_pct}%`} color={colors.res_event_tokens} testID="domain-bonus" />
            <Stat label="Tetto" value={`${d.bonus_cap_pct}%`} />
          </Row>
          <Progress value={d.owned} max={d.total} label={d.next_tile_at_stage ? `Prossima tessera allo stage ${d.next_tile_at_stage} (record ${d.highest_cleared})` : "Dominio completo"} />
        </Panel>
        <Panel variant="wood">
          <Txt v="small" color={colors.muted}>Ogni 2 stage conquistati il tuo Dominio si espande di una tessera adiacente. Ogni 10 tessere: +5% produzione (max +50%). La mappa dipinta mostra strade, forti, villaggi e città che crescono con il territorio.</Txt>
        </Panel>
      </ScrollView>
      <Sheet ref={sheet} title={tile ? `${TERRAIN_LABEL[tile.terrain] ?? tile.terrain} (${tile.x}, ${tile.y})` : ""} snap={["35%"]} testID="tile-sheet">
        {tile ? (
          <View style={{ gap: 6 }}>
            <Txt v="body">{tile.owned ? "Territorio del tuo Dominio." : tile.order === d.owned ? `Prossima conquista: si sblocca allo stage ${tile.unlock_stage}.` : `Si sblocca conquistando lo stage ${tile.unlock_stage}.`}</Txt>
            <Txt v="small" color={colors.muted}>Ordine di espansione #{tile.order + 1}</Txt>
          </View>
        ) : null}
      </Sheet>
    </View>
  );
}
