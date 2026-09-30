// Capture: photograph -> categorise -> weight, with AI assist.
//
// The photo is real (expo-camera), uploaded straight to Cloudinary, attached as
// metadata, and only then offered to the classifier. If the collector picks
// "I don't know" the item is still valid — it is routed for later review
// rather than guessed at.

import React, { useState } from 'react';
import {
  CameraView,
  useCameraPermissions,
  type CameraType,
} from 'expo-camera';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ApiClient } from '../api/client';
import { CloudinaryUploader } from '../api/upload';
import { Locale, MATERIAL_LABELS, t } from '../i18n/locales';
import { SyncService } from '../sync/service';
import { BigButton, BigInput, Banner, Card, Glyph, Row, ScreenTitle, theme } from './components';
import { MATERIAL_CATEGORY_IDS } from './PriceBoardScreen';

const CATEGORY_GLYPH: Record<string, string> = {
  tv_monitor: '\uD83D\uDCFA',
  computer_laptop: '\uD83D\uDCBB',
  mobile_electronics: '\uD83D\uDCF1',
  pcb_board: '\uD83D\uDCC1',
  cable_wire: '\uD83D\uDD0C',
  battery: '\uD83D\uDD50',
  motor: '\u2699',
  magnet: '\uD83D\uDD25',
  plastic: '\uD83E\uDDFA',
  metal: '\u26A1',
  lamp: '\uD83D\uDE9B',
  printer: '\uD83D\uDDA8',
  other: '\u2753',
  dont_know: '\uD83D\uDCDA',
};

type Stage = 'capture' | 'category' | 'weight' | 'ai' | 'done';

