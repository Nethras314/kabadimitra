// Sign in / register.
//
// The app has no anonymous mode: the backend authorizes every read with a
// Supabase JWT, so an unauthenticated app can only ever show empty offline
// screens. This gate is therefore the precondition for everything else.
//
// Copy stays short and uses one idea per field, matching the low-literacy
// design rules the rest of the app follows.

import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { authConfigured, signIn, signUp } from '../auth/session';
import { Locale, t } from '../i18n/locales';
import { Banner, BigButton, BigInput, ScreenTitle, theme } from './components';

type Mode = 'signin' | 'signup';

export function SignInScreen({ locale }: { locale: Locale }) {
  const [mode, setMode] = useState<Mode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    setNotice(null);

    // Validate locally so an obvious mistake never costs a network round trip
    // on a metered mobile connection.
    if (!email.trim() || !password) {
      setError(t(locale, 'auth_error_generic'));
      return;
    }

    setBusy(true);
    try {
      if (mode === 'signin') {
        await signIn(email.trim(), password);
      } else {
        const { needsConfirmation } = await signUp(email.trim(), password, {
          fullName: fullName.trim() || undefined,
        });
        if (needsConfirmation) {
          setNotice(t(locale, 'auth_confirm_email'));
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t(locale, 'auth_error_generic'));
    } finally {
      setBusy(false);
    }
  };

  if (!authConfigured) {
    return (
      <View style={styles.centered}>
        <Banner tone="warn" text={t(locale, 'auth_not_configured')} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.form} keyboardShouldPersistTaps="handled">
        <ScreenTitle text={t(locale, 'auth_welcome')} />

        {error ? <Banner tone="warn" text={error} /> : null}
        {notice ? <Banner text={notice} /> : null}

        {mode === 'signup' ? (
          <BigInput
            value={fullName}
            onChangeText={setFullName}
            placeholder={t(locale, 'auth_name')}
            autoComplete="name"
            testID="auth-name-input"
          />
        ) : null}

        <BigInput
          value={email}
          onChangeText={setEmail}
          placeholder={t(locale, 'auth_email')}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
          testID="auth-email-input"
        />

        <BigInput
          value={password}
          onChangeText={setPassword}
          placeholder={t(locale, 'auth_password')}
          secureTextEntry
          autoCapitalize="none"
          autoComplete="password"
          testID="auth-password-input"
        />

        <BigButton
          title={mode === 'signin' ? t(locale, 'auth_sign_in') : t(locale, 'auth_sign_up')}
          onPress={submit}
          busy={busy}
          testID="auth-submit"
        />

        <BigButton
          title={mode === 'signin' ? t(locale, 'auth_need_account') : t(locale, 'auth_have_account')}
          tone="ghost"
          onPress={() => {
            setMode(mode === 'signin' ? 'signup' : 'signin');
            setError(null);
            setNotice(null);
          }}
          testID="auth-toggle-mode"
        />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: 'center', padding: 24 },
  form: { padding: 16, paddingBottom: 48 },
});
