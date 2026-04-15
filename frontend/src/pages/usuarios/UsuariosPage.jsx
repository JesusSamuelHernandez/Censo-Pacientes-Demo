/**
 * UsuariosPage.jsx — Gestión de cuentas de usuario (Solo SUPER_ADMIN).
 *
 * Flujo de creación:
 *   1. SUPER_ADMIN llena el formulario.
 *   2. Backend genera contraseña temporal y la devuelve una sola vez.
 *   3. Se muestra en modal de contraseña temporal para copiarla.
 *   4. Al primer login el usuario debe cambiarla.
 */
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Pencil, Trash2, X, Save, Copy, Check, Users } from "lucide-react";
import { toast } from "sonner";

import {
  listarUsuarios,
  crearUsuario,
  actualizarUsuario,
  eliminarUsuario,
} from "../../api/usuarios";
import UnidadCombobox from "../../components/shared/UnidadCombobox";

const ROLES = ["SUPER_ADMIN", "ADMIN_ESTATAL", "RESPONSABLE_UNIDAD"];

const ROL_LABEL = {
  SUPER_ADMIN: "Super Administrador",
  ADMIN_ESTATAL: "Admin Estatal",
  RESPONSABLE_UNIDAD: "Responsable de Unidad",
};

const ROL_BADGE = {
  SUPER_ADMIN: "bg-primary/10 text-primary",
  ADMIN_ESTATAL: "bg-secondary/10 text-secondary",
  RESPONSABLE_UNIDAD: "bg-neutral-gray/15 text-neutral-black",
};

const ENTIDADES = [
  "AGUASCALIENTES", "BAJA CALIFORNIA", "BAJA CALIFORNIA SUR", "CAMPECHE",
  "CHIAPAS", "CHIHUAHUA", "CIUDAD DE MEXICO", "COAHUILA", "COLIMA", "DURANGO",
  "MEXICO", "GUANAJUATO", "GUERRERO", "HIDALGO", "JALISCO",
  "MICHOACAN DE OCAMPO", "MORELOS", "NAYARIT", "NUEVO LEON", "OAXACA",
  "PUEBLA", "QUERETARO", "QUINTANA ROO", "SAN LUIS POTOSI", "SINALOA",
  "SONORA", "TABASCO", "TAMAULIPAS", "TLAXCALA",
  "VERACRUZ DE IGNACIO DE LA LLAVE", "YUCATAN", "ZACATECAS",
];

// ── Esquemas de validación ────────────────────────────────────────────────────
const schemaCrear = z
  .object({
    nombre_usuario: z.string().min(2, "Mínimo 2 caracteres.").max(150),
    email: z.string().email("Correo inválido."),
    rol_nombre: z.enum(["SUPER_ADMIN", "ADMIN_ESTATAL", "RESPONSABLE_UNIDAD"], {
      errorMap: () => ({ message: "Selecciona un rol." }),
    }),
    clues_unidad_asignada: z.string().optional(),
    id_entidad: z.string().optional(),
  })
  .superRefine((val, ctx) => {
    if (val.rol_nombre === "RESPONSABLE_UNIDAD" && !val.clues_unidad_asignada) {
      ctx.addIssue({
        path: ["clues_unidad_asignada"],
        code: z.ZodIssueCode.custom,
        message: "Selecciona la unidad asignada.",
      });
    }
    if (val.rol_nombre === "ADMIN_ESTATAL" && !val.id_entidad) {
      ctx.addIssue({
        path: ["id_entidad"],
        code: z.ZodIssueCode.custom,
        message: "Selecciona la entidad asignada.",
      });
    }
  });

const schemaEditar = z.object({
  nombre_usuario: z.string().min(2, "Mínimo 2 caracteres.").max(150).optional().or(z.literal("")),
  rol_nombre: z.enum(["SUPER_ADMIN", "ADMIN_ESTATAL", "RESPONSABLE_UNIDAD"]).optional(),
  clues_unidad_asignada: z.string().optional().or(z.literal("")),
  id_entidad: z.string().optional().or(z.literal("")),
  password: z.string().min(8, "Mínimo 8 caracteres.").optional().or(z.literal("")),
});

