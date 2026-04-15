/**
 * LoginPage.jsx — Pantalla de inicio de sesión.
 * Usa colores institucionales definidos en tailwind.config.js.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, LogIn } from "lucide-react";
import { toast } from "sonner";

import { login } from "../../api/auth";
import useAuthStore from "../../store/authStore";

const schema = z.object({
  email: z.string().email("Ingresa un correo electrónico válido."),
  password: z.string().min(1, "La contraseña es requerida."),
});

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
    <div className="min-h-screen flex items-center justify-center bg-neutral-light">
      <div className="w-full max-w-md">
        {/* Logo / Header */}
        <div className="bg-primary rounded-t-2xl px-8 py-8 text-center">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-primary font-bold text-2xl">MB</span>
          </div>
          <h1 className="text-white text-2xl font-bold tracking-tight">
            Medicamentos de Alto Costo
          </h1>
          <p className="text-white/70 text-sm mt-1">IMSS Bienestar</p>
        </div>

        {/* Formulario */}
        <div className="bg-white rounded-b-2xl shadow-lg px-8 py-8">
          <h2 className="text-neutral-black text-lg font-semibold mb-6">
            Iniciar sesión
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Correo electrónico
              </label>
              <input
                type="email"
                autoComplete="email"
                placeholder="usuario@imssbienestar.gob.mx"
                className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/30 focus:border-primary
                  ${errors.email ? "border-red-400 bg-red-50" : "border-neutral-gray/40 bg-neutral-light"}`}
                {...register("email")}
              />
              {errors.email && (
                <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className={`w-full px-4 py-2.5 pr-10 rounded-lg border text-sm outline-none transition
                    focus:ring-2 focus:ring-primary/30 focus:border-primary
                    ${errors.password ? "border-red-400 bg-red-50" : "border-neutral-gray/40 bg-neutral-light"}`}
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-gray hover:text-neutral-black"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            {/* Botón */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark
                text-white font-semibold py-2.5 rounded-lg transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <LogIn size={16} />
              )}
              {loading ? "Iniciando sesión..." : "Entrar"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
