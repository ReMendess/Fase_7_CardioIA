import { StatusBar } from "expo-status-bar";
import { SafeAreaView } from "react-native";

import ChatScreen from "./src/screens/ChatScreen";
import { colors } from "./src/theme";

export default function App() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <StatusBar style="auto" />
      <ChatScreen />
    </SafeAreaView>
  );
}
