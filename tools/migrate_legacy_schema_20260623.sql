BEGIN;

DO $$
DECLARE
    recetas_count integer;
BEGIN
    IF to_regclass('public.recetas') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM public.recetas' INTO recetas_count;
        IF recetas_count > 0 THEN
            RAISE EXCEPTION 'No se puede migrar automaticamente: public.recetas contiene % filas.', recetas_count;
        END IF;
    END IF;
END $$;

ALTER TABLE IF EXISTS public.cat_medicamentos
    ADD COLUMN IF NOT EXISTS unidad varchar(100),
    ADD COLUMN IF NOT EXISTS unidad_de_medida varchar(50);

ALTER TABLE IF EXISTS public.cat_unidades
    ADD COLUMN IF NOT EXISTS id_entidad varchar(100);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'cat_unidades'
          AND column_name = 'entidad'
    ) THEN
        UPDATE public.cat_unidades
        SET id_entidad = entidad
        WHERE id_entidad IS NULL;
    END IF;
END $$;

UPDATE public.cat_unidades
SET id_entidad = 'SIN_ENTIDAD'
WHERE id_entidad IS NULL;

ALTER TABLE IF EXISTS public.cat_unidades
    ALTER COLUMN id_entidad SET NOT NULL;

DROP INDEX IF EXISTS public.ix_cat_unidades_id_entidad;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'cat_unidades'
          AND column_name = 'entidad'
    ) THEN
        ALTER TABLE public.cat_unidades DROP COLUMN entidad;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_cat_unidades_id_entidad
    ON public.cat_unidades (id_entidad);

ALTER TABLE IF EXISTS public.medicos
    ADD COLUMN IF NOT EXISTS es_activo boolean;

UPDATE public.medicos
SET es_activo = true
WHERE es_activo IS NULL;

ALTER TABLE IF EXISTS public.medicos
    ALTER COLUMN es_activo SET NOT NULL;

ALTER TABLE IF EXISTS public.pacientes
    ADD COLUMN IF NOT EXISTS fecha_nacimiento date,
    ADD COLUMN IF NOT EXISTS estatus_evolucion varchar(30) DEFAULT 'Inicia tx',
    ADD COLUMN IF NOT EXISTS id_usuario_ultimo_cambio_estatus integer,
    ADD COLUMN IF NOT EXISTS fecha_ultimo_cambio_estatus timestamptz;

UPDATE public.pacientes
SET estatus_evolucion = 'Inicia tx'
WHERE estatus_evolucion IS NULL;

ALTER TABLE IF EXISTS public.pacientes
    ALTER COLUMN estatus_evolucion SET NOT NULL;

ALTER TABLE IF EXISTS public.pacientes
    ALTER COLUMN curp_hash DROP NOT NULL,
    ALTER COLUMN curp_paciente DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'pacientes_id_usuario_ultimo_cambio_estatus_fkey'
    ) THEN
        ALTER TABLE public.pacientes
            ADD CONSTRAINT pacientes_id_usuario_ultimo_cambio_estatus_fkey
            FOREIGN KEY (id_usuario_ultimo_cambio_estatus)
            REFERENCES public.usuarios(id_usuario)
            ON DELETE SET NULL;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pacientes'
          AND column_name = 'peso'
    ) THEN
        ALTER TABLE public.pacientes DROP COLUMN peso;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pacientes'
          AND column_name = 'talla'
    ) THEN
        ALTER TABLE public.pacientes DROP COLUMN talla;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.cat_diagnosticos (
    id_diagnostico serial PRIMARY KEY,
    nombre varchar(500) NOT NULL UNIQUE,
    codigo_cie10 varchar(20),
    es_activo boolean NOT NULL
);

CREATE TABLE IF NOT EXISTS public.unidad_medicamentos (
    clues varchar(20) NOT NULL REFERENCES public.cat_unidades(clues) ON DELETE CASCADE,
    clave_cnis varchar(50) NOT NULL REFERENCES public.cat_medicamentos(clave_cnis) ON DELETE CASCADE,
    PRIMARY KEY (clues, clave_cnis)
);

