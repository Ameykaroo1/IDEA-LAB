/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#F8FAFC",
        surface: "#FFFFFF",
        primaryText: "#0F172A",
        secondaryText: "#64748B",
        borderColor: "#E2E8F0",
        accent: "#10B981",
        accentDark: "#059669",
        accentLight: "#ECFDF5",
        accentBorder: "#A7F3D0",
      },
    },
  },
  plugins: [],
}
