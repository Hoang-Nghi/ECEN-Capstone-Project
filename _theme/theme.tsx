// theme.ts
export type ThemeName = "green" | "purple" | "dark";

export type AppTheme = {
  name: ThemeName;
  background: string;
  text: string;
  subtleText: string;
  accent: string;
  card: string;
};

export const themes: Record<ThemeName, AppTheme> = {
  green: {
    name: "green",
    background: "#f2f2f2",
    text: "#222222",
    subtleText: "#666666",
    accent: "#00b140",
    card: "#ffffff",
  },
  purple: {
    name: "purple",
    background: "#f6f2ff",
    text: "#241c3b",
    subtleText: "#7a6f9b",
    accent: "#8b5cf6",
    card: "#ffffff",
  },
  dark: {
    name: "dark",
    background: "#0C0F0A",
    card: "#1A1D16",
    text: "#E9F5EE",
    subtleText: "#A5B5AA",
    accent: "#2ECC71",
  }
};
