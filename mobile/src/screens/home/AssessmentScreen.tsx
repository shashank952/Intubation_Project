import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  ActivityIndicator,
  Animated,
  useWindowDimensions,
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  User,
  Stethoscope,
  ClipboardList,
  History,
  FlaskConical,
  Shuffle,
  ChevronDown,
  AlertCircle,
  Activity,
} from 'lucide-react-native';
import { useTheme } from '@/theme/ThemeProvider';
import { useAuth } from '@/context/AuthContext';
import { radii } from '@/theme/tokens';
import { createPatient, runPrediction, checkLlmStatus } from '@/lib/api';
import { saveDraft, clearDraft, loadDraft } from '@/lib/storage';
import {
  defaultFormData,
  generateRandomData,
  FIXTURES,
} from '@/utils/randomData';
import { validateStep, validateAll } from '@/utils/formValidation';
import type { PredictionInput, PredictionResponse } from '@/types';
import AppButton from '@/components/ui/AppButton';
import AppInput from '@/components/ui/AppInput';
import Select from '@/components/ui/Select';
import Banner from '@/components/ui/Banner';
import type { HomeStackParamList } from '@/navigation';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

const STEPS = [
  { key: 'basic', label: 'Basic', icon: User },
  { key: 'airway', label: 'Airway', icon: Stethoscope },
  { key: 'physical', label: 'Physical', icon: ClipboardList },
  { key: 'history', label: 'History', icon: History },
];

// Must stay above the backend report budget (LLM_REPORT_BUDGET_SECONDS = 28s),
// otherwise the client aborts before the server can return its fallback report.
const PREDICTION_TIMEOUT_MS = 45000;

const YES_NO = [
  { label: 'No', value: 'No' },
  { label: 'Yes', value: 'Yes' },
];

const MALLAMPATI = [
  { label: 'Class I', value: '1' },
  { label: 'Class II', value: '2' },
  { label: 'Class III', value: '3' },
  { label: 'Class IV', value: '4' },
];