// ── Modal de contraseña temporal ──────────────────────────────────────────────
function ModalPasswordTemporal({ usuario, onClose }) {
  const [copiado, setCopiado] = useState(false);

  const copiar = () => {
    navigator.clipboard.writeText(usuario.password_temporal).then(() => {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    });
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="px-6 py-5 border-b border-neutral-gray/20">
          <h3 className="font-semibold text-neutral-black">Usuario creado</h3>
          <p className="text-sm text-neutral-gray mt-0.5">
            Comparte esta contraseña temporal con el usuario. No se volverá a mostrar.
          </p>
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-neutral-gray mb-0.5">Nombre</p>
              <p className="font-medium text-neutral-black">{usuario.nombre_usuario}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-gray mb-0.5">Correo</p>
              <p className="font-medium text-neutral-black">{usuario.email}</p>
            </div>
            <div>
              <p className="text-xs text-neutral-gray mb-0.5">Rol</p>
              <p className="font-medium text-neutral-black">{ROL_LABEL[usuario.rol_nombre]}</p>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-neutral-gray mb-1">Contraseña temporal</p>
            <div className="flex items-center gap-2 bg-neutral-light border border-neutral-gray/30 rounded-lg px-4 py-3">
              <span className="flex-1 font-mono text-lg font-semibold text-neutral-black tracking-widest">
                {usuario.password_temporal}
              </span>
              <button
                onClick={copiar}
                className={`p-1.5 rounded-lg transition ${
                  copiado
                    ? "text-secondary bg-secondary/10"
                    : "text-neutral-gray hover:text-primary hover:bg-primary/10"
                }`}
                title="Copiar contraseña"
              >
                {copiado ? <Check size={16} /> : <Copy size={16} />}
              </button>
            </div>
            <p className="text-xs text-neutral-gray mt-1.5">
              El usuario deberá cambiarla en su primer inicio de sesión.
            </p>
          </div>

          <button
            onClick={onClose}
            className="w-full px-4 py-2.5 rounded-lg bg-primary hover:bg-primary-dark
              text-white text-sm font-medium transition"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal crear/editar ────────────────────────────────────────────────────────
function ModalFormulario({ item, onClose, onGuardado }) {
  const esEdicion = Boolean(item);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esEdicion ? schemaEditar : schemaCrear),
    defaultValues: esEdicion
      ? {
          nombre_usuario: item.nombre_usuario,
          rol_nombre: item.rol_nombre,
          clues_unidad_asignada: item.clues_unidad_asignada ?? "",
          id_entidad: item.id_entidad ?? "",
          password: "",
        }
      : {
          nombre_usuario: "",
          email: "",
          rol_nombre: "",
          clues_unidad_asignada: "",
          id_entidad: "",
        },
  });

  const rolSeleccionado = watch("rol_nombre");
  const cluesSeleccionada = watch("clues_unidad_asignada");

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      if (esEdicion) {
        const payload = Object.fromEntries(
          Object.entries(values).filter(([, v]) => v !== "" && v !== undefined)
        );
        const resultado = await actualizarUsuario(item.id_usuario, payload);
        toast.success("Usuario actualizado.");
        onGuardado(resultado);
      } else {
        const payload = {
          nombre_usuario: values.nombre_usuario,
          email: values.email,
          rol_nombre: values.rol_nombre,
          clues_unidad_asignada: values.clues_unidad_asignada || undefined,
          id_entidad: values.id_entidad || undefined,
        };
        const resultado = await crearUsuario(payload);
        onGuardado(resultado); // incluye password_temporal
      }
    } catch (err) {
      const detalle = err.response?.data?.detail;
      const mensaje = Array.isArray(detalle)
        ? detalle.map((e) => e.msg).join(". ")
        : detalle || "Error al guardar.";
      toast.error(mensaje);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-gray/20 sticky top-0 bg-white z-10">
          <h3 className="font-semibold text-neutral-black">
            {esEdicion ? `Editar — ${item.nombre_usuario}` : "Nuevo usuario"}
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-neutral-gray hover:text-neutral-black hover:bg-neutral-light transition"
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Nombre completo {!esEdicion && <span className="text-primary">*</span>}
            </label>
            <input
              type="text"
              placeholder="ej. Juan Pérez García"
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.nombre_usuario ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("nombre_usuario")}
            />
            {errors.nombre_usuario && (
              <p className="text-red-500 text-xs mt-1">{errors.nombre_usuario.message}</p>
            )}
          </div>

          {/* Email — solo en creación */}
          {!esEdicion && (
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Correo electrónico <span className="text-primary">*</span>
              </label>
              <input
                type="email"
                placeholder="usuario@ejemplo.gob.mx"
                className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/20 focus:border-primary
                  ${errors.email ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                {...register("email")}
              />
              {errors.email && (
                <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>
              )}
            </div>
          )}

          {/* Rol */}
          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Rol {!esEdicion && <span className="text-primary">*</span>}
            </label>
            <select
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.rol_nombre ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("rol_nombre")}
            >
              <option value="">— Selecciona un rol —</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>{ROL_LABEL[r]}</option>
              ))}
            </select>
            {errors.rol_nombre && (
              <p className="text-red-500 text-xs mt-1">{errors.rol_nombre.message}</p>
            )}
          </div>

          {/* Entidad — solo ADMIN_ESTATAL */}
          {rolSeleccionado === "ADMIN_ESTATAL" && (
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Entidad asignada <span className="text-primary">*</span>
              </label>
              <select
                className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/20 focus:border-primary
                  ${errors.id_entidad ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                {...register("id_entidad")}
              >
                <option value="">— Selecciona una entidad —</option>
                {ENTIDADES.map((e) => (
                  <option key={e} value={e}>{e}</option>
                ))}
              </select>
              {errors.id_entidad && (
                <p className="text-red-500 text-xs mt-1">{errors.id_entidad.message}</p>
              )}
            </div>
          )}

          {/* Unidad — solo RESPONSABLE_UNIDAD */}
          {rolSeleccionado === "RESPONSABLE_UNIDAD" && (
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Unidad asignada <span className="text-primary">*</span>
              </label>
              <UnidadCombobox
                value={cluesSeleccionada}
                onChange={(clues) =>
                  setValue("clues_unidad_asignada", clues, { shouldValidate: true })
                }
                error={errors.clues_unidad_asignada}
              />
              {errors.clues_unidad_asignada && (
                <p className="text-red-500 text-xs mt-1">{errors.clues_unidad_asignada.message}</p>
              )}
            </div>
          )}

          {/* Reset contraseña — solo en edición */}
          {esEdicion && (
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Nueva contraseña{" "}
                <span className="text-neutral-gray font-normal">(dejar vacío para no cambiar)</span>
              </label>
              <input
                type="password"
                placeholder="Mínimo 8 caracteres"
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-lg border border-neutral-gray/30
                text-sm text-neutral-gray hover:bg-neutral-light transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark
                text-white text-sm font-medium py-2.5 rounded-lg transition
                disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading
                ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                : <Save size={15} />}
              {loading ? "Guardando..." : esEdicion ? "Guardar cambios" : "Crear usuario"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Modal de confirmación de eliminación ──────────────────────────────────────
function ModalEliminar({ usuario, onClose, onConfirm }) {
  const [loading, setLoading] = useState(false);

  const confirmar = async () => {
    setLoading(true);
    try {
      await eliminarUsuario(usuario.id_usuario);
      toast.success(`Usuario "${usuario.nombre_usuario}" eliminado.`);
      onConfirm();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al eliminar.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
            <Trash2 size={18} className="text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-neutral-black">Eliminar usuario</h3>
            <p className="text-sm text-neutral-gray mt-1">
              ¿Eliminar a <span className="font-medium text-neutral-black">{usuario.nombre_usuario}</span>?
              Esta acción no se puede deshacer.
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-lg border border-neutral-gray/30
              text-sm text-neutral-gray hover:bg-neutral-light transition"
          >
            Cancelar
          </button>
          <button
            onClick={confirmar}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700
              text-white text-sm font-medium py-2.5 rounded-lg transition
              disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading
              ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              : <Trash2 size={15} />}
            {loading ? "Eliminando..." : "Eliminar"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────
export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalForm, setModalForm] = useState({ open: false, item: null });
  const [modalPassword, setModalPassword] = useState(null); // datos del usuario recién creado
  const [modalEliminar, setModalEliminar] = useState(null);

  const cargar = async () => {
    setLoading(true);
    try {
      const data = await listarUsuarios();
      setUsuarios(data);
    } catch {
      toast.error("Error al cargar usuarios.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, []);

  const onGuardadoCrear = (resultado) => {
    setModalForm({ open: false, item: null });
    setModalPassword(resultado); // muestra la contraseña temporal
    cargar();
  };

  const onGuardadoEditar = () => {
    setModalForm({ open: false, item: null });
    toast.success("Usuario actualizado.");
    cargar();
  };

  const onEliminado = () => {
    setModalEliminar(null);
    cargar();
  };

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">Usuarios</h2>
          <p className="text-sm text-neutral-gray mt-0.5">
            Cuentas de acceso a la plataforma.
          </p>
        </div>
        <button
          onClick={() => setModalForm({ open: true, item: null })}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary hover:bg-primary-dark
            text-white text-sm font-medium transition"
        >
          <Plus size={16} />
          Nuevo usuario
        </button>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-light border-b border-neutral-gray/20">
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Nombre</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Correo</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Rol</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Unidad / Entidad</th>
                <th className="text-center px-4 py-3 font-semibold text-neutral-black">Estado</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12">
                    <div className="flex justify-center">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  </td>
                </tr>
              ) : usuarios.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12">
                    <Users size={32} className="mx-auto text-neutral-gray/40 mb-2" />
                    <p className="text-neutral-gray text-sm">Sin usuarios registrados.</p>
                  </td>
                </tr>
              ) : (
                usuarios.map((u) => (
                  <tr key={u.id_usuario} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-4 py-3 font-medium text-neutral-black">
                      {u.nombre_usuario}
                    </td>
                    <td className="px-4 py-3 text-neutral-gray">{u.email}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${ROL_BADGE[u.rol_nombre]}`}>
                        {ROL_LABEL[u.rol_nombre]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-neutral-gray font-mono text-xs">
                      {u.clues_unidad_asignada ?? u.id_entidad ?? (
                        <span className="font-sans text-neutral-gray/40">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {u.debe_cambiar_password ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                          bg-amber-100 text-amber-700">
                          Pendiente
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                          bg-secondary/10 text-secondary">
                          Activo
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setModalForm({ open: true, item: u })}
                          className="p-1.5 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                          title="Editar"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          onClick={() => setModalEliminar(u)}
                          className="p-1.5 rounded-lg text-neutral-gray hover:text-red-600 hover:bg-red-50 transition"
                          title="Eliminar"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modales */}
      {modalForm.open && (
        <ModalFormulario
          item={modalForm.item}
          onClose={() => setModalForm({ open: false, item: null })}
          onGuardado={modalForm.item ? onGuardadoEditar : onGuardadoCrear}
        />
      )}
      {modalPassword && (
        <ModalPasswordTemporal
          usuario={modalPassword}
          onClose={() => setModalPassword(null)}
        />
      )}
      {modalEliminar && (
        <ModalEliminar
          usuario={modalEliminar}
          onClose={() => setModalEliminar(null)}
          onConfirm={onEliminado}
        />
      )}
    </div>
  );
}
