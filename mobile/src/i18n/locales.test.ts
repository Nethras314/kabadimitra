// Spec-critical localization guarantees.
// The spec requires Marathi + Hindi at minimum, and a genuinely usable
// interface for low-literacy users. These tests fail if a key is missing or a
// translation silently falls back to English.

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  MATERIAL_LABELS,
  STRINGS,
  SUPPORTED_LOCALES,
  t,
} from './locales';

const REQUIRED_LOCALES = ['en', 'hi', 'mr', 'ta', 'te', 'ml', 'kn', 'bn'] as const;

test('supports the spec-required locales', () => {
  for (const loc of REQUIRED_LOCALES) {
    assert.ok(SUPPORTED_LOCALES.includes(loc), `missing locale ${loc}`);
  }
});

test('every locale defines the same UI keys', () => {
  const reference = Object.keys(STRINGS.en).sort();
  for (const loc of REQUIRED_LOCALES) {
    assert.deepEqual(
      Object.keys(STRINGS[loc]).sort(),
      reference,
      `locale ${loc} has a different key set`,
    );
  }
});

test('no locale value is empty', () => {
  for (const loc of REQUIRED_LOCALES) {
    for (const [key, value] of Object.entries(STRINGS[loc])) {
      assert.ok(value && value.trim().length > 0, `${loc}.${key} is empty`);
    }
  }
});

test('hindi and marathi are actually translated, not english fallbacks', () => {
  const keys = Object.keys(STRINGS.en);
  for (const loc of REQUIRED_LOCALES) {
    if (loc === 'en') continue;
    const same = keys.filter((k) => STRINGS[loc][k] === STRINGS.en[k]).length;
    // A couple of symbols may legitimately match, but a wholesale copy means the
    // translation never landed.
    assert.ok(
      same <= 2,
      `${loc} looks untranslated (${same}/${keys.length} identical)`,
    );
  }
});

test('t() falls back to english for an unknown locale', () => {
  // @ts-expect-error deliberately invalid locale
  assert.equal(t('xx', 'tab_prices'), STRINGS.en.tab_prices);
});

test('t() returns the key when unknown, never undefined', () => {
  assert.equal(t('en', 'totally_unknown_key'), 'totally_unknown_key');
});

test('material labels exist in all three locales for every category', () => {
  const categories = Object.keys(MATERIAL_LABELS.en);
  assert.equal(categories.length, 14, 'expected the 14 approved collector categories');
  for (const loc of REQUIRED_LOCALES) {
    assert.deepEqual(
      Object.keys(MATERIAL_LABELS[loc]).sort(),
      categories.slice().sort(),
      `material labels differ in ${loc}`,
    );
  }
});

test('every non-english locale differs for "I don\'t know"', () => {
  for (const loc of REQUIRED_LOCALES) {
    if (loc === 'en') continue;
    assert.notEqual(
      MATERIAL_LABELS[loc].dont_know,
      MATERIAL_LABELS.en.dont_know,
      `${loc}.dont_know is untranslated`,
    );
  }
});

test('safety-critical strings are short enough to read aloud', () => {
  // Low-literacy users need short, scannable copy.
  for (const loc of REQUIRED_LOCALES) {
    for (const key of ['safety_do', 'safety_dont', 'capture_choose', 'capture_weight']) {
      assert.ok(
        STRINGS[loc][key].length <= 40,
        `${loc}.${key} is too long for low-literacy UI: "${STRINGS[loc][key]}"`,
      );
    }
  }
});
