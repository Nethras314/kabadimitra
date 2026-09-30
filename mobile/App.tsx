// App shell: four large tabs, no hidden navigation. Offline state is always
// visible so a collector knows whether what they see is current.

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, View } from 'react-native';

import { ApiClient, API_BASE, PriceBoardRow, SafetyTopic } from './src/api/client';
import { SqliteStore } from './src/db/sqliteStore';
import { ReachabilityConnectivity } from './src/lib/connectivity';
import { Locale, LOCALE_LABELS, SUPPORTED_LOCALES, t } from './src/i18n/locales';
import { SyncService } from './src/sync/service';
import { CaptureScreen } from './src/ui/CaptureScreen';
import { EarningsScreen } from './src/ui/EarningsScreen';
import { PriceBoardScreen } from './src/ui/PriceBoardScreen';
import { SafetyScreen } from './src/ui/SafetyScreen';
import { BigButton, theme } from './src/ui/components';

type Tab = 'capture' | 'prices' | 'safety' | 'earnings';

const TABS: { key: Tab; glyph: string }[] = [
  { key: 'capture', glyph: '\uD83D\uDCF7' },
  { key: 'prices', glyph: '\uD83D\uDCCA' },
  { key: 'safety', glyph: '\uD83D\uDEE1' },
  { key: 'earnings', glyph: '\uD83D\uDCB0' },
];

const CACHE_BOARD = 'cache:price-board';
const CACHE_SAFETY = 'cache:safety';

export default function App() {
  const [locale, setLocale] = useState<Locale>('hi');
  const [tab, setTab] = useState<Tab>('capture');
  const [online, setOnline] = useState<boolean | null>(null);
  const [pending, setPending] = useState(0);
  const [board, setBoard] = useState<PriceBoardRow[] | null>(null);
  const [safety, setSafety] = useState<SafetyTopic[] | null>(null);

  const { api, sync, store } = useMemo(() => {
    const s = new SqliteStore();
    const client = new ApiClient();
    // Reachability against the API health endpoint: an honest online/offline
    // signal rather than assuming the radio state means the server is up.
    const connectivity = new ReachabilityConnectivity(`${API_BASE}/health`, 4000);
    const service = new SyncService(s, client, connectivity);
    return { api: client, sync: service, store: s };
  }, []);

  useEffect(() => {
    (async () => {
      try {
        await store.open();
        // Load cached reference data so a cold, offline start is not empty.
        const cachedBoard = await store.getCached(CACHE_BOARD);
        if (cachedBoard) setBoard(JSON.parse(cachedBoard) as PriceBoardRow[]);
        const cachedSafety = await store.getCached(CACHE_SAFETY);
        if (cachedSafety) setSafety(JSON.parse(cachedSafety) as SafetyTopic[]);
      } catch {
        // Store unavailable (e.g. first run): screens still work online.
      }
    })();
  }, [store]);

  const refreshStatus = useCallback(async () => {
    const s = await sync.status();
    setOnline(s.connectivity === 'online');
    setPending(s.pending + s.failed);
  }, [sync]);

  useEffect(() => {
    refreshStatus();
    const id = setInterval(refreshStatus, 15000);
    return () => clearInterval(id);
  }, [refreshStatus]);

  const saveBoard = useCallback(
    async (rows: PriceBoardRow[]) => {
      setBoard(rows);
      try {
        await store.setCached(CACHE_BOARD, JSON.stringify(rows));
      } catch {
        /* cache is best-effort */
      }
    },
    [store],
  );

  const saveSafety = useCallback(
    async (topics: SafetyTopic[]) => {
      setSafety(topics);
      try {
        await store.setCached(CACHE_SAFETY, JSON.stringify(topics));
      } catch {
        /* cache is best-effort */
      }
    },
    [store],
  );

  const flushNow = useCallback(async () => {
    await sync.flush();
    refreshStatus();
  }, [sync, refreshStatus]);

  const cycleLocale = () => {
    const i = SUPPORTED_LOCALES.indexOf(locale);
    setLocale(SUPPORTED_LOCALES[(i + 1) % SUPPORTED_LOCALES.length]);
  };

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.topBar}>
        <Pressable onPress={cycleLocale} style={styles.localeBtn} accessibilityRole="button">
          <Text style={styles.localeText}>{LOCALE_LABELS[locale]}</Text>
        </Pressable>
        <View style={{ flex: 1 }} />
        <View style={styles.statusPill}>
          <Text style={styles.statusText}>
            {online === null ? '…' : online ? t(locale, 'sync_online') : t(locale, 'sync_offline')}
          </Text>
        </View>
      </View>

      {pending > 0 ? (
        <View style={styles.pendingBar}>
          <Text style={styles.pendingText}>
            {t(locale, 'sync_pending')}: {pending}
          </Text>
          <BigButton title={t(locale, 'sync_now')} onPress={flushNow} />
        </View>
      ) : null}

      <ScrollView style={{ flex: 1 }}>
        {tab === 'capture' ? <CaptureScreen sync={sync} api={api} locale={locale} /> : null}
        {tab === 'prices' ? (
          <PriceBoardScreen
            api={api}
            locale={locale}
            city="Pune"
            cachedBoard={board}
            onCache={saveBoard}
          />
        ) : null}
        {tab === 'safety' ? (
          <SafetyScreen api={api} locale={locale} cached={safety} onCache={saveSafety} />
        ) : null}
        {tab === 'earnings' ? <EarningsScreen api={api} locale={locale} /> : null}
      </ScrollView>

      <View style={styles.tabBar}>
        {TABS.map((x) => (
          <Pressable
            key={x.key}
            onPress={() => setTab(x.key)}
            style={[styles.tab, tab === x.key && styles.tabActive]}
            accessibilityRole="tab"
            accessibilityLabel={t(locale, `tab_${x.key}`)}
          >
            <Text style={styles.tabGlyph}>{x.glyph}</Text>
            <Text style={[styles.tabLabel, tab === x.key && styles.tabLabelActive]}>
              {t(locale, `tab_${x.key}`)}
            </Text>
          </Pressable>
        ))}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  localeBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 12,
    backgroundColor: theme.greenSoft,
  },
  localeText: { fontSize: 17, fontWeight: '800', color: theme.green },
  statusPill: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 10,
    backgroundColor: theme.card,
  },
  statusText: { fontSize: 14, fontWeight: '700', color: theme.inkSoft },
  pendingBar: {
    marginHorizontal: 12,
    padding: 10,
    borderRadius: 12,
    backgroundColor: theme.amberSoft,
  },
  pendingText: { fontSize: 15, fontWeight: '700', color: theme.amber, marginBottom: 6 },
  tabBar: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: theme.line,
    backgroundColor: theme.bg,
  },
  tab: { flex: 1, alignItems: 'center', paddingVertical: 10 },
  tabActive: { backgroundColor: theme.greenSoft },
  tabGlyph: { fontSize: 26 },
  tabLabel: { fontSize: 13, fontWeight: '700', color: theme.inkSoft, marginTop: 2 },
  tabLabelActive: { color: theme.green },
});
