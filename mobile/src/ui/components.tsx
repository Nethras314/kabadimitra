// Low-literacy UI primitives.
//
// Design rules for this product:
//  - one idea per screen, minimal text
//  - icon-first: meaning carried by the pictogram, text is reinforcement
//  - large type (>=18), high contrast, generous touch targets (>=64dp)
//  - colour is never the only signal (icon + text always accompany it)

import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { t, Locale } from '../i18n/locales';

export const theme = {
  bg: '#FFFFFF',
  card: '#F4F6F5',
  ink: '#111827',
  inkSoft: '#4B5563',
  green: '#14532D',
  greenSoft: '#DCFCE7',
  amber: '#92400E',
  amberSoft: '#FEF3C7',
  red: '#991B1B',
  redSoft: '#FEE2E2',
  blue: '#1E3A8A',
  blueSoft: '#DBEAFE',
  line: '#D1D5DB',
};

// Maps the icon keys the backend sends to something renderable without an
// icon font dependency. Unknown keys fall back to a neutral dot.
export const ICON_GLYPHS: Record<string, string> = {
  fire_crossed: '\u274C',
  handshake: '\uD83E\uDD1A',
  acid_flask: '\uD83E\uDDEA',
  board_whole: '\uD83D\uDCC1',
  battery_burst: '\u26A1',
  battery_box: '\uD83D\uDD50',
  tube_crack: '\uD83D\uDDA3',
  tube_whole: '\uD83D\uDCFA',
  hand_solder: '\uD83D\uDD28',
  ventilate: '\uD83C\uDF00',
  gloves: '\uD83E\uDDDF',
  mask: '\u1F637',
  shoes: '\uD83D\uDC5E',
  child_warning: '\u26A0',
  verified_recycler: '\u2705',
  unknown_buyer: '\u2753',
  covered_store: '\uD83C\uDFE2',
  hand_wash: '\uD83D\uDCDF',
  trending_up: '\u2B06',
  trending_down: '\u2B07',
  trending_flat: '\u27A1',
  rupee: '\u20B9',
  camera: '\uD83D\uDCF7',
  scale: '\u2696',
  truck: '\uD83D\uDE9A',
  receipt: '\uD83E\uDDBA',
  shield: '\uD83D\uDEE1',
};

export function Glyph({ name, size = 32 }: { name: string; size?: number }) {
  return <Text style={{ fontSize: size, lineHeight: size * 1.2 }}>{ICON_GLYPHS[name] ?? '\u2022'}</Text>;
}

/** Big tappable tile: icon + label. The primary low-literacy control. */
export function Tile({
  icon,
  label,
  onPress,
  tone = 'neutral',
  disabled,
  testID,
}: {
  icon: string;
  label: string;
  onPress?: () => void;
  tone?: 'neutral' | 'good' | 'warn' | 'bad';
  disabled?: boolean;
  testID?: string;
}) {
  const bg =
    tone === 'good' ? theme.greenSoft
    : tone === 'warn' ? theme.amberSoft
    : tone === 'bad' ? theme.redSoft
    : theme.card;
  const ink =
    tone === 'good' ? theme.green
    : tone === 'warn' ? theme.amber
    : tone === 'bad' ? theme.red
    : theme.ink;

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.tile,
        { backgroundColor: bg, opacity: disabled ? 0.5 : pressed ? 0.75 : 1 },
      ]}
    >
      <Glyph name={icon} />
      <Text style={[styles.tileLabel, { color: ink }]} numberOfLines={2}>
        {label}
      </Text>
    </Pressable>
  );
}

/** Primary action button with a large hit area. */
export function BigButton({
  title,
  onPress,
  tone = 'primary',
  disabled,
  busy,
  testID,
}: {
  title: string;
  onPress?: () => void;
  tone?: 'primary' | 'ghost' | 'danger';
  disabled?: boolean;
  busy?: boolean;
  testID?: string;
}) {
  const bg = tone === 'primary' ? theme.green : tone === 'danger' ? theme.red : 'transparent';
  const ink = tone === 'ghost' ? theme.green : '#FFFFFF';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || busy}
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={title}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, opacity: disabled ? 0.5 : pressed ? 0.8 : 1 },
        tone === 'ghost' && styles.buttonGhost,
      ]}
    >
      {busy ? <ActivityIndicator color={ink} /> : <Text style={[styles.buttonText, { color: ink }]}>{title}</Text>}
    </Pressable>
  );
}

