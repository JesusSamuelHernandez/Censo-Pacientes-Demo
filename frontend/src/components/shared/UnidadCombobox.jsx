/**
 * UnidadCombobox.jsx — Campo de búsqueda de unidades médicas.
 * Carga todas las unidades una vez y filtra localmente.
 * Muestra máximo 15 resultados para evitar congelar el navegador.
 */
import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { listarUnidades } from "../../api/catalogos";

export default function UnidadCombobox({ value, onChange, error }) {
  const [unidades, setUnidades] = useState([]);
  const [query, setQuery] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(true);
  const ref = useRef(null);

  // Cargar todas las unidades una sola vez
  useEffect(() => {
    listarUnidades()
      .then(setUnidades)
      .finally(() => setCargando(false));
  }, []);

  // Inicializar el texto del campo si ya hay un valor (modo edición)
  useEffect(() => {
    if (value && unidades.length > 0) {
      const u = unidades.find((u) => u.clues === value);
      if (u) setQuery(`${u.clues} — ${u.nombre_de_la_unidad}`);
    }
  }, [value, unidades]);

  // Cerrar el dropdown al hacer clic fuera
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setAbierto(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtradas = query.length < 2
    ? []
    : unidades
        .filter((u) =>
          u.clues.toLowerCase().includes(query.toLowerCase()) ||
          u.nombre_de_la_unidad.toLowerCase().includes(query.toLowerCase())
        )
        .slice(0, 15);

  const seleccionar = (u) => {
    onChange(u.clues);
    setQuery(`${u.clues} — ${u.nombre_de_la_unidad}`);
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
          placeholder={cargando ? "Cargando unidades..." : "Escribe CLUES o nombre de la unidad..."}
          disabled={cargando}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setAbierto(true);
            if (!e.target.value) onChange("");
          }}
          onFocus={() => query.length >= 2 && setAbierto(true)}
          className="flex-1 bg-transparent outline-none text-neutral-black placeholder:text-neutral-gray"
        />
        {query && (
          <button type="button" onClick={limpiar} className="text-neutral-gray hover:text-neutral-black">
            <X size={14} />
          </button>
        )}
      </div>

      {/* Dropdown de resultados */}
      {abierto && filtradas.length > 0 && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg max-h-60 overflow-y-auto">
          {filtradas.map((u) => (
            <li
              key={u.clues}
              onMouseDown={() => seleccionar(u)}
              className={`px-4 py-2.5 cursor-pointer hover:bg-primary/5 text-sm
                ${value === u.clues ? "bg-primary/10 text-primary font-medium" : "text-neutral-black"}`}
            >
              <span className="font-mono text-xs text-neutral-gray mr-2">{u.clues}</span>
              {u.nombre_de_la_unidad}
            </li>
          ))}
        </ul>
      )}

      {/* Mensaje de ayuda */}
      {abierto && query.length >= 2 && filtradas.length === 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-gray/20 rounded-lg
          shadow-lg px-4 py-3 text-sm text-neutral-gray">
          No se encontraron unidades con ese criterio.
        </div>
      )}
      {!abierto && query.length > 0 && query.length < 2 && (
        <p className="text-xs text-neutral-gray mt-1">Escribe al menos 2 caracteres para buscar.</p>
      )}
    </div>
  );
}
