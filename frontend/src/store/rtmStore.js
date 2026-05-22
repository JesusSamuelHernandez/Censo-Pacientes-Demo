import { create } from "zustand";

const useRtmStore = create((set) => ({
  entidad: "",
  unidadSeleccionada: null,
  setEntidad: (entidad) => set({ entidad }),
  setUnidadSeleccionada: (unidad) => set({ unidadSeleccionada: unidad }),
  limpiarUnidad: () => set({ unidadSeleccionada: null }),
}));

export default useRtmStore;
