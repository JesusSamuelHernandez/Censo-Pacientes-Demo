/** @type {import('tailwindcss').Config} */

// ============================================================
// PALETA INSTITUCIONAL — IMSS Bienestar
// Modifica los valores HEX aquí para cambiar colores globalmente.
// ============================================================
const colores = {
  // Rojo principal — botones primarios, header, acentos
  rojo:        "#9b2247",   // PANTONE 7420 C
  rojoOscuro:  "#611232",   // PANTONE 7421 C  ← hover y énfasis

  // Verde institucional — badges activos, éxito
  verde:       "#1e5b4f",   // PANTONE 626 C
  verdeOscuro: "#002f2a",   // PANTONE 627 C   ← hover

  // Dorado — alertas, advertencias
  dorado:      "#a57f2c",   // PANTONE 1255 C
  doradoClaro: "#e6d194",   // PANTONE 7402 C  ← fondos suaves

  // Neutros
  negro:       "#161a1d",   // PANTONE Neutral Black C ← sidebar, textos
  gris:        "#98989a",   // PANTONE Cool Gray 7 C   ← bordes, textos secundarios
  grisClaro:   "#f4f4f5",   // Fondo general de la app
  blanco:      "#ffffff",
};

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Uso: bg-primary, text-primary, border-primary
        primary: {
          DEFAULT: colores.rojo,
          dark:    colores.rojoOscuro,
        },
        // Uso: bg-secondary, text-secondary
        secondary: {
          DEFAULT: colores.verde,
          dark:    colores.verdeOscuro,
        },
        // Uso: bg-warning, text-warning, bg-warning-light
        warning: {
          DEFAULT: colores.dorado,
          light:   colores.doradoClaro,
        },
        // Uso: bg-neutral-black, text-neutral-gray, bg-neutral-light
        neutral: {
          black: colores.negro,
          gray:  colores.gris,
          light: colores.grisClaro,
          white: colores.blanco,
        },
        // Alias directos
        sidebar: colores.negro,
        brand:   colores.rojo,
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
