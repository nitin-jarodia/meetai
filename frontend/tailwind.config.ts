import type { Config } from "tailwindcss";
import { COLORS } from "./lib/design-tokens";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          base: "var(--color-bg-base)",
          surface: "var(--color-bg-surface)",
          elevated: "var(--color-bg-elevated)",
          border: "var(--color-bg-border)",
          borderHover: "var(--color-bg-border-hover)",
        },
        brand: {
          primary: "var(--color-brand-primary)",
          primaryHover: "var(--color-brand-primary-hover)",
          primaryDim: "var(--color-brand-primary-dim)",
        },
        semantic: {
          success: "var(--color-semantic-success)",
          warning: "var(--color-semantic-warning)",
          danger: "var(--color-semantic-danger)",
          info: "var(--color-semantic-info)",
        },
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          muted: "var(--color-text-muted)",
          inverse: "var(--color-text-inverse)",
        },
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "20px",
      },
      boxShadow: {
        card: `0 0 0 1px ${COLORS.background.border}`,
        glow: "0 0 24px #6366F130",
        none: "none",
      },
      fontSize: {
        xs: ["12px", "16px"],
        sm: ["13px", "18px"],
        base: ["14px", "20px"],
        lg: ["16px", "24px"],
        xl: ["18px", "26px"],
        "2xl": ["24px", "32px"],
        "3xl": ["32px", "40px"],
        "4xl": ["48px", "56px"],
      },
      transitionDuration: {
        150: "150ms",
        250: "250ms",
      },
    },
  },
  plugins: [],
};

export default config;
