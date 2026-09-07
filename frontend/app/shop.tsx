import React, { useEffect, useState } from "react";
import { Platform, View } from "react-native";

import { QK, useAction, useProfile, useStore } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { billingAvailable, configureBilling, fetchStorePrices, purchaseSku, restoreNative } from "@/src/billing";
import { SkinShop } from "@/src/shop/SkinShop";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Res, Row, Screen, Txt, fmt } from "@/src/ui";
import { useToast } from "@/src/ui/Toast";

export default function ShopScreen() {
  const { colors } = useTheme();
  const toast = useToast();
  const { user } = useAuth();
  const { data: s, isLoading } = useStore();
  const { data: profile } = useProfile();
  const [prices, setPrices] = useState<Record<string, string>>({});
  const [configured, setConfigured] = useState(false);
  const crate = useAction("post", "/store/crate", [QK.store], { success: (d) => `Cassa aperta: ${Object.entries(d.granted).map(([k, v]) => `${fmt(v as number)} ${k}`).join(", ")}` });
  const verify = useAction("post", "/purchases/verify", [QK.store, QK.purchases], { success: (d) => `Verifica store completata (${d.restored.length} acquisti)` });
  const restore = useAction("post", "/purchases/restore", [QK.store, QK.purchases], { success: (d) => `Ripristinati ${d.restored.length} acquisti` });
  useEffect(() => {
    if (!user || !s) return;
    configureBilling(user.player_id).then((ok) => {
      setConfigured(ok);
      if (ok) fetchStorePrices(s.store_products.map((p: any) => p.sku)).then(setPrices).catch(() => {});
    });
  }, [user, s]);
  if (isLoading || !s || !profile) return <Loading />;
  const buy = async (sku: string) => {
    if (!configured) return toast.show("Acquisti disponibili solo nella build nativa con RevenueCat configurato", "info");
    try {
      const r = await purchaseSku(sku);
      if (r.cancelled) return;
      if (!r.ok) return toast.show("Prodotto non disponibile nello store", "error");
      verify.mutate({ product_id: sku, transaction_id: r.transactionId, store: Platform.OS === "ios" ? "app_store" : "play_store" });
    } catch (e: any) {
      toast.show(e?.message ?? "Acquisto non riuscito", "error");
    }
  };
  const priceLabel = (p: any) => prices[p.sku] ?? (Platform.OS === "web" ? `≈ €${p.reference_eur.toFixed(2)} (riferimento anteprima)` : "Prezzo dallo store");
  return (
    <Screen title="Negozio" subtitle="Nessun equipaggiamento casuale a pagamento · Prezzi localizzati dallo store" testID="shop-screen">
      <Panel variant="parchment">
        <Row style={{ justifyContent: "space-between" }}>
          <Res kind="rubies" value={profile.resources.rubies} size={18} testID="shop-rubies" />
          <Btn title="Ripristina acquisti" small variant="ghost" onPress={() => (billingAvailable && configured ? restoreNative().then(() => restore.mutate({})) : restore.mutate({}))} testID="restore-button" />
        </Row>
        {!configured ? <Txt v="small" color={colors.onSurfaceInverse}>{billingAvailable ? "Chiavi RevenueCat non configurate (input del proprietario)." : "Gli acquisti reali richiedono la build nativa iOS/Android (non Expo Go / web)."} Nessun acquisto viene simulato.</Txt> : null}
      </Panel>
      <SkinShop />
      <Txt v="h2">Rubini e pacchetti</Txt>
      {s.store_products.map((p: any) => {
        const ent = p.entitlement ? s.entitlements?.[p.entitlement] : null;
        return (
          <Panel key={p.sku} testID={`product-${p.sku}`}>
            <Row style={{ justifyContent: "space-between" }}>
              <Icon name={p.kind === "pass" ? "crown" : p.kind === "non_consumable" ? "gift" : "diamond-stone"} size={26} color={colors.res_rubies} />
              <View style={{ flex: 1 }}>
                <Txt v="h3">{p.title}</Txt>
                <Txt v="small" color={colors.muted}>{p.grant ? Object.entries(p.grant).map(([k, v]) => `${v} ${k.replace(/_/g, " ")}`).join(" · ") : `${p.duration_days} giorni · sblocca il percorso premium`}{p.exclusive_power === false ? " · nessun potere esclusivo" : ""}</Txt>
                {ent?.active ? <Txt v="small" color={colors.success}>Attivo fino a {new Date(ent.expires_at).toLocaleDateString("it-IT")}</Txt> : null}
              </View>
              <Btn title={priceLabel(p)} small variant="gold" onPress={() => buy(p.sku)} disabled={ent?.active} testID={`buy-${p.sku}`} />
            </Row>
          </Panel>
        );
      })}
      <Txt v="h2">Casse di risorse (Rubini)</Txt>
      {s.ruby_items.resource_crates.map((c: any) => (
        <Panel key={c.key} variant="wood" testID={`crate-${c.key}`}>
          <Row style={{ justifyContent: "space-between" }}>
            <View style={{ flex: 1 }}>
              <Txt v="h3">{c.key.replace(/_/g, " ")}</Txt>
              <Txt v="small" color={colors.muted}>{c.production_hours_equivalent}h di produzione di tutte le risorse · limite {c.daily_limit}/giorno</Txt>
            </View>
            <Btn title={`${c.rubies}`} icon="diamond-stone" small onPress={() => crate.mutate({ key: c.key })} loading={crate.isPending} disabled={profile.resources.rubies < c.rubies} testID={`buy-crate-${c.key}`} />
          </Row>
        </Panel>
      ))}
      <Panel>
        <Txt v="h3">Altri usi dei Rubini</Txt>
        <Txt v="small" color={colors.muted}>Accelerazioni: max(5, minuti rimanenti/3) · Ingresso dungeon extra {s.ruby_items.dungeon_extra_entry_rubies} · Attacco Titano extra {s.ruby_items.alliance_boss_extra_attack_rubies} · Ricarica energia {s.ruby_items.event_energy_refill.rubies} · Booster PvE {s.ruby_items.pve_booster.rubies} · Reset talenti {s.ruby_items.talent_respec_rubies}</Txt>
        <Txt v="small" color={colors.muted}>Cosmetici (mantelli, cornici, stendardi) si ottengono da Season Pass, Starter Bundle e imprese. Pubblicità ricompensate: {s.rewarded_ads}.</Txt>
      </Panel>
    </Screen>
  );
}
