// Price board + instant value estimate.
// One idea per screen: "what is this worth today".

import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { ApiClient, EstimateResult, PriceBoardRow } from '../api/client';
import { Locale, MATERIAL_LABELS, t } from '../i18n/locales';
import { Banner, BigButton, BigInput, Card, Glyph, Row, ScreenTitle, theme } from './components';

const MATERIAL_CODES: Record<string, string> = {
  tv_monitor: '20000000-0000-0000-0000-000000000001',
  computer_laptop: '20000000-0000-0000-0000-000000000002',
  mobile_electronics: '20000000-0000-0000-0000-000000000003',
  printer: '20000000-0000-0000-0000-000000000004',
  lamp: '20000000-0000-0000-0000-000000000005',
  motor: '20000000-0000-0000-0000-000000000006',
  pcb_board: '20000000-0000-0000-0000-000000000009',
  cable_wire: '20000000-0000-0000-0000-000000000010',
  metal: '20000000-0000-0000-0000-000000000014',
  plastic: '20000000-0000-0000-0000-000000000015',
  battery: '20000000-0000-0000-0000-000000000019',
  magnet: '20000000-0000-0000-0000-000000000018',
};

export function PriceBoardScreen({
  api,
  locale,
  city,
  cachedBoard,
  onCache,
}: {
  api: ApiClient;
  locale: Locale;
  city?: string;
  cachedBoard?: PriceBoardRow[] | null;
  onCache?: (rows: PriceBoardRow[]) => void;
}) {
  const [board, setBoard] = useState<PriceBoardRow[]>(cachedBoard ?? []);
  const [offline, setOffline] = useState(!cachedBoard?.length);
  const [picked, setPicked] = useState<PriceBoardRow | null>(null);
  const [weight, setWeight] = useState('');
  const [estimate, setEstimate] = useState<EstimateResult | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.priceBoard(city, locale);
      setBoard(res.board);
      setOffline(false);
      onCache?.(res.board);
    } catch {
      setOffline(true);
    }
  }, [api, city, locale, onCache]);

  useEffect(() => {
    load();
  }, [load]);

  const dirKey = (d: string) =>
    d === 'rising' ? 'prices_rising' : d === 'falling' ? 'prices_falling' : 'prices_stable';
  const dirTone = (d: string) => (d === 'rising' ? 'good' : d === 'falling' ? 'warn' : 'neutral');

  const calc = async () => {
    if (!picked) return;
    const kg = parseFloat(weight);
    if (!Number.isFinite(kg) || kg <= 0) return;
    try {
      const res = await api.estimateValue(picked.material_category_id, kg, city);
      setEstimate(res);
    } catch {
      setOffline(true);
    }
  };

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }}>
      <ScreenTitle text={t(locale, 'prices_title')} />
      {offline ? <Banner tone="warn" text={t(locale, 'prices_offline')} /> : null}

      {picked ? (
        <Card>
          <Text style={styles.pickedName}>{picked.name}</Text>
          <Text style={styles.pickedPrice}>
            {t(locale, 'common_rupees')} {picked.current_price ?? '—'} / kg
          </Text>
          <Row
            icon={picked.icon}
            title={t(locale, dirKey(picked.direction))}
            subtitle={`${picked.pct_change > 0 ? '+' : ''}${picked.pct_change}%`}
            tone={dirTone(picked.direction)}
          />
          <BigInput
            value={weight}
            onChangeText={setWeight}
            placeholder={t(locale, 'capture_weight')}
            keyboardType="decimal-pad"
            suffix="kg"
          />
          <BigButton title={t(locale, 'estimate_title')} onPress={calc} />
          {estimate ? (
            <View style={styles.estimateBox}>
              <Text style={styles.estimateHead}>{t(locale, 'estimate_title')}</Text>
              <Row
                icon="trending_down"
                title={t(locale, 'estimate_low')}
                right={`${t(locale, 'common_rupees')} ${estimate.estimated_value.low}`}
              />
              <Row
                icon="rupee"
                title={t(locale, 'estimate_mid')}
                right={`${t(locale, 'common_rupees')} ${estimate.estimated_value.mid}`}
                tone="good"
              />
              <Row
                icon="trending_up"
                title={t(locale, 'estimate_high')}
                right={`${t(locale, 'common_rupees')} ${estimate.estimated_value.high}`}
              />
              <Text style={styles.disclaimer}>{t(locale, 'estimate_note')}</Text>
            </View>
          ) : null}
          <BigButton title={t(locale, 'common_back')} tone="ghost" onPress={() => {
            setPicked(null);
            setEstimate(null);
            setWeight('');
          }} />
        </Card>
      ) : (
        <View>
          {board.length === 0 ? (
            <Banner tone="warn" text={t(locale, 'prices_offline')} />
          ) : null}
          {board.map((b) => (
            <Card key={b.code}>
              <Text
                style={styles.boardName}
                onPress={() => setPicked(b)}
                accessibilityRole="button"
              >
                {MATERIAL_LABELS[locale]?.[b.code] ?? b.name}
              </Text>
              <View style={styles.boardRow}>
                <Glyph name="rupee" size={26} />
                <Text style={styles.boardPrice}>{b.current_price ?? '—'}</Text>
                <Text style={styles.boardUnit}>/ kg</Text>
                <View style={{ flex: 1 }} />
                <Glyph name={b.icon} size={22} />
                <Text style={styles.boardPct}>
                  {b.pct_change > 0 ? '+' : ''}
                  {b.pct_change}%
                </Text>
              </View>
            </Card>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

export const MATERIAL_CATEGORY_IDS = MATERIAL_CODES;

const styles = StyleSheet.create({
  boardName: { fontSize: 24, fontWeight: '800', color: theme.ink },
  boardRow: { flexDirection: 'row', alignItems: 'center', marginTop: 8 },
  boardPrice: { fontSize: 30, fontWeight: '800', color: theme.green, marginLeft: 8 },
  boardUnit: { fontSize: 16, color: theme.inkSoft, marginLeft: 4 },
  boardPct: { fontSize: 16, fontWeight: '700', color: theme.inkSoft, marginLeft: 4 },
  pickedName: { fontSize: 26, fontWeight: '800', color: theme.ink },
  pickedPrice: { fontSize: 24, fontWeight: '700', color: theme.green, marginTop: 4 },
  estimateBox: {
    marginTop: 12,
    padding: 12,
    backgroundColor: theme.greenSoft,
    borderRadius: 14,
  },
  estimateHead: { fontSize: 20, fontWeight: '800', color: theme.green, marginBottom: 6 },
  disclaimer: { fontSize: 14, color: theme.inkSoft, marginTop: 8, fontStyle: 'italic' },
});