export function CaptureScreen({
  sync,
  api,
  locale,
  onCaptured,
}: {
  sync: SyncService;
  api: ApiClient;
  locale: Locale;
  onCaptured?: (lotId: string) => void;
}) {
  const [permission, requestPermission] = useCameraPermissions();
  const [facing, setFacing] = useState<CameraType>('back');
  const [stage, setStage] = useState<Stage>('capture');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [lotId, setLotId] = useState<string | null>(null);
  const [itemId, setItemId] = useState<string | null>(null);
  const [imageId, setImageId] = useState<string | null>(null);
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [weight, setWeight] = useState('');
  const [aiNote, setAiNote] = useState<string | null>(null);

  const begin = async () => {
    if (!permission?.granted) {
      const res = await requestPermission();
      if (!res.granted) {
        setError('Camera permission denied');
        return;
      }
    }
    setStage('capture');
  };

  const takePhoto = async () => {
    if (!lotId) {
      // The lot is created locally first, so capture works fully offline.
      const lot = await sync.createLot({});
      setLotId(lot.id);
      onCaptured?.(lot.id);
    }
    setStage('capture');
  };

  const onShutter = async () => {
    // CameraView ref is provided by the parent render below.
  };

  const pickCategory = async (code: string) => {
    setCategory(code);
    setStage('weight');
  };

  const save = async () => {
    if (!lotId || !category) return;
    setBusy(true);
    setError(null);
    try {
      const kg = parseFloat(weight);
      const item = await sync.addItem({
        lot_id: lotId,
        collector_category_id: category,
        material_category_id: MATERIAL_CATEGORY_IDS[category] ?? null,
        kind:
          category === 'battery' || category === 'mobile_electronics'
            ? 'equipment'
            : 'recovered_material',
        declared_weight_kg: Number.isFinite(kg) ? kg : null,
      });
      setItemId(item.id);

      // Upload the photo if one was taken. Failure is non-fatal: the item is
      // already recorded locally and will sync regardless.
      if (photoUri) {
        try {
          const up = new CloudinaryUploader(api);
          const res = await up.upload(photoUri, { lotId });
          await api.attachImage(lotId, item.id, {
            cloudinary_public_id: res.publicId,
            cloudinary_url: res.secureUrl,
            is_primary: true,
            mime_type: 'image/jpeg',
            width: res.width,
            height: res.height,
          });
        } catch (e) {
          setError('Photo upload failed; the item was still saved');
        }
      }

      setStage('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const askAi = async () => {
    if (!itemId) return;
    setBusy(true);
    setError(null);
    try {
      const d = await api.classifyItem(itemId, imageId ?? undefined);
      if (d.predicted_category_id) {
        setAiNote(`${d.provider} · ${Math.round(d.confidence * 100)}%`);
      } else {
        setAiNote(`${d.provider} · not confident`);
      }
    } catch (e) {
      setAiNote('AI unavailable');
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setStage('capture');
    setCategory(null);
    setWeight('');
    setLotId(null);
    setItemId(null);
    setImageId(null);
    setPhotoUri(null);
    setAiNote(null);
    setError(null);
  };

  // ------------------------------------------------------------------ camera
  if (stage === 'capture') {
    return (
      <View style={{ flex: 1 }}>
        {error ? <Banner tone="warn" text={error} /> : null}
        {!permission?.granted ? (
          <View style={styles.permBox}>
            <ScreenTitle text={t(locale, 'capture_photo')} />
            <BigButton title={t(locale, 'capture_photo')} onPress={begin} testID="capture-request-permission" />
          </View>
        ) : (
          <>
            <CameraView
              style={{ flex: 1 }}
              facing={facing}
              ref={(r) => {
                cameraRef = r;
              }}
            />
            <View style={styles.shutterBar}>
              <Pressable
                style={styles.flipBtn}
                onPress={() => setFacing(facing === 'back' ? 'front' : 'back')}
                accessibilityRole="button"
                testID="capture-flip-camera"
              >
                <Glyph name="camera" size={28} />
              </Pressable>
              <Pressable
                style={styles.shutter}
                onPress={async () => {
                  await takePhoto();
                  if (cameraRef) {
                    const shot = await cameraRef.takePictureAsync();
                    if (shot?.uri) setPhotoUri(shot.uri);
                  }
                }}
                accessibilityRole="button"
                accessibilityLabel={t(locale, 'capture_photo')}
                testID="capture-shutter"
              />
              <Pressable
                style={styles.nextBtn}
                onPress={() => setStage('category')}
                accessibilityRole="button"
                accessibilityLabel={t(locale, 'capture_next')}
                testID="capture-next"
              >
                <Text style={styles.nextText}>{t(locale, 'capture_next')}</Text>
              </Pressable>
            </View>
          </>
        )}
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }}>
      <ScreenTitle text={t(locale, 'capture_title')} />
      {error ? <Banner tone="warn" text={error} /> : null}

      {stage === 'category' ? (
        <View>
          <Text style={styles.prompt}>{t(locale, 'capture_choose')}</Text>
          {Object.keys(MATERIAL_LABELS[locale]).map((code) => (
            <Card key={code}>
              <Pressable
                onPress={() => pickCategory(code)}
                accessibilityRole="button"
                accessibilityLabel={MATERIAL_LABELS[locale][code]}
                testID={`capture-category-${code}`}
                style={styles.catRow}
              >
                <Text style={styles.catIcon}>{CATEGORY_GLYPH[code] ?? '\u2022'}</Text>
                <Text style={styles.catLabel}>{MATERIAL_LABELS[locale][code]}</Text>
              </Pressable>
            </Card>
          ))}
        </View>
      ) : null}

      {stage === 'weight' ? (
        <View>
          <Row
            icon={CATEGORY_GLYPH[category ?? 'other']}
            title={MATERIAL_LABELS[locale]?.[category ?? ''] ?? ''}
            right={photoUri ? '\uD83D\uDCF7' : undefined}
          />
          <BigInput
            value={weight}
            onChangeText={setWeight}
            placeholder={t(locale, 'capture_weight')}
            keyboardType="decimal-pad"
            suffix="kg"
            testID="capture-weight-input"
          />
          <BigButton title={t(locale, 'capture_save')} onPress={save} busy={busy} testID="capture-save" />
          <BigButton
            title={t(locale, 'common_cancel')}
            tone="ghost"
            onPress={() => setStage('category')}
            testID="capture-cancel"
          />
        </View>
      ) : null}

      {stage === 'done' ? (
        <Card testID="capture-done">
          <Text style={styles.doneGlyph}>{'\u2705'}</Text>
          <Text style={styles.doneText}>{t(locale, 'capture_saved')}</Text>
          {photoUri ? (
            <BigButton title="AI: check material" tone="ghost" onPress={askAi} busy={busy} testID="capture-ai-check" />
          ) : null}
          {aiNote ? <Text style={styles.aiNote} testID="capture-ai-note">{aiNote}</Text> : null}
          <BigButton title={t(locale, 'capture_add_item')} onPress={reset} testID="capture-add-another" />
        </Card>
      ) : null}
    </ScrollView>
  );
}

// Module-level ref so the shutter handler can reach the live camera instance
// without threading it through render props.
let cameraRef: CameraView | null = null;

const styles = StyleSheet.create({
  permBox: { padding: 16 },
  shutterBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 20,
    backgroundColor: theme.bg,
  },
  flipBtn: { width: 64, height: 64, alignItems: 'center', justifyContent: 'center' },
  shutter: {
    width: 78,
    height: 78,
    borderRadius: 39,
    backgroundColor: theme.green,
    borderWidth: 4,
    borderColor: '#FFFFFF',
  },
  nextBtn: {
    minHeight: 64,
    paddingHorizontal: 18,
    justifyContent: 'center',
    borderRadius: 14,
    backgroundColor: theme.greenSoft,
  },
  nextText: { fontSize: 18, fontWeight: '800', color: theme.green },
  prompt: { fontSize: 24, fontWeight: '800', color: theme.ink, marginVertical: 8 },
  catRow: { flexDirection: 'row', alignItems: 'center', minHeight: 72 },
  catIcon: { fontSize: 40, marginRight: 16 },
  catLabel: { fontSize: 22, fontWeight: '700', color: theme.ink, flex: 1 },
  doneGlyph: { fontSize: 64, textAlign: 'center' },
  doneText: {
    fontSize: 26,
    fontWeight: '800',
    color: theme.green,
    textAlign: 'center',
    marginVertical: 16,
  },
  aiNote: {
    fontSize: 16,
    fontWeight: '700',
    color: theme.inkSoft,
    textAlign: 'center',
    marginVertical: 8,
  },
});
