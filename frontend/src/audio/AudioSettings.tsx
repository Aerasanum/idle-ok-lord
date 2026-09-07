// Audio bootstrap + music volume UI. Mounted once in the root layout; volume comes from the player profile (server) with a local cache.
import React, { useEffect, useState } from "react";
import { View } from "react-native";

import { useProfile } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Row, Txt } from "@/src/ui";
import { getVolumes, initAudio, setVolumes, stopMusic, subscribeAudio } from "./index";

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
  const music = profile?.settings?.music_volume;
  useEffect(() => {
    if (typeof music === "number") initAudio({ music_volume: music });
  }, [music]);
  return null;
}

export function useAudioVolumes() {
  const [v, setV] = useState(getVolumes());
  useEffect(() => subscribeAudio(() => setV(getVolumes())), []);
  return v;
}

export function AudioSettings() {
  const { colors } = useTheme();
  const v = useAudioVolumes();
  const pct = Math.round(v.music * 100);
  return (
    <View style={{ gap: 6 }} testID="audio-settings">
      <Row style={{ justifyContent: "space-between" }} testID="music-volume">
        <Row>
          <Icon name={pct === 0 ? "volume-off" : "music"} size={18} color={colors.goldBright} />
          <Txt v="body">Musica</Txt>
        </Row>
        <Txt v="bodyBold" testID="music-volume-value">{pct}%</Txt>
      </Row>
      <Row>
        <Btn title="−" small variant="secondary" onPress={() => setVolumes({ music: Math.max(0, v.music - 0.1) })} testID="music-volume-minus" />
        <View style={{ flex: 1, height: 10, borderRadius: 5, backgroundColor: colors.scrim, borderWidth: 1, borderColor: colors.wood, overflow: "hidden" }}>
          <View style={{ width: `${pct}%`, height: "100%", backgroundColor: colors.goldBright }} />
        </View>
        <Btn title="+" small variant="secondary" onPress={() => setVolumes({ music: Math.min(1, v.music + 0.1) })} testID="music-volume-plus" />
      </Row>
      <Txt v="small" color={colors.muted}>Colonna sonora per regione. Gli effetti sonori sono disattivati.</Txt>
    </View>
  );
}
