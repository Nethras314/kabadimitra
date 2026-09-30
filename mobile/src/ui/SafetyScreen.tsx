// Safety guidance: pictogram-first, one rule per card, DO vs NEVER.
// Critical items sort to the top. Safe to render with no connectivity.

import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { ApiClient, SafetyTopic } from '../api/client';
import { Locale, t } from '../i18n/locales';
import { Banner, BigButton, Card, Glyph, ScreenTitle, theme } from './components';

export function SafetyScreen({
  api,
  locale,
  cached,
  onCache,
}: {
  api: ApiClient;
  locale: Locale;
  cached?: SafetyTopic[] | null;
  onCache?: (topics: SafetyTopic[]) => void;
}) {
  const [topics, setTopics] = useState<SafetyTopic[]>(cached ?? []);
  const [offline, setOffline] = useState(!cached?.length);
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.safetyTopics(locale);
      setTopics(res.topics);
      setOffline(false);
      onCache?.(res.topics);
    } catch {
      setOffline(true);
    }
  }, [api, locale, onCache]);

  useEffect(() => {
    load();
  }, [load]);

  const tone = (s: SafetyTopic['severity']) =>
    s === 'critical' ? 'bad' : s === 'high' ? 'warn' : 'neutral';

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }}>
      <ScreenTitle text={t(locale, 'safety_title')} />
      {offline ? <Banner tone="warn" text={t(locale, 'prices_offline')} /> : null}

      {topics.map((topic) => {
        const isOpen = open === topic.id;
        const dont = topic.pictograms.find((p) => p.kind === 'dont');
        const doIcon = topic.pictograms.find((p) => p.kind === 'do');
        return (
          <Card key={topic.id} testID={`safety-topic-${topic.code}`}>
            <Text style={[styles.title, tone(topic.severity) === 'bad' && { color: theme.red }]}>
              {topic.title}
            </Text>
            {topic.short_text ? <Text style={styles.short}>{topic.short_text}</Text> : null}

            <View style={styles.iconRow}>
              {dont ? (
                <View style={styles.iconBox}>
                  <Glyph name={dont.icon_key} size={34} />
                  <Text style={styles.never}>{t(locale, 'safety_dont')}</Text>
                </View>
              ) : null}
              {doIcon ? (
                <View style={styles.iconBox}>
                  <Glyph name={doIcon.icon_key} size={34} />
                  <Text style={styles.do}>{t(locale, 'safety_do')}</Text>
                </View>
              ) : null}
            </View>

            {isOpen ? (
              <View style={styles.detail} testID={`safety-detail-${topic.code}`}>
                {topic.dont_text ? (
                  <View style={styles.dontBox}>
                    <Text style={styles.detailHead}>{t(locale, 'safety_dont')}</Text>
                    <Text style={styles.detailText}>{topic.dont_text}</Text>
                  </View>
                ) : null}
                {topic.do_text ? (
                  <View style={styles.doBox}>
                    <Text style={styles.detailHead}>{t(locale, 'safety_do')}</Text>
                    <Text style={styles.detailText}>{topic.do_text}</Text>
                  </View>
                ) : null}
                {topic.audio_url ? (
                  <BigButton
                    title={t(locale, 'safety_play')}
                    tone="ghost"
                    testID={`safety-play-${topic.code}`}
                  />
                ) : null}
              </View>
            ) : (
              <BigButton
                title={t(locale, 'common_ok')}
                tone="ghost"
                testID={`safety-expand-${topic.code}`}
                onPress={() => setOpen(isOpen ? null : topic.id)}
              />
            )}
          </Card>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '800', color: theme.ink, marginBottom: 6 },
  short: { fontSize: 17, color: theme.inkSoft, marginBottom: 10 },
  iconRow: { flexDirection: 'row', marginVertical: 8 },
  iconBox: { flex: 1, alignItems: 'center' },
  never: { fontSize: 14, fontWeight: '800', color: theme.red, marginTop: 4 },
  do: { fontSize: 14, fontWeight: '800', color: theme.green, marginTop: 4 },
  detail: { marginTop: 8 },
  dontBox: {
    backgroundColor: theme.redSoft,
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
  },
  doBox: { backgroundColor: theme.greenSoft, borderRadius: 12, padding: 12 },
  detailHead: { fontSize: 15, fontWeight: '800', marginBottom: 4 },
  detailText: { fontSize: 18, color: theme.ink, lineHeight: 26 },
});