/** Large numeric input — used for weight. */
export function BigInput({
  value,
  onChangeText,
  placeholder,
  keyboardType = 'default',
  suffix,
  secureTextEntry,
  autoCapitalize,
  autoComplete,
  testID,
}: {
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  keyboardType?: 'default' | 'numeric' | 'decimal-pad' | 'email-address';
  suffix?: string;
  secureTextEntry?: boolean;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
  autoComplete?: 'email' | 'password' | 'name' | 'tel' | 'off';
  testID?: string;
}) {
  return (
    <View style={styles.inputWrap}>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={theme.inkSoft}
        keyboardType={keyboardType}
        secureTextEntry={secureTextEntry}
        autoCapitalize={autoCapitalize}
        autoComplete={autoComplete}
        testID={testID}
        style={styles.input}
        accessibilityLabel={placeholder}
      />
      {suffix ? <Text style={styles.suffix}>{suffix}</Text> : null}
    </View>
  );
}

export function Card({ children, testID }: { children: React.ReactNode; testID?: string }) {
  return <View style={styles.card} testID={testID}>{children}</View>;
}

export function Row({
  icon,
  title,
  right,
  subtitle,
  tone = 'neutral',
}: {
  icon?: string;
  title: string;
  right?: string;
  subtitle?: string;
  tone?: 'neutral' | 'good' | 'warn' | 'bad';
}) {
  const ink =
    tone === 'good' ? theme.green
    : tone === 'warn' ? theme.amber
    : tone === 'bad' ? theme.red
    : theme.ink;
  return (
    <View style={styles.row}>
      {icon ? <Glyph name={icon} size={28} /> : null}
      <View style={{ flex: 1, marginLeft: icon ? 12 : 0 }}>
        <Text style={[styles.rowTitle, { color: ink }]}>{title}</Text>
        {subtitle ? <Text style={styles.rowSubtitle}>{subtitle}</Text> : null}
      </View>
      {right ? <Text style={styles.rowRight}>{right}</Text> : null}
    </View>
  );
}

export function Banner({ text, tone = 'info' }: { text: string; tone?: 'info' | 'warn' }) {
  const bg = tone === 'warn' ? theme.amberSoft : theme.blueSoft;
  const ink = tone === 'warn' ? theme.amber : theme.blue;
  return (
    <View style={[styles.banner, { backgroundColor: bg }]}>
      <Text style={[styles.bannerText, { color: ink }]}>{text}</Text>
    </View>
  );
}

export function ScreenTitle({ text }: { text: string }) {
  return <Text style={styles.screenTitle}>{text}</Text>;
}

export function useT(locale: Locale) {
  return (key: string) => t(locale, key);
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    minHeight: 112,
    borderRadius: 16,
    padding: 14,
    alignItems: 'center',
    justifyContent: 'center',
    margin: 6,
  },
  tileLabel: {
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
    marginTop: 8,
  },
  button: {
    minHeight: 64,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
    marginVertical: 8,
  },
  buttonGhost: {
    borderWidth: 2,
    borderColor: theme.green,
  },
  buttonText: { fontSize: 20, fontWeight: '800' },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.card,
    borderRadius: 14,
    paddingHorizontal: 16,
    minHeight: 72,
  },
  input: { flex: 1, fontSize: 30, fontWeight: '700', color: theme.ink },
  suffix: { fontSize: 20, color: theme.inkSoft, marginLeft: 8, fontWeight: '600' },
  card: {
    backgroundColor: theme.card,
    borderRadius: 16,
    padding: 16,
    marginVertical: 8,
  },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10 },
  rowTitle: { fontSize: 20, fontWeight: '700' },
  rowSubtitle: { fontSize: 15, color: theme.inkSoft, marginTop: 2 },
  rowRight: { fontSize: 20, fontWeight: '800', color: theme.ink },
  banner: { borderRadius: 12, padding: 12, marginVertical: 8 },
  bannerText: { fontSize: 16, fontWeight: '600' },
  screenTitle: { fontSize: 28, fontWeight: '800', color: theme.ink, marginVertical: 12 },
});
