import type { Config } from "tailwindcss";
import forms from "@tailwindcss/forms";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "#0057ff",
          navy: "#080c14",
          cyan: "#00c2ff"
        }
      },
      fontFamily: {
        sans: ["IBM Plex Sans Thai", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
        display: ["Barlow Condensed", "sans-serif"]
      },
      animation: {
        "pulse-slow": "pulse 2.5s ease-in-out infinite",
        "scan-line": "scan-line 2.8s linear infinite",
        "fade-in-up": "fade-in-up 420ms ease-out both"
      },
      keyframes: {
        "scan-line": {
          "0%": { transform: "translateY(0%)", opacity: "0.18" },
          "50%": { transform: "translateY(100%)", opacity: "0.28" },
          "100%": { transform: "translateY(0%)", opacity: "0.18" }
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        }
      }
    }
  },
  plugins: [forms]
} satisfies Config;
