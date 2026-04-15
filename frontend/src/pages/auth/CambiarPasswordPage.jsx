/**
 * CambiarPasswordPage.jsx — Pantalla de cambio de contraseña temporal.
 * Se muestra obligatoriamente cuando debe_cambiar_password = true.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, KeyRound } from "lucide-react";
import { toast } from "sonner";

import { cambiarPassword } from "../../api/auth";
import useAuthStore from "../../store/authStore";

const schema = z
  .object({
    password_actual: z.string().min(1, "Ingresa tu contraseña actual."),
    password_nueva: z
      .string()
      .min(8, "La nueva contraseña debe tener al menos 8 caracteres."),
    password_confirmar: z.string().min(1, "Confirma tu nueva contraseña."),
  })
  .refine((d) => d.password_nueva === d.password_confirmar, {
    message: "Las contraseñas no coinciden.",
    path: ["password_confirmar"],
  });

export default function CambiarPasswordPage() {
  const navigate = useNavigate();
  const marcarPasswordCambiado = useAuthStore((s) => s.marcarPasswordCambiado);
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState({ actual: false, nueva: false, confirmar: false });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });

  const toggleShow = (field) => setShow((prev) => ({ ...prev, [field]: !prev[field] }));

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      await cambiarPassword({
        password_actual: values.password_actual,
        password_nueva: values.password_nueva,
      });
      marcarPasswordCambiado();
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
            <InputPassword
              name="password_actual"
              label="Contraseña temporal actual"
              showField="actual"
            />
            <InputPassword
              name="password_nueva"
              label="Nueva contraseña (mínimo 8 caracteres)"
              showField="nueva"
            />
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
