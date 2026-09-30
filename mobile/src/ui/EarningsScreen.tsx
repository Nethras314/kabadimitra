// Earnings ledger: total earned, paid, and still due.
// Plain numbers, no jargon — the ledger is how a collector builds trust in
// informal trade.

import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { ApiClient, EarningsItem, EarningsSummary } from '../api/client';
import { Locale, t } from '../i18n/locales';
import { Banner, Card, Glyph, Row, ScreenTitle, theme } from './components';

export function EarningsScreen({
  api,
  locale,
  cachedSummary,
  cachedItems,
}: {
  api: ApiClient;
  locale: Locale;
  cachedSummary?: EarningsSummary | null;
  cachedItems?: EarningsItem[] | null;
}) {
  const [summary, setSummary] = useState<EarningsSummary | null>(cachedSummary ?? null);
  const [items, setItems] = useState<EarningsItem[]>(cachedItems ?? []);
  const [offline, setOffline] = useState(!cachedSummary);

  const load = useCallback(async () => {
    try {
      const res = await api.earnings();
      setSummary(res.summary);
      setItems(res.items);
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, [api]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }}>
      <ScreenTitle text={t(locale, 'earnings_title')} />
      {offline ? <Banner tone="warn" text={t(locale, 'prices_offline')} /> : null}

      {summary ? (
        <Card>
          <Row
            icon="rupee"
            title={t(locale, 'earnings_earned')}
            right={`${t(locale, 'common_rupees')} ${summary.total_earned}`}
            tone="good"
          />
          <Row
            icon="receipt"
            title={t(locale, 'earnings_paid')}
            right={`${t(locale, 'common_rupees')} ${summary.total_paid}`}
          />
          <Row
            icon="scale"
            title={t(locale, 'earnings_due')}
            right={`${t(locale, 'common_rupees')} ${summary.total_pending_due}`}
            tone={summary.total_pending_due > 0 ? 'warn' : 'neutral'}
          />
        </Card>
      ) : null}

      {items.length === 0 ? (
        <Card>
          <Text style={styles.empty}>{t(locale, 'earnings_nothing')}</Text>
        </Card>
      ) : (
        items.map((it) => (
          <Card key={it.transaction_id}>
            <Row
              icon={it.state === 'due' ? 'scale' : 'receipt'}
              title={it.recycler_name ?? it.status}
              subtitle={`${it.date?.slice(0, 10) ?? ''}${
                it.weight_kg ? ` · ${it.weight_kg} kg` : ''
              }`}
              right={`${t(locale, 'common_rupees')} ${it.earned}`}
              tone={it.state === 'due' ? 'warn' : 'good'}
            />
            {it.pending > 0 ? (
              <Text style={styles.due}>
                {t(locale, 'earnings_due')}: {t(locale, 'common_rupees')} {it.pending}
              </Text>
            ) : null}
          </Card>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  empty: { fontSize: 20, color: theme.inkSoft, textAlign: 'center', paddingVertical: 16 },
  due: { fontSize: 16, fontWeight: '700', color: theme.amber, marginTop: 4 },
});
