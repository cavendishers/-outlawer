import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#f7f0e6",
        bone: "#fff8ea",
        canvas: "#fffdf8",
        muted: "#6f675c",
        neon: "#d8ff19",
        aqua: "#80d6ef",
        peach: "#ffc3a5",
        gold: "#f4d35e",
        mint: "#b8e7c8",
        ember: "#f17c67",
        ink: "#0b0b0b",
      },
      boxShadow: {
        brutal: "6px 6px 0 #0b0b0b",
        brutalSoft: "4px 4px 0 #0b0b0b",
        brutalTiny: "2px 2px 0 #0b0b0b",
      },
    },
  },
  plugins: [],
};

export default config;
