import { create } from "zustand";
import { persist } from "zustand/middleware";

const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      rolNombre: null,
      idUsuario: null,
      debeCambiarPassword: false,
      email: null,
      nombreUsuario: null,
      cluesUnidadAsignada: null,
      nombreUnidad: null,
      idEntidad: null,

      login: ({
        access_token,
        rol_nombre,
        id_usuario,
        debe_cambiar_password,
        email,
        nombre_usuario,
        clues_unidad_asignada,
        nombre_unidad,
        id_entidad,
      }) => {
        localStorage.setItem("access_token", access_token);
        set({
          token: access_token,
          rolNombre: rol_nombre,
          idUsuario: id_usuario,
          debeCambiarPassword: debe_cambiar_password,
          email,
          nombreUsuario: nombre_usuario,
          cluesUnidadAsignada: clues_unidad_asignada,
          nombreUnidad: nombre_unidad,
          idEntidad: id_entidad,
        });
      },

      marcarPasswordCambiado: () => {
        set({ debeCambiarPassword: false });
      },

      logout: () => {
        localStorage.removeItem("access_token");
        set({
          token: null,
          rolNombre: null,
          idUsuario: null,
          debeCambiarPassword: false,
          email: null,
          nombreUsuario: null,
          cluesUnidadAsignada: null,
          nombreUnidad: null,
          idEntidad: null,
        });
      },

      esSuperAdmin: () => useAuthStore.getState().rolNombre === "SUPER_ADMIN",
      esAdminEstatal: () => useAuthStore.getState().rolNombre === "ADMIN_ESTATAL",
      esResponsableUnidad: () => useAuthStore.getState().rolNombre === "RESPONSABLE_UNIDAD",
    }),
    {
      name: "auth_store",
      partialize: (state) => ({
        token: state.token,
        rolNombre: state.rolNombre,
        idUsuario: state.idUsuario,
        debeCambiarPassword: state.debeCambiarPassword,
        email: state.email,
        nombreUsuario: state.nombreUsuario,
        cluesUnidadAsignada: state.cluesUnidadAsignada,
        nombreUnidad: state.nombreUnidad,
        idEntidad: state.idEntidad,
      }),
    }
  )
);

export default useAuthStore;