// Port of web src/components/PatientForm.tsx + dashboard handleSubmit (PatientForm section tabs â†’ wizard steps)
export default function AssessmentScreen() {
  const { c } = useTheme();
  const { user } = useAuth();
  const navigation = useNavigation<NativeStackNavigationProp<HomeStackParamList>>();
  const route = useRoute<RouteProp<HomeStackParamList, 'Assessment'>>();
  const { width } = useWindowDimensions();
  const stepFade = React.useRef(new Animated.Value(1)).current;

  // Responsive form grid: 2 columns when there is enough width, 1 column on narrow screens
  const canFitTwoColumns = width >= 380;
  const fieldWidth = canFitTwoColumns ? '48%' : '100%';
  const fieldThirdWidth = canFitTwoColumns ? '30%' : '100%';

  const [formData, setFormData] = useState<PredictionInput>({
    ...defaultFormData,
    ...(route.params?.initialData ?? {}),
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [step, setStep] = useState(1);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [predictingSlow, setPredictingSlow] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const transitionStep = useCallback(
    (next: number) => {
      Animated.timing(stepFade, {
        toValue: 0,
        duration: 120,
        useNativeDriver: true,
      }).start(() => {
        setStep(next);
        Animated.timing(stepFade, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }).start();
      });
    },
    [stepFade],
  );

  // Restore draft on mount
  useEffect(() => {
    loadDraft<PredictionInput>().then((draft) => {
      if (draft) setFormData((prev) => ({ ...prev, ...draft }));
    });
  }, []);

  // Persist draft while typing
  const handleChange = useCallback(
    (field: keyof PredictionInput, value: string | number) => {
      setFormData((prev) => {
        const next = { ...prev, [field]: value };
        saveDraft(next);
        return next;
      });
      setErrors((prev) => {
        if (!prev[field as string]) return prev;
        const n = { ...prev };
        delete n[field as string];
        return n;
      });
    },
    [],
  );

  const loadFixture = (data: PredictionInput) => {
    setFormData({ ...data });
    setErrors({});
    setSubmitError('');
    setStep(1);
  };

  const goNext = () => {
    const errs = validateStep(step, formData);
    setErrors(errs);
    if (Object.keys(errs).length === 0) {
      transitionStep(Math.min(4, step + 1));
    }
  };

  const goBack = () => transitionStep(Math.max(1, step - 1));

  const handleSubmit = async () => {
    const errs = validateAll(formData);
    setErrors(errs);
    if (Object.keys(errs).length > 0) {
      setSubmitError('Fix errors above before submitting');
      return;
    }

    setPredicting(true);
    setPredictingSlow(false);
    setSubmitError('');

    // Fire LLM status check in parallel (non-blocking)
    checkLlmStatus().catch(() => {});

    const controller = new AbortController();
    const slowTimer = setTimeout(() => setPredictingSlow(true), 5000);
    const failTimer = setTimeout(() => controller.abort(), PREDICTION_TIMEOUT_MS);

    const numericData: PredictionInput = {
      ...formData,
      age: Number(formData.age),
      bmi: Number(formData.bmi),
      mallampati_score: Number(formData.mallampati_score),
      tmd: Number(formData.tmd),
      neck_circumference: Number(formData.neck_circumference),
      mouth_opening: Number(formData.mouth_opening),
      smd: Number(formData.smd),
      neck_movement: Number(formData.neck_movement),
    };

    try {
      // Web parity: create patient first (mallampati sent as STRING here)
      try {
        await createPatient({
          patient_id: numericData.patient_id,
          age: numericData.age,
          gender: numericData.gender,
          bmi: numericData.bmi,
          mallampati: String(numericData.mallampati_score),
          tmd: numericData.tmd,
          neck_circumference: numericData.neck_circumference,
        });
      } catch (err: any) {
        // Duplicate patient (409) â†’ continue to prediction (safer UX)
        if (!(err?.status === 409 || String(err?.message ?? '').toLowerCase().includes('already exists'))) {
          throw err;
        }
      }

      const result: PredictionResponse = await runPrediction(numericData, controller.signal);
      await clearDraft();
      navigation.navigate('PredictionResult', { result, input: numericData });
    } catch (err) {
      if (controller.signal.aborted) {
        setSubmitError(
          'Time limit exceeded. The server did not respond in time. Please wait a moment and try again.',
        );
      } else {
        setSubmitError(err instanceof Error ? err.message : 'Prediction failed. Please try again.');
      }
    } finally {
      clearTimeout(slowTimer);
      clearTimeout(failTimer);
      setPredicting(false);
      setPredictingSlow(false);
    }
  };

  const inputBorder = (field: string) =>
    errors[field] ? { borderColor: c.danger[300] } : { borderColor: c.ink };

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.page }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <View style={[styles.headerIcon, { backgroundColor: c.brand[50] }]}>
              <Activity size={16} color={c.brand[600]} />
            </View>
            <View>
              <Text style={[styles.headerTitle, { color: c.text }]}>Patient Entry</Text>
              <Text style={[styles.headerSub, { color: c.textFaint }]}>
                {user?.role ?? ''} Â· {user?.email ?? ''}
              </Text>
            </View>
          </View>
        </View>

        {/* Fixture buttons (web parity: E / M / D / Random) */}
        <View style={styles.fixtureRow}>
          {FIXTURES.map((f) => {
            const tint =
              f.key === 'E'
                ? { bg: c.success[50], border: c.success[200], text: c.success[700] }
                : f.key === 'M'
                ? { bg: c.warning[50], border: c.warning[200], text: c.warning[700] }
                : { bg: c.danger[50], border: c.danger[200], text: c.danger[700] };
            return (
              <Pressable
                key={f.key}
                onPress={() => loadFixture(f.data)}
                style={({ pressed }) => [
                  styles.fixtureBtn,
                  { backgroundColor: tint.bg, borderColor: tint.border },
                  pressed && { opacity: 0.7 },
                ]}
              >
                <FlaskConical size={11} color={tint.text} />
                <Text style={[styles.fixtureText, { color: tint.text }]}>{f.label}</Text>
              </Pressable>
            );
          })}
          <Pressable
            onPress={() => loadFixture(generateRandomData())}
            style={({ pressed }) => [
              styles.fixtureBtn,
              { backgroundColor: c.neutral[50], borderColor: c.neutral[200] },
              pressed && { opacity: 0.7 },
            ]}
          >
            <Shuffle size={11} color={c.neutral[600]} />
          </Pressable>
        </View>

        {/* Step indicator (segmented pill) */}
        <View style={[styles.steps, { backgroundColor: c.neutral[100], borderColor: c.ink }]}>
          {STEPS.map((s, i) => {
            const isActive = step === i + 1;
            const Icon = s.icon;
            return (
              <Pressable
                key={s.key}
                onPress={() => {
                  // Allow going back to earlier steps freely; going forward validates
                  if (i + 1 < step) setStep(i + 1);
                }}
                style={[
                  styles.stepTab,
                  { backgroundColor: isActive ? c.card : 'transparent' },
                  isActive && {
                    shadowColor: '#111111',
                    shadowOffset: { width: 2, height: 2 },
                    shadowOpacity: 0.6,
                    shadowRadius: 0,
                    elevation: 2,
                  },
                ]}
              >
                <Icon size={14} color={isActive ? c.brand[700] : c.textMuted} />
                <Text
                  numberOfLines={1}
                  style={[
                    styles.stepLabel,
                    { color: isActive ? c.brand[700] : c.textMuted },
                  ]}
                >
                  {s.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {/* Form card */}
        <Animated.View
          style={[styles.formCard, { backgroundColor: c.card, borderColor: c.border, opacity: stepFade }]}
        >
          {/* STEP 1: Basic */}
          {step === 1 && (
            <View style={{ gap: 4 }}>
              <AppInput
                label="Patient ID"
                required
                placeholder="e.g. P-2024-0001"
                value={formData.patient_id}
                onChangeText={(t) => handleChange('patient_id', t)}
                error={errors.patient_id}
              />
              <View style={styles.grid3}>
                <AppInput
                  label="Age"
                  keyboardType="numeric"
                  placeholder="45"
                  value={formData.age ? String(formData.age) : ''}
                  onChangeText={(t) => handleChange('age', t)}
                  error={errors.age}
                  containerStyle={{ width: fieldThirdWidth }}
                />
                <Select
                  label="Gender"
                  required
                  value={formData.gender}
                  options={[
                    { label: 'Male', value: 'Male' },
                    { label: 'Female', value: 'Female' },
                  ]}
                  onChange={(v) => handleChange('gender', String(v))}
                  error={errors.gender}
                  containerStyle={{ width: fieldThirdWidth }}
                />
                <AppInput
                  label="BMI"
                  keyboardType="numeric"
                  placeholder="28.5"
                  value={formData.bmi ? String(formData.bmi) : ''}
                  onChangeText={(t) => handleChange('bmi', t)}
                  error={errors.bmi}
                  containerStyle={{ width: fieldThirdWidth }}
                />
              </View>
            </View>
          )}

          {/* STEP 2: Airway */}
          {step === 2 && (
            <View style={{ gap: 4 }}>
              <Select
                label="Mallampati Score"
                required
                value={formData.mallampati_score ? String(formData.mallampati_score) : ''}
                options={MALLAMPATI}
                onChange={(v) => handleChange('mallampati_score', v)}
                error={errors.mallampati_score}
                placeholder="Select"
              />
              <View style={styles.grid2}>
                <AppInput
                  label="TMD (cm)"
                  keyboardType="numeric"
                  placeholder="6.5"
                  value={formData.tmd ? String(formData.tmd) : ''}
                  onChangeText={(t) => handleChange('tmd', t)}
                  error={errors.tmd}
                  containerStyle={{ width: fieldWidth }}
                />
                <AppInput
                  label="SMD (cm)"
                  keyboardType="numeric"
                  placeholder="14.0"
                  value={formData.smd !== undefined ? String(formData.smd) : ''}
                  onChangeText={(t) => handleChange('smd', t)}
                  error={errors.smd}
                  containerStyle={{ width: fieldWidth }}
                />
              </View>
            </View>
          )}

          {/* STEP 3: Physical */}
          {step === 3 && (
            <View style={{ gap: 4 }}>
              <View style={styles.grid2}>
                <AppInput
                  label="Neck Circ (cm)"
                  keyboardType="numeric"
                  placeholder="38.0"
                  value={formData.neck_circumference ? String(formData.neck_circumference) : ''}
                  onChangeText={(t) => handleChange('neck_circumference', t)}
                  error={errors.neck_circumference}
                  containerStyle={{ width: fieldWidth }}
                />
                <AppInput
                  label="Mouth (mm)"
                  keyboardType="numeric"
                  placeholder="40.0"
                  value={formData.mouth_opening !== undefined ? String(formData.mouth_opening) : ''}
                  onChangeText={(t) => handleChange('mouth_opening', t)}
                  error={errors.mouth_opening}
                  containerStyle={{ width: fieldWidth }}
                />
              </View>
              <AppInput
                label="Neck Movement (Â°)"
                keyboardType="numeric"
                placeholder="85"
                value={formData.neck_movement !== undefined ? String(formData.neck_movement) : ''}
                onChangeText={(t) => handleChange('neck_movement', t)}
                error={errors.neck_movement}
              />

              {/* More findings toggle */}
              <Pressable
                onPress={() => setShowAdvanced((s) => !s)}
                style={styles.moreToggle}
              >
                <ChevronDown
                  size={12}
                  color={c.brand[600]}
                  style={{ transform: [{ rotate: showAdvanced ? '180deg' : '0deg' }] }}
                />
                <Text style={[styles.moreText, { color: c.brand[600] }]}>
                  {showAdvanced ? 'Less' : 'More'} findings
                </Text>
              </Pressable>

              {showAdvanced && (
                <View style={styles.grid2}>
                  <Select
                    label="Beard"
                    value={formData.beard ?? 'No'}
                    options={YES_NO}
                    onChange={(v) => handleChange('beard', String(v))}
                    containerStyle={{ width: fieldWidth }}
                  />
                  <Select
                    label="Chest"
                    value={formData.chest_size ?? 'Medium'}
                    options={[
                      { label: 'Small', value: 'Small' },
                      { label: 'Medium', value: 'Medium' },
                      { label: 'Large', value: 'Large' },
                    ]}
                    onChange={(v) => handleChange('chest_size', String(v))}
                    containerStyle={{ width: fieldWidth }}
                  />
                  <Select
                    label="Neck"
                    value={formData.neck_structure ?? 'Normal'}
                    options={[
                      { label: 'Normal', value: 'Normal' },
                      { label: 'Abnormal', value: 'Abnormal' },
                    ]}
                    onChange={(v) => handleChange('neck_structure', String(v))}
                    containerStyle={{ width: fieldWidth }}
                  />
                  <Select
                    label="Jaw"
                    value={formData.jaw_movement ?? 'Normal'}
                    options={[
                      { label: 'Normal', value: 'Normal' },
                      { label: 'Reduced', value: 'Reduced' },
                    ]}
                    onChange={(v) => handleChange('jaw_movement', String(v))}
                    containerStyle={{ width: fieldWidth }}
                  />
                  <Select
                    label="Tissue"
                    value={formData.tissue_flexibility ?? 'Normal'}
                    options={[
                      { label: 'Normal', value: 'Normal' },
                      { label: 'Reduced', value: 'Reduced' },
                    ]}
                    onChange={(v) => handleChange('tissue_flexibility', String(v))}
                    containerStyle={{ width: fieldWidth }}
                  />
                </View>
              )}
            </View>
          )}

          {/* STEP 4: History */}
          {step === 4 && (
            <View style={styles.grid2}>
              {([
                ['previous_airway_records', 'Previous Airway Records'],
                ['disease_arthritis', 'Arthritis'],
                ['disease_diabetes', 'Diabetes'],
                ['disease_down_syndrome', 'Down Syndrome'],
                ['breathing_snoring', 'Snoring'],
                ['breathing_sleep_apnea', 'Sleep Apnea'],
                ['symptom_voice_changes', 'Voice Changes'],
                ['symptom_difficulty_swallowing', 'Difficulty Swallowing'],
                ['symptom_cant_lie_flat', "Can't Lie Flat"],
                ['injury_swelling', 'Swelling'],
                ['injury_previous_neck_fracture', 'Previous Neck Fracture'],
                ['previous_emergencies_icu', 'Previous Emergencies/ICU'],
              ] as [keyof PredictionInput, string][]).map(([field, label]) => (
                <Select
                  key={field}
                  label={label}
                  value={String(formData[field] ?? 'No')}
                  options={YES_NO}
                  onChange={(v) => handleChange(field, String(v))}
                  containerStyle={{ width: fieldWidth }}
                />
              ))}
            </View>
          )}

          {Object.keys(errors).length > 0 && step === 4 ? (
            <View style={[styles.errorBar, { backgroundColor: c.danger[50], borderColor: c.danger[200] }]}>
              <AlertCircle size={14} color={c.danger[600]} />
              <Text style={[styles.errorBarText, { color: c.danger[600] }]}>
                Fix errors above before submitting
              </Text>
            </View>
          ) : null}

          {submitError ? (
            <Banner variant="danger" icon={<AlertCircle size={16} color={c.danger[500]} />}>
              {submitError}
            </Banner>
          ) : null}

          {/* Nav buttons */}
          <View style={styles.navRow}>
            {step > 1 ? (
              <AppButton
                title="Back"
                variant="secondary"
                onPress={goBack}
                disabled={predicting}
                style={canFitTwoColumns ? { flex: 1 } : { width: '100%' }}
              />
            ) : null}
            {step < 4 ? (
              <AppButton
                title="Next"
                onPress={goNext}
                style={canFitTwoColumns ? { flex: 1 } : { width: '100%' }}
              />
            ) : (
              <AppButton
                title={predicting ? 'Assessing...' : 'Assess Patient'}
                onPress={handleSubmit}
                loading={predicting}
                icon={!predicting ? <Activity size={16} color="#111111" /> : undefined}
                style={canFitTwoColumns ? { flex: 1 } : { width: '100%' }}
              />
            )}
          </View>

          {predicting && predictingSlow ? (
            <View style={[styles.slowNote, { backgroundColor: c.warning[50], borderColor: c.ink }]}>
              <ActivityIndicator size="small" color={c.warning[600]} />
              <Text style={[styles.slowNoteText, { color: c.warning[700] }]}>
                The LLM response is taking longer than usual. Please waitâ€¦
              </Text>
            </View>
          ) : null}
        </Animated.View>
      </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 16,
    paddingBottom: 120,
    gap: 14,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  headerIcon: {
    width: 30,
    height: 30,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: '600',
    fontFamily: 'Inter_600SemiBold',
  },
  headerSub: {
    fontSize: 11,
    textTransform: 'capitalize',
    fontFamily: 'Inter_400Regular',
  },
  fixtureRow: {
    flexDirection: 'row',
    gap: 6,
    flexWrap: 'wrap',
  },
  fixtureBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  fixtureText: {
    fontSize: 11,
    fontWeight: '600',
    fontFamily: 'Inter_600SemiBold',
  },
  steps: {
    flexDirection: 'row',
    borderWidth: 2,
    borderRadius: 5,
    padding: 3,
    gap: 2,
  },
  stepTab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: 7,
    paddingHorizontal: 2,
    borderRadius: radii.sm,
    minWidth: 0,
  },
  stepLabel: {
    fontSize: 11,
    fontWeight: '600',
    fontFamily: 'Inter_600SemiBold',
    flexShrink: 1,
  },
  formCard: {
    borderWidth: 1,
    borderRadius: radii.lg,
    padding: 16,
    gap: 4,
  },
  grid3: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  grid2: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  moreToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 4,
    alignSelf: 'flex-start',
  },
  moreText: {
    fontSize: 12,
    fontWeight: '500',
    fontFamily: 'Inter_500Medium',
  },
  errorBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderWidth: 1,
    borderRadius: 8,
    padding: 10,
    marginTop: 4,
  },
  errorBarText: {
    fontSize: 11,
    fontWeight: '500',
    fontFamily: 'Inter_500Medium',
  },
  navRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginTop: 16,
  },
  slowNote: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 2,
    borderRadius: 6,
    padding: 10,
    marginTop: 12,
  },
  slowNoteText: {
    fontSize: 12,
    fontWeight: '500',
    flex: 1,
    fontFamily: 'Inter_500Medium',
  },
});