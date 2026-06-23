/**
 * PuestoCombobox.jsx — Campo de búsqueda de puestos/especialidades médicas.
 * Carga el catálogo una vez (catálogo fijo y acotado, ~154 entradas) y
 * filtra localmente. Sin límite de resultados: a diferencia de UnidadCombobox
 * (cientos/miles de unidades), aquí se puede mostrar el catálogo completo
 * sin afectar el rendimiento.
 */
import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { listarPuestos } from "../../api/catalogos";

export default function PuestoCombobox({ value, onChange, error }) {
  const [puestos, setPuestos] = useState([]);
  const [query, setQuery] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(true);
  const ref = useRef(null);

  useEffect(() => {
    listarPuestos()
      .then(setPuestos)
      .finally(() => setCargando(false));
  }, []);

  // Inicializar el texto del campo si ya hay un valor (modo edición)
  useEffect(() => {
    if (value && puestos.length > 0) {
      const p = puestos.find((p) => p.codigo === value);
      if (p) setQuery(p.denominacion_puesto);
    }
  }, [value, puestos]);

  // Cerrar el dropdown al hacer clic fuera
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setAbierto(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtrados = query.length < 2
    ? puestos
    : puestos.filter((p) => p.denominacion_puesto.toLowerCase().includes(query.toLowerCase()));

  const seleccionar = (p) => {
    onChange(p.codigo);
    setQuery(p.denominacion_puesto);
    setAbierto(false);
  };

  const limpiar = () => {
    onChange("");
    setQuery("");
    setAbierto(false);
  };

  return (
    <div ref={ref} className="relative">
      <div className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm transition
        focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary
        ${error ? "border-red-400 bg-red-50" : "border-neutral-gray/30 bg-neutral-light"}`}>
        <Search size={14} className="text-neutral-gray flex-shrink-0" />
        <input
          type="text"
          placeholder={cargando ? "Cargando puestos..." : "Escribe el puesto o especialidad..."}
          disabled={cargando}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setAbierto(true);
            if (!e.target.value) onChange("");
          }}
          onFocus={() => setAbierto(true)}
          className="flex-1 bg-transparent outline-none text-neutral-black placeholder:text-neutral-gray"
        />
        {query && (
          <button type="button" onClick={limpiar} className="text-neutral-gray hover:text-neutral-black">
            <X size={14} />
          </button>
        )}
      </div>

      {/* Dropdown de resultados */}
      {abierto && filtrados.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg max-h-60 overflow-y-auto">
          {filtrados.map((p) => (
            <li
              key={p.codigo}
              onMouseDown={() => seleccionar(p)}
              className={`px-4 py-2.5 cursor-pointer hover:bg-primary/5 text-sm
                ${value === p.codigo ? "bg-primary/10 text-primary font-medium" : "text-neutral-black"}`}
            >
              {p.denominacion_puesto}
            </li>
          ))}
        </ul>
      )}

      {/* Mensaje de ayuda */}
      {abierto && query.length >= 2 && filtrados.length === 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg px-4 py-3 text-sm text-neutral-gray">
          No se encontraron puestos con ese criterio.
        </div>
      )}
    </div>
  );
}
