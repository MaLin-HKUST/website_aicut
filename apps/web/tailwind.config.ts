import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#f4f1ea",
        foreground: "#1b1815",
        card: "#fffdf9",
        border: "#d7cec0",
        accent: "#c4633d",
        accentDark: "#8b3a1d",
      },
      boxShadow: {
        panel: "0 20px 50px rgba(78, 54, 33, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;