CREATE TABLE IF NOT EXISTS public.registros (
    id_registro serial PRIMARY KEY,
    id_medico integer NOT NULL REFERENCES public.medicos(id_medico) ON DELETE RESTRICT,
    id_paciente integer NOT NULL REFERENCES public.pacientes(id_paciente) ON DELETE CASCADE,
    clave_cnis varchar(50) NOT NULL REFERENCES public.cat_medicamentos(clave_cnis) ON DELETE RESTRICT,
    clues varchar(20) NOT NULL REFERENCES public.cat_unidades(clues) ON DELETE RESTRICT,
    fecha_inicio_tratamiento date,
    fecha_primera_administracion date,
    fecha_fin_tratamiento date,
    dosis_administrada varchar(100),
    peso numeric(5, 2),
    talla numeric(5, 2),
    estatus_diagnostico varchar(50),
    confirmado_por varchar(100),
    prescripcion text,
    dosis double precision,
    cantidad double precision,
    frecuencia integer,
    unidad_tiempo varchar(50),
    duracion integer,
    total_medicamento double precision,
    id_diagnostico integer REFERENCES public.cat_diagnosticos(id_diagnostico) ON DELETE RESTRICT,
    id_registro_origen integer REFERENCES public.registros(id_registro) ON DELETE SET NULL,
    fecha_registro_sistema timestamptz NOT NULL DEFAULT now(),
    id_usuario_registro integer REFERENCES public.usuarios(id_usuario) ON DELETE SET NULL,
    es_activo boolean NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_registros_id_medico ON public.registros (id_medico);
CREATE INDEX IF NOT EXISTS ix_registros_id_paciente ON public.registros (id_paciente);
CREATE INDEX IF NOT EXISTS ix_registros_clave_cnis ON public.registros (clave_cnis);
CREATE INDEX IF NOT EXISTS ix_registros_clues ON public.registros (clues);
CREATE INDEX IF NOT EXISTS ix_registros_id_diagnostico ON public.registros (id_diagnostico);
CREATE INDEX IF NOT EXISTS idx_registros_paciente_activo ON public.registros (id_paciente, es_activo);
CREATE INDEX IF NOT EXISTS idx_registros_clues_activo_fecha ON public.registros (clues, es_activo, fecha_primera_administracion);
CREATE INDEX IF NOT EXISTS idx_registros_activo_fin_tratamiento ON public.registros (es_activo, fecha_fin_tratamiento);

CREATE TABLE IF NOT EXISTS public.expedientes_paciente (
    id_paciente integer NOT NULL REFERENCES public.pacientes(id_paciente) ON DELETE CASCADE,
    clues varchar(20) NOT NULL REFERENCES public.cat_unidades(clues) ON DELETE RESTRICT,
    numero_expediente varchar(100) NOT NULL,
    PRIMARY KEY (id_paciente, clues)
);

CREATE TABLE IF NOT EXISTS public.reacciones_adversas (
    id_reaccion serial PRIMARY KEY,
    id_paciente integer NOT NULL REFERENCES public.pacientes(id_paciente) ON DELETE CASCADE,
    clave_cnis varchar(50) NOT NULL REFERENCES public.cat_medicamentos(clave_cnis) ON DELETE RESTRICT,
    comentario text NOT NULL,
    id_usuario_registro integer REFERENCES public.usuarios(id_usuario) ON DELETE SET NULL,
    fecha_registro timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_reacciones_adversas_id_paciente
    ON public.reacciones_adversas (id_paciente);

CREATE TABLE IF NOT EXISTS public.notificaciones_transferencia (
    id serial PRIMARY KEY,
    id_paciente integer NOT NULL REFERENCES public.pacientes(id_paciente) ON DELETE CASCADE,
    clues_unidad_origen varchar(20) NOT NULL REFERENCES public.cat_unidades(clues) ON DELETE RESTRICT,
    clues_unidad_destino varchar(20) NOT NULL REFERENCES public.cat_unidades(clues) ON DELETE RESTRICT,
    id_usuario_traslado integer REFERENCES public.usuarios(id_usuario) ON DELETE SET NULL,
    fecha_traslado timestamptz NOT NULL DEFAULT now(),
    leida boolean NOT NULL,
    id_usuario_leida integer REFERENCES public.usuarios(id_usuario) ON DELETE SET NULL,
    fecha_leida timestamptz
);

CREATE INDEX IF NOT EXISTS ix_notificaciones_transferencia_id_paciente
    ON public.notificaciones_transferencia (id_paciente);
CREATE INDEX IF NOT EXISTS ix_notificaciones_transferencia_clues_unidad_origen
    ON public.notificaciones_transferencia (clues_unidad_origen);

CREATE INDEX IF NOT EXISTS idx_pacientes_clues_activo
    ON public.pacientes (clues_unidad_adscripcion, es_activo);

DROP TABLE IF EXISTS public.recetas CASCADE;

CREATE TABLE IF NOT EXISTS public.alembic_version (
    version_num varchar(32) NOT NULL PRIMARY KEY
);

DELETE FROM public.alembic_version;
INSERT INTO public.alembic_version (version_num) VALUES ('20260619_0001');

COMMIT;