// Audio bootstrap + volume UI. Mounted once in the root layout; volumes come from the player profile (server) with a local cache.
import React, { useEffect, useState } from "react";
import { View } from "react-native";

import { useProfile } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Icon, IconName, Row, Txt } from "@/src/ui";
import { getVolumes, initAudio, playSfx, setVolumes, stopMusic, subscribeAudio } from "./index";

export function AudioBootstrap() {
  const { user } = useAuth();
  useEffect(() => {
    initAudio();
  }, []);
  useEffect(() => {
    if (!user) stopMusic();
  }, [user]);
  return user ? <ProfileVolumeSync /> : null;
}

function ProfileVolumeSync() {
  const { data: profile } = useProfile();
  const music = profile?.settings?.music_volume, sfx = profile?.settings?.sfx_volume;
  useEffect(() => {
    if (typeof music === "number" || typeof sfx === "number") initAudio({ music_volume: music, sfx_volume: sfx });
  }, [music, sfx]);
  return null;
}

export function useAudioVolumes() {
  const [v, setV] = useState(getVolumes());
  useEffect(() => subscribeAudio(() => setV(getVolumes())), []);
  return v;
}

function VolumeRow({ label, icon, value, onChange, testID }: { label: string; icon: IconName; value: number; onChange: (v: number) => void; testID: string }) {
  const { colors } = useTheme();
  const pct = Math.round(value * 100);
  return (
    <View style={{ gap: 6 }} testID={testID}>
      <Row style={{ justifyContent: "space-between" }}>
        <Row>
          <Icon name={pct === 0 ? "volume-off" : icon} size={18} color={colors.goldBright} />
          <Txt v="body">{label}</Txt>
        </Row>
        <Txt v="bodyBold" testID={`${testID}-value`}>{pct}%</Txt>
      </Row>
      <Row>
        <Btn title="−" small variant="secondary" onPress={() => onChange(Math.max(0, value - 0.1))} testID={`${testID}-minus`} />
        <View style={{ flex: 1, height: 10, borderRadius: 5, backgroundColor: colors.scrim, borderWidth: 1, borderColor: colors.wood, overflow: "hidden" }}>
          <View style={{ width: `${pct}%`, height: "100%", backgroundColor: colors.goldBright }} />
        </View>
        <Btn title="+" small variant="secondary" onPress={() => onChange(Math.min(1, value + 0.1))} testID={`${testID}-plus`} />
      </Row>
    </View>
  );
}

export function AudioSettings() {
  const v = useAudioVolumes();
  return (
    <View style={{ gap: 12 }} testID="audio-settings">
      <VolumeRow label="Musica" icon="music" value={v.music} onChange={(music) => setVolumes({ music })} testID="music-volume" />
      <VolumeRow label="Effetti sonori" icon="volume-high" value={v.sfx} onChange={(sfx) => { setVolumes({ sfx }); playSfx("coin"); }} testID="sfx-volume" />
    </View>
  );
}
