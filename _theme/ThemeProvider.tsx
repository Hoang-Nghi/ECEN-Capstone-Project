// theme/ThemeProvider.tsx  (we'll import from this)
// 🚫 NO AsyncStorage import here

import React, {
  createContext,
  ReactNode,
  useContext,
  useState,
} from "react";
import { AppTheme, ThemeName, themes } from "./theme";

type ThemeContextValue = {
  theme: AppTheme;
  setThemeName: (name: ThemeName) => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [themeName, setThemeName] = useState<ThemeName>("green");

  // In-memory only for now (no persistence)
  const handleSetThemeName = (name: ThemeName) => {
    setThemeName(name);
  };

  return (
    <ThemeContext.Provider
      value={{ theme: themes[themeName], setThemeName: handleSetThemeName }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used inside a ThemeProvider");
  }
  return ctx;
};
