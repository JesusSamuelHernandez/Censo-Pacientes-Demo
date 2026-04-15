/**
 * UnidadesPage.jsx — Catálogo de unidades médicas (Solo SUPER_ADMIN).
 * Permite listar, crear y editar unidades médicas.
 */
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Pencil, X, Save, Building2 } from "lucide-react";
import { toast } from "sonner";

import {
  listarUnidades,
  crearUnidad,
  actualizarUnidad,
} from "../../api/catalogos";

const schemaCrear = z.object({
  clues: z
    .string()
    .min(1, "El CLUES es requerido.")
    .max(20)
    .regex(/^[A-Z0-9]+$/i, "Solo letras y números."),
  nombre_de_la_unidad: z.string().min(1, "El nombre es requerido.").max(255),
  id_entidad: z.string().min(1, "La entidad es requerida.").max(100),
  categoria_gerencial: z.string().max(150).optional().or(z.literal("")),
});

const schemaEditar = z.object({
  nombre_de_la_unidad: z.string().min(1, "El nombre es requerido.").max(255),
  id_entidad: z.string().min(1, "La entidad es requerida.").max(100),
  categoria_gerencial: z.string().max(150).optional().or(z.literal("")),
});

// ── Modal ─────────────────────────────────────────────────────────────────────
function Modal({ item, onClose, onGuardado }) {
  const esEdicion = Boolean(item);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(esEdicion ? schemaEditar : schemaCrear),
    defaultValues: esEdicion
      ? {
          nombre_de_la_unidad: item.nombre_de_la_unidad,
          id_entidad: item.id_entidad,
          categoria_gerencial: item.categoria_gerencial ?? "",
        }
      : { clues: "", nombre_de_la_unidad: "", id_entidad: "", categoria_gerencial: "" },
  });

  const onSubmit = async (values) => {
    setLoading(true);
    try {
      if (esEdicion) {
        const payload = {
          nombre_de_la_unidad: values.nombre_de_la_unidad,
          id_entidad: values.id_entidad,
          categoria_gerencial: values.categoria_gerencial || undefined,
        };
        await actualizarUnidad(item.clues, payload);
        toast.success("Unidad actualizada.");
      } else {
        const payload = {
          clues: values.clues.toUpperCase(),
          nombre_de_la_unidad: values.nombre_de_la_unidad,
          id_entidad: values.id_entidad,
          categoria_gerencial: values.categoria_gerencial || undefined,
        };
        await crearUnidad(payload);
        toast.success("Unidad registrada.");
      }
      onGuardado();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Error al guardar.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-gray/20">
          <h3 className="font-semibold text-neutral-black">
            {esEdicion ? `Editar — ${item.clues}` : "Nueva unidad médica"}
          </h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-neutral-gray hover:text-neutral-black hover:bg-neutral-light transition"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          {!esEdicion && (
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                CLUES <span className="text-primary">*</span>
              </label>
              <input
                type="text"
                placeholder="ej. ZSIMB002406"
                className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition uppercase
                  focus:ring-2 focus:ring-primary/20 focus:border-primary
                  ${errors.clues ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                {...register("clues")}
              />
              {errors.clues && (
                <p className="text-red-500 text-xs mt-1">{errors.clues.message}</p>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-neutral-black mb-1">
              Nombre de la unidad <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              placeholder="ej. Hospital General de Zacatecas"
              className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                focus:ring-2 focus:ring-primary/20 focus:border-primary
                ${errors.nombre_de_la_unidad ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
              {...register("nombre_de_la_unidad")}
            />
            {errors.nombre_de_la_unidad && (
              <p className="text-red-500 text-xs mt-1">{errors.nombre_de_la_unidad.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Entidad <span className="text-primary">*</span>
              </label>
              <input
                type="text"
                placeholder="ej. ZACATECAS"
                className={`w-full px-4 py-2.5 rounded-lg border text-sm outline-none transition
                  focus:ring-2 focus:ring-primary/20 focus:border-primary
                  ${errors.id_entidad ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}
                {...register("id_entidad")}
              />
              {errors.id_entidad && (
                <p className="text-red-500 text-xs mt-1">{errors.id_entidad.message}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-black mb-1">
                Categoría gerencial{" "}
                <span className="text-neutral-gray font-normal">(opcional)</span>
              </label>
              <input
                type="text"
                placeholder="ej. Segundo nivel"
                className="w-full px-4 py-2.5 rounded-lg border border-neutral-gray/30 bg-neutral-light
                  text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
                {...register("categoria_gerencial")}
              />
            </div>
          </div>

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
              {loading ? "Guardando..." : esEdicion ? "Guardar cambios" : "Registrar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const ENTIDADES = [
  "AGUASCALIENTES",
  "BAJA CALIFORNIA",
  "BAJA CALIFORNIA SUR",
  "CAMPECHE",
  "CHIAPAS",
  "CHIHUAHUA",
  "CIUDAD DE MEXICO",
  "COAHUILA",
  "COLIMA",
  "DURANGO",
  "MEXICO",
  "GUANAJUATO",
  "GUERRERO",
  "HIDALGO",
  "JALISCO",
  "MICHOACAN DE OCAMPO",
  "MORELOS",
  "NAYARIT",
  "NUEVO LEON",
  "OAXACA",
  "PUEBLA",
  "QUERETARO",
  "QUINTANA ROO",
  "SAN LUIS POTOSI",
  "SINALOA",
  "SONORA",
  "TABASCO",
  "TAMAULIPAS",
  "TLAXCALA",
  "VERACRUZ DE IGNACIO DE LA LLAVE",
  "YUCATAN",
  "ZACATECAS",
];

// ── Página principal ──────────────────────────────────────────────────────────
export default function UnidadesPage() {
  const [unidades, setUnidades] = useState([]);
  const [entidad, setEntidad] = useState("BAJA CALIFORNIA");
  const [busqueda, setBusqueda] = useState("");
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState({ open: false, item: null });

  const cargar = async (entidadSeleccionada) => {
    setLoading(true);
    try {
      const data = await listarUnidades(entidadSeleccionada);
      setUnidades(data);
    } catch {
      toast.error("Error al cargar unidades.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(entidad); }, [entidad]);

  const handleEntidadChange = (e) => {
    setEntidad(e.target.value);
    setBusqueda("");
  };

  const filtradas = busqueda.length < 2
    ? unidades
    : unidades.filter(
        (u) =>
          u.clues.toLowerCase().includes(busqueda.toLowerCase()) ||
          u.nombre_de_la_unidad.toLowerCase().includes(busqueda.toLowerCase()) ||
          (u.categoria_gerencial ?? "").toLowerCase().includes(busqueda.toLowerCase())
      );

  const cerrarModal = () => setModal({ open: false, item: null });
  const onGuardado = () => { cerrarModal(); cargar(); };

  return (
    <div className="space-y-4">
      {/* Encabezado */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-neutral-black">
            Unidades Médicas
          </h2>
          <p className="text-sm text-neutral-gray mt-0.5">
            Directorio de unidades médicas registradas en el sistema.
          </p>
        </div>
        <button
          onClick={() => setModal({ open: true, item: null })}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary hover:bg-primary-dark
            text-white text-sm font-medium transition"
        >
          <Plus size={16} />
          Nueva unidad
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 px-4 py-3 flex flex-wrap items-center gap-4">
        <select
          value={entidad}
          onChange={handleEntidadChange}
          className="px-4 py-2 rounded-lg border border-neutral-gray/30 bg-neutral-light
            text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
        >
          {ENTIDADES.map((e) => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Buscar por CLUES, nombre o categoría..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="flex-1 min-w-[220px] px-4 py-2 rounded-lg border border-neutral-gray/30 bg-neutral-light
            text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
        />
        <span className="text-xs text-neutral-gray ml-auto">
          {filtradas.length} unidad(es)
        </span>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-neutral-gray/20 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-light border-b border-neutral-gray/20">
                <th className="text-left px-4 py-3 font-semibold text-neutral-black whitespace-nowrap">CLUES</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Nombre de la Unidad</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black whitespace-nowrap">Entidad</th>
                <th className="text-left px-4 py-3 font-semibold text-neutral-black">Categoría Gerencial</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="text-center py-12">
                    <div className="flex justify-center">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                  </td>
                </tr>
              ) : filtradas.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12">
                    <Building2 size={32} className="mx-auto text-neutral-gray/40 mb-2" />
                    <p className="text-neutral-gray text-sm">Sin registros.</p>
                  </td>
                </tr>
              ) : (
                filtradas.map((u) => (
                  <tr key={u.clues} className="border-b border-neutral-gray/10 hover:bg-neutral-light/60">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-neutral-black whitespace-nowrap">
                      {u.clues}
                    </td>
                    <td className="px-4 py-3 font-medium text-neutral-black">
                      {u.nombre_de_la_unidad}
                    </td>
                    <td className="px-4 py-3 text-neutral-gray whitespace-nowrap">
                      {u.id_entidad}
                    </td>
                    <td className="px-4 py-3 text-neutral-gray">
                      {u.categoria_gerencial ?? <span className="text-neutral-gray/40">—</span>}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => setModal({ open: true, item: u })}
                        className="p-1.5 rounded-lg text-neutral-gray hover:text-primary hover:bg-primary/10 transition"
                        title="Editar"
                      >
                        <Pencil size={15} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {modal.open && (
        <Modal item={modal.item} onClose={cerrarModal} onGuardado={onGuardado} />
      )}
    </div>
  );
}
