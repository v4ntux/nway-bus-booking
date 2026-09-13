/** @type {import('tailwindcss').Config} */

const token = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: token("--c-paper"),
        surface: token("--c-surface"),
        raised: token("--c-raised"),
        ink: token("--c-ink"),
        muted: token("--c-muted"),
        faint: token("--c-faint"),
        line: token("--c-line"),
        hairline: token("--c-hairline"),
        accent: token("--c-accent"),
        "accent-deep": token("--c-accent-deep"),
        "accent-ink": token("--c-accent-ink"),
        "accent-soft": token("--c-accent-soft"),
        "accent-strong": token("--c-accent-strong"),
        sky: token("--c-sky"),
        "sky-soft": token("--c-sky-soft"),
        "sky-ink": token("--c-sky-ink"),
        rose: token("--c-rose"),
        positive: token("--c-positive"),
        "positive-soft": token("--c-positive-soft"),
        danger: token("--c-danger"),
        "danger-soft": token("--c-danger-soft"),
        free: token("--c-free"),
        "free-soft": token("--c-free-soft"),
        taken: token("--c-taken"),
        "taken-soft": token("--c-taken-soft"),
        women: token("--c-women"),
        "women-soft": token("--c-women-soft"),
      },
      fontFamily: {
        sans: ["Outfit Variable", "Outfit", "system-ui", "sans-serif"],
        mono: ["Geist Mono Variable", "Geist Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        control: "14px",
        panel: "20px",
        plate: "28px",
      },
      boxShadow: {
        raise: "var(--shadow-raise)",
        lift: "var(--shadow-lift)",
        glow: "var(--shadow-glow)",
        inset: "var(--shadow-inset)",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16, 1, 0.3, 1)",
        spring: "cubic-bezier(0.22, 1.2, 0.36, 1)",
      },
      keyframes: {
        "fade-rise": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "none" },
        },
        shimmer: {
          from: { backgroundPosition: "200% 0" },
          to: { backgroundPosition: "-200% 0" },
        },
        "pop-in": {
          "0%": { transform: "scale(0.86)" },
          "60%": { transform: "scale(1.05)" },
          "100%": { transform: "scale(1)" },
        },
        "icon-swap": {
          from: { opacity: "0", transform: "rotate(-40deg) scale(0.7)" },
          to: { opacity: "1", transform: "none" },
        },
      },
      animation: {
        "fade-rise": "fade-rise 0.45s cubic-bezier(0.16, 1, 0.3, 1) both",
        shimmer: "shimmer 1.6s linear infinite",
        "pop-in": "pop-in 0.38s cubic-bezier(0.22, 1.2, 0.36, 1)",
        "icon-swap": "icon-swap 0.35s cubic-bezier(0.16, 1, 0.3, 1) both",
      },
    },
  },
  plugins: [],
};
