import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View } from 'react-native';

// Minimal entry point. Screens (capture, lots, sync status) are wired in
// subsequent UI work; the offline data layer lives under src/.
export default function App() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Kabadi Mitra</Text>
      <Text>Collector-first e-waste bridge</Text>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#14532d',
  },
});
