import React from 'react';
import { View, ActivityIndicator, StyleSheet, Pressable } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator, BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { LayoutDashboard, History, FileText, Settings as SettingsIcon, Stethoscope } from 'lucide-react-native';

import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/theme/ThemeProvider';
import { useReduceMotion } from '@/hooks/useReduceMotion';

import LoginScreen from '@/screens/auth/LoginScreen';
import SignupScreen from '@/screens/auth/SignupScreen';
import DashboardScreen from '@/screens/home/DashboardScreen';
import AssessmentScreen from '@/screens/home/AssessmentScreen';
import PredictionResultScreen from '@/screens/home/PredictionResultScreen';
import HistoryScreen from '@/screens/history/HistoryScreen';
import ReportsScreen from '@/screens/reports/ReportsScreen';
import ReportDetailScreen from '@/screens/reports/ReportDetailScreen';
import SettingsScreen from '@/screens/settings/SettingsScreen';
import AboutScreen from '@/screens/settings/AboutScreen';

import type { PredictionInput, PredictionResponse, PredictionHistory } from '@/types';

export type HomeStackParamList = {
  Dashboard: undefined;
  Assessment: { initialData?: PredictionInput } | undefined;
  PredictionResult: { result: PredictionResponse; input: PredictionInput };
  ReportDetail: { prediction: PredictionHistory };
};

export type HistoryStackParamList = {
  History: undefined;
  ReportDetail: { prediction: PredictionHistory };
};

export type ReportsStackParamList = {
  ReportsList: undefined;
  ReportDetail: { prediction: PredictionHistory };
};

export type SettingsStackParamList = {
  SettingsMain: undefined;
  About: undefined;
};

export type TabParamList = {
  Home: undefined;
  Records: undefined;
  Reports: undefined;
  Settings: undefined;
};

const HomeStackNav = createNativeStackNavigator<HomeStackParamList>();
const HistoryStackNav = createNativeStackNavigator<HistoryStackParamList>();
const ReportsStackNav = createNativeStackNavigator<ReportsStackParamList>();
const SettingsStackNav = createNativeStackNavigator<SettingsStackParamList>();
const Tab = createBottomTabNavigator();
const RootStack = createNativeStackNavigator();

function HomeStack() {
  const reduceMotion = useReduceMotion();
  return (
    <HomeStackNav.Navigator
      screenOptions={{
        headerShown: false,
        animation: reduceMotion ? 'fade' : 'slide_from_right',
        animationDuration: reduceMotion ? 0 : 240,
      }}
    >
      <HomeStackNav.Screen name="Dashboard" component={DashboardScreen} />
      <HomeStackNav.Screen name="Assessment" component={AssessmentScreen} />
      <HomeStackNav.Screen name="PredictionResult" component={PredictionResultScreen} />
      <HomeStackNav.Screen name="ReportDetail" component={ReportDetailScreen} />
    </HomeStackNav.Navigator>
  );
}

function HistoryStack() {
  const reduceMotion = useReduceMotion();
  return (
    <HistoryStackNav.Navigator
      screenOptions={{
        headerShown: false,
        animation: reduceMotion ? 'fade' : 'slide_from_right',
        animationDuration: reduceMotion ? 0 : 240,
      }}
    >
      <HistoryStackNav.Screen name="History" component={HistoryScreen} />
      <HistoryStackNav.Screen name="ReportDetail" component={ReportDetailScreen} />
    </HistoryStackNav.Navigator>
  );
}

function ReportsStack() {
  const reduceMotion = useReduceMotion();
  return (
    <ReportsStackNav.Navigator
      screenOptions={{
        headerShown: false,
        animation: reduceMotion ? 'fade' : 'slide_from_right',
        animationDuration: reduceMotion ? 0 : 240,
      }}
    >
      <ReportsStackNav.Screen name="ReportsList" component={ReportsScreen} />
      <ReportsStackNav.Screen name="ReportDetail" component={ReportDetailScreen} />
    </ReportsStackNav.Navigator>
  );
}

function SettingsStack() {
  const reduceMotion = useReduceMotion();
  return (
    <SettingsStackNav.Navigator
      screenOptions={{
        headerShown: false,
        animation: reduceMotion ? 'fade' : 'slide_from_right',
        animationDuration: reduceMotion ? 0 : 240,
      }}
    >
      <SettingsStackNav.Screen name="SettingsMain" component={SettingsScreen} />
      <SettingsStackNav.Screen name="About" component={AboutScreen} />
    </SettingsStackNav.Navigator>
  );
}

const TAB_ICONS: Record<string, any> = {
  Home: LayoutDashboard,
  Records: History,
  Reports: FileText,
  Settings: SettingsIcon,
};

function FloatingTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const { c, isDark } = useTheme();
  const insets = useSafeAreaInsets();

  const barBg = isDark ? '#FFFFFF' : '#111111';
  const activeIconColor = isDark ? '#FFFFFF' : '#111111';
  const inactiveIconColor = isDark ? '#111111' : '#FFFFFF';
  const activeIndicatorBg = isDark ? '#111111' : '#FFFFFF';
  const inactiveIndicatorBg = isDark ? 'rgba(0,0,0,0.14)' : 'rgba(255,255,255,0.14)';

  return (
    <View
      style={[
        styles.homebarWrap,
        {
          paddingBottom: Math.max(insets.bottom, 8),
          paddingLeft: 16,
          paddingRight: 16,
          paddingTop: 8,
        },
      ]}
      pointerEvents="box-none"
    >
      <View
        style={[
          styles.homebar,
          {
            backgroundColor: barBg,
            height: 62,
            borderRadius: 31,
            shadowColor: '#000000',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.18,
            shadowRadius: 12,
            elevation: 6,
          },
        ]}
      >
        {state.routes.map((route, index) => {
          const isFocused = state.index === index;
          const Icon = TAB_ICONS[route.name] ?? LayoutDashboard;

          const onPress = () => {
            const event = navigation.emit({
              type: 'tabPress',
              target: route.key,
              canPreventDefault: true,
            });
            if (!isFocused && !event.defaultPrevented) {
              navigation.navigate(route.name);
            }
          };

          const onLongPress = () => {
            navigation.emit({ type: 'tabLongPress', target: route.key });
          };

          return (
            <Pressable
              key={route.key}
              accessibilityRole="tab"
              accessibilityState={isFocused ? { selected: true } : {}}
              accessibilityLabel={descriptors[route.key].options.title ?? route.name}
              onPress={onPress}
              onLongPress={onLongPress}
              style={styles.homebarSlot}
              hitSlop={6}
            >
              <View
                style={[
                  styles.homebarIndicator,
                  isFocused ? { backgroundColor: activeIndicatorBg } : { backgroundColor: inactiveIndicatorBg },
                ]}
              >
                <Icon
                  size={22}
                  color={isFocused ? activeIconColor : inactiveIconColor}
                  strokeWidth={isFocused ? 2.5 : 2}
                />
              </View>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function MainTabs() {
  const { c } = useTheme();
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          position: 'absolute',
          backgroundColor: 'transparent',
          borderTopWidth: 0,
          elevation: 0,
        },
        sceneStyle: { backgroundColor: c.page },
      }}
      tabBar={(props) => <FloatingTabBar {...props} />}
    >
      <Tab.Screen name="Home" component={HomeStack} options={{ title: 'Home' }} />
      <Tab.Screen name="Records" component={HistoryStack} options={{ title: 'Records' }} />
      <Tab.Screen name="Reports" component={ReportsStack} options={{ title: 'Reports' }} />
      <Tab.Screen name="Settings" component={SettingsStack} options={{ title: 'Settings' }} />
    </Tab.Navigator>
  );
}

function LoadingScreen() {
  const { c } = useTheme();
  return (
    <View style={[styles.loading, { backgroundColor: '#111111' }]}>
      <View
        style={{
          width: 64,
          height: 64,
          borderRadius: 14,
          backgroundColor: '#111111',
          borderWidth: 2,
          borderColor: c.neutral[600],
          alignItems: 'center',
          justifyContent: 'center',
          shadowColor: '#FFD900',
          shadowOffset: { width: 4, height: 4 },
          shadowOpacity: 1,
          shadowRadius: 0,
          elevation: 4,
        }}
      >
        <Stethoscope size={30} color="#FFFFFF" />
      </View>
      <ActivityIndicator color={c.brand[500]} style={{ marginTop: 20 }} size="large" />
    </View>
  );
}

function RootNavigator() {
  const { token, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <RootStack.Navigator screenOptions={{ headerShown: false }}>
      {token ? (
        <RootStack.Screen name="Main" component={MainTabs} />
      ) : (
        <>
          <RootStack.Screen name="Login" component={LoginScreen} />
          <RootStack.Screen name="Signup" component={SignupScreen} />
        </>
      )}
    </RootStack.Navigator>
  );
}

export default function AppNavigator() {
  const { c, isDark } = useTheme();
  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <NavigationContainer>
        <RootNavigator />
      </NavigationContainer>
    </>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  homebarWrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'transparent',
  },
  homebar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 6,
  },
  homebarSlot: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
    minWidth: 48,
  },
  homebarIndicator: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
});