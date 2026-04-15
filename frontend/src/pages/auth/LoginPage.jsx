/**
 * LoginPage.jsx — Pantalla de inicio de sesión.
 * Estética institucional inspirada en portales Gobierno de México / IMSS Bienestar.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Mail, Lock, LogIn } from "lucide-react";
import { toast } from "sonner";

import { login } from "../../api/auth";
import useAuthStore from "../../store/authStore";

const schema = z.object({
  email: z.string().email("Ingresa un correo electrónico válido."),
  password: z.string().min(1, "La contraseña es requerida."),
});

const ROJO_OSCURO = "#611232";     // PANTONE 7421 C — header barra superior
const GOB_DORADO  = "#9D7836";     // línea dorada separadora

export default function LoginPage() {
  const navigate = useNavigate();
  const loginStore = useAuthStore((s) => s.login);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });

  const onSubmit = async ({ email, password }) => {
    setLoading(true);
    try {
      const data = await login(email, password);
      loginStore(data);
      if (data.debe_cambiar_password) {
        navigate("/cambiar-password", { replace: true });
      } else {
        navigate("/pacientes", { replace: true });
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail || "Error al iniciar sesión. Verifica tus credenciales.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-white">

      {/* ── Barra superior GOB.MX ──────────────────────────────────────── */}
      <header style={{ backgroundColor: ROJO_OSCURO }} className="w-full px-6 py-2 flex items-center justify-between">
        <img
          src="/shared/logos/logoGobiernoMex.png"
          alt="Gobierno de México"
          className="h-7 object-contain"
        />
        <nav className="flex items-center gap-4 text-white text-sm">
          <a href="#" className="hover:underline opacity-90">Trámites</a>
          <span className="opacity-40">|</span>
          <a href="#" className="hover:underline opacity-90">Gobierno</a>
          <button className="ml-1 opacity-90 hover:opacity-100">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
          </button>
        </nav>
      </header>

      {/* ── Franja dorada ──────────────────────────────────────────────── */}
      <div style={{ backgroundColor: GOB_DORADO, height: "4px" }} className="w-full" />

      {/* ── Contenido principal ────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col items-center justify-center py-10 px-4 bg-white">
        {/* Logo superior Gobierno de México */}
        <div className="mb-4">
          <img
            src="/shared/logos/logoGobiernoMex.png"
            alt="Gobierno de México"
            className="h-12 object-contain"
          />
        </div>

        {/* Tarjeta de login — ancho fijado a 380 px para seguir la imagen del header */}
        <div className="rounded-lg overflow-hidden shadow-lg" style={{ width: "320px", maxWidth: "95vw" }}>

          {/* Cabecera — imagen PLECA_LOGO_linea ocupa todo el ancho */}
          <img
            src="/shared/logos/PLECA_LOGO_linea.png"
            alt="IMSS Bienestar — Servicios Públicos de Salud"
            className="w-full block"
          />

          {/* Franja dorada divisora */}
          <div style={{ backgroundColor: GOB_DORADO, height: "5px" }} />

          {/* Formulario */}
          <div className="bg-white px-8 py-7">
            <h2
              className="text-center text-sm font-bold tracking-widest mb-6 uppercase"
              style={{ color: ROJO_OSCURO }}
            >
              Inicio Sesión
            </h2>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

              {/* Email */}
              <div>
                <div className={`flex items-center border-b-2 pb-1 transition
                  ${errors.email ? "border-red-400" : "border-gray-300 focus-within:border-[#006847]"}`}>
                  <Mail size={15} className="mr-2 flex-shrink-0" style={{ color: ROJO_OSCURO }} />
                  <div className="flex-1">
                    <p className="text-xs font-semibold tracking-wider uppercase mb-0.5" style={{ color: ROJO_OSCURO }}>
                      Correo Institucional
                    </p>
                    <input
                      type="email"
                      autoComplete="email"
                      placeholder="usuario@imssbienestar.gob.mx"
                      className="w-full text-sm outline-none bg-transparent text-gray-700 placeholder:text-gray-400"
                      {...register("email")}
                    />
                  </div>
                </div>
                {errors.email && (
                  <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>
                )}
              </div>

              {/* Password */}
              <div>
                <div className={`flex items-center border-b-2 pb-1 transition
                  ${errors.password ? "border-red-400" : "border-gray-300 focus-within:border-[#006847]"}`}>
                  <Lock size={15} className="mr-2 flex-shrink-0" style={{ color: ROJO_OSCURO }} />
                  <div className="flex-1">
                    <p className="text-xs font-semibold tracking-wider uppercase mb-0.5" style={{ color: ROJO_OSCURO }}>
                      Contraseña
                    </p>
                    <input
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      placeholder="••••••••"
                      className="w-full text-sm outline-none bg-transparent text-gray-700 placeholder:text-gray-400"
                      {...register("password")}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="ml-2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
                )}
              </div>

              {/* Botón */}
              <div className="pt-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded
                    text-white text-sm font-semibold tracking-wide transition
                    disabled:opacity-60 disabled:cursor-not-allowed"
                  style={{ backgroundColor: ROJO_OSCURO }}
                  onMouseEnter={(e) => { if (!loading) e.currentTarget.style.backgroundColor = "#004d34"; }}
                  onMouseLeave={(e) => { if (!loading) e.currentTarget.style.backgroundColor = ROJO_OSCURO; }}
                >
                  {loading ? (
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <LogIn size={16} />
                  )}
                  {loading ? "Iniciando sesión..." : "INGRESAR"}
                </button>
              </div>

            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
