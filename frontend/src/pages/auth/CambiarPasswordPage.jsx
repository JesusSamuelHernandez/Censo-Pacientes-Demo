/**
 * CambiarPasswordPage.jsx — Pantalla de cambio de contraseña temporal.
 * Se muestra obligatoriamente cuando debe_cambiar_password = true.
 */
import { useState } from "react";
import { useNavigate } from "react-router";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, KeyRound } from "lucide-react";
import { toast } from "sonner";

import { cambiarPassword } from "../../api/auth";
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

const construirSchema = (requiereNombre) =>
  z
    .object({
      nombre_usuario: requiereNombre
        ? z.string().min(2, "Ingresa tu nombre de usuario.").max(150)
        : z.string().optional(),
      password_actual: z.string().min(1, "Ingresa tu contraseña actual."),
      password_nueva: z
        .string()
        .min(15, "La nueva contraseña debe tener al menos 15 caracteres.")
        .max(72, "La nueva contraseña no puede exceder 72 caracteres."),
      password_confirmar: z.string().min(1, "Confirma tu nueva contraseña."),
    })
    .refine((d) => d.password_nueva === d.password_confirmar, {
      message: "Las contraseñas no coinciden.",
      path: ["password_confirmar"],
    });

export default function CambiarPasswordPage() {
  const navigate = useNavigate();
  const marcarPasswordCambiado = useAuthStore((s) => s.marcarPasswordCambiado);
  const nombreUsuarioActual = useAuthStore((s) => s.nombreUsuario);
  const requiereNombre = !nombreUsuarioActual;
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState({ actual: false, nueva: false, confirmar: false });

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({ resolver: zodResolver(construirSchema(requiereNombre)) });

  const passwordNueva = watch("password_nueva") || "";
  const fortaleza = calcularFortaleza(passwordNueva);

  const toggleShow = (field) => setShow((prev) => ({ ...prev, [field]: !prev[field] }));

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      const data = await cambiarPassword({
        password_actual: values.password_actual,
        password_nueva: values.password_nueva,
        nombre_usuario: requiereNombre ? values.nombre_usuario : undefined,
      });
      // Cambiar la contraseña invalida el token anterior en el servidor
      // (token_version); el backend emite uno nuevo para no cerrar la sesión.
      marcarPasswordCambiado(requiereNombre ? values.nombre_usuario : undefined, data.access_token);
      toast.success("Contraseña actualizada correctamente.");
      navigate("/pacientes", { replace: true });
    } catch (err) {
      const msg = err.response?.data?.detail || "Error al cambiar la contraseña.";
      toast.error(msg);
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
      {errors[name] && (
        <p className="text-red-500 text-xs mt-1">{errors[name].message}</p>
      )}
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-light">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="bg-primary-dark rounded-t-2xl px-8 py-8 text-center">
          <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <KeyRound size={28} className="text-white" />
          </div>
          <h1 className="text-white text-xl font-bold">Cambio de contraseña requerido</h1>
          <p className="text-white/70 text-sm mt-2">
            Tu cuenta tiene una contraseña temporal. Debes crear una nueva antes de continuar.
          </p>
        </div>

        {/* Formulario */}
        <div className="bg-white rounded-b-2xl shadow-lg px-8 py-8">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {requiereNombre && (
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
            )}
            <InputPassword
              name="password_actual"
              label="Contraseña temporal actual"
              showField="actual"
            />
            <div>
              <InputPassword
                name="password_nueva"
                label="Nueva contraseña (mínimo 15 caracteres)"
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
              label="Confirmar nueva contraseña"
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
                <KeyRound size={16} />
              )}
              {loading ? "Guardando..." : "Guardar nueva contraseña"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
