/**
 * ActivarCuentaPage.jsx — Activación de cuenta vía enlace de un solo uso.
 *
 * Pública (sin sesión): se llega aquí desde el enlace del correo de alta
 * (autoservicio o "Nuevo usuario"). El token del enlace reemplaza a la
 * contraseña temporal reutilizable (SAST-14) — la persona elige su propia
 * contraseña aquí, y queda con sesión iniciada al terminar.
 */
import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, ShieldCheck, TriangleAlert } from "lucide-react";
import { toast } from "sonner";

import { activarCuenta } from "../../api/auth";
import useAuthStore from "../../store/authStore";

// Medidor de fortaleza puramente indicativo (UX) — la validación real
// (longitud, blocklist de contraseñas comunes) la hace el backend.
function calcularFortaleza(password) {
  if (!password) return { nivel: 0, etiqueta: "", color: "bg-neutral-gray/20" };
  let puntos = 0;
  if (password.length >= 15) puntos += 1;
  if (password.length >= 20) puntos += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) puntos += 1;
  if (/\d/.test(password)) puntos += 1;
  if (/[^A-Za-z0-9]/.test(password)) puntos += 1;

  if (puntos <= 1) return { nivel: 1, etiqueta: "Débil", color: "bg-red-500" };
  if (puntos <= 3) return { nivel: 2, etiqueta: "Aceptable", color: "bg-yellow-500" };
  return { nivel: 3, etiqueta: "Fuerte", color: "bg-green-600" };
}

const schema = z
  .object({
    nombre_usuario: z.string().min(2, "Ingresa tu nombre de usuario.").max(150),
    password_nueva: z
      .string()
      .min(15, "La contraseña debe tener al menos 15 caracteres.")
      .max(72, "La contraseña no puede exceder 72 caracteres."),
    password_confirmar: z.string().min(1, "Confirma tu contraseña."),
  })
  .refine((d) => d.password_nueva === d.password_confirmar, {
    message: "Las contraseñas no coinciden.",
    path: ["password_confirmar"],
  });

export default function ActivarCuentaPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const login = useAuthStore((s) => s.login);
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState({ nueva: false, confirmar: false });

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });

  const passwordNueva = watch("password_nueva") || "";
  const fortaleza = calcularFortaleza(passwordNueva);
  const toggleShow = (field) => setShow((prev) => ({ ...prev, [field]: !prev[field] }));

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      const data = await activarCuenta({
        token,
        password_nueva: values.password_nueva,
        nombre_usuario: values.nombre_usuario,
      });
      login(data);
      toast.success("Cuenta activada. ¡Bienvenido!");
      navigate("/pacientes", { replace: true });
    } catch (err) {
      const detalle = err.response?.data?.detail;
      const mensaje = Array.isArray(detalle)
        ? detalle.map((e) => e.msg).join(". ")
        : detalle || "No se pudo activar la cuenta.";
      toast.error(mensaje);
    } finally {
      setLoading(false);
    }
  };

  const InputPassword = ({ name, label, showField }) => (
    <div>
      <label className="block text-sm font-medium text-neutral-black mb-1">{label}</label>
      <div className="relative">
        <input
          type={show[showField] ? "text" : "password"}
          placeholder="••••••••"
          className={`w-full px-4 py-2.5 pr-10 rounded-lg border text-sm outline-none transition
            focus:ring-2 focus:ring-primary/30 focus:border-primary
            ${errors[name] ? "border-red-400 bg-red-50" : "border-neutral-gray/40 bg-neutral-light"}`}
          {...register(name)}
        />
        <button
          type="button"
          onClick={() => toggleShow(showField)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-gray hover:text-neutral-black"
        >
          {show[showField] ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {errors[name] && <p className="text-red-500 text-xs mt-1">{errors[name].message}</p>}
    </div>
  );

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-light">
        <div className="w-full max-w-md text-center bg-white rounded-2xl shadow-lg px-8 py-10">
          <TriangleAlert size={32} className="mx-auto text-amber-500 mb-3" />
          <h1 className="text-lg font-bold text-neutral-black">Enlace incompleto</h1>
          <p className="text-sm text-neutral-gray mt-2">
            Este enlace no incluye un token de activación válido. Ábrelo directamente desde
            el correo que recibiste, o solicita uno nuevo desde el login.
          </p>
          <Link
            to="/login"
            className="inline-block mt-5 px-4 py-2.5 rounded-lg bg-primary hover:bg-primary-dark
              text-white text-sm font-medium transition"
          >
            Ir al login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-light">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="bg-primary-dark rounded-t-2xl px-8 py-8 text-center">
          <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <ShieldCheck size={28} className="text-white" />
          </div>
          <h1 className="text-white text-xl font-bold">Activa tu cuenta</h1>
          <p className="text-white/70 text-sm mt-2">
            Elige tu nombre de usuario y crea tu contraseña para terminar de activar tu acceso.
          </p>
        </div>

        {/* Formulario */}
        <div className="bg-white rounded-b-2xl shadow-lg px-8 py-8">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Nombre de usuario
              </label>
              <input
                type="text"
                placeholder="Tu nombre completo"
                className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/30 focus:border-primary
                  ${errors.nombre_usuario ? "border-red-400 bg-red-50" : "border-neutral-gray/40 bg-neutral-light"}`}
                {...register("nombre_usuario")}
              />
              {errors.nombre_usuario && (
                <p className="text-red-500 text-xs mt-1">{errors.nombre_usuario.message}</p>
              )}
            </div>
            <div>
              <InputPassword
                name="password_nueva"
                label="Contraseña (mínimo 15 caracteres)"
                showField="nueva"
              />
              {passwordNueva && (
                <div className="mt-1.5">
                  <div className="h-1.5 w-full bg-neutral-gray/20 rounded-full overflow-hidden flex gap-0.5">
                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className={`h-full flex-1 rounded-full transition-colors ${
                          fortaleza.nivel >= i ? fortaleza.color : "bg-neutral-gray/20"
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-neutral-gray mt-1">
                    Fortaleza: <span className="font-medium">{fortaleza.etiqueta}</span>
                  </p>
                </div>
              )}
            </div>
            <InputPassword
              name="password_confirmar"
              label="Confirmar contraseña"
              showField="confirmar"
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark
                text-white font-semibold py-2.5 rounded-lg transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <ShieldCheck size={16} />
              )}
              {loading ? "Activando..." : "Activar cuenta"}
            </button>
            <p className="text-xs text-neutral-gray text-center">
              El enlace es de un solo uso y expira 48 horas después de generarse.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
