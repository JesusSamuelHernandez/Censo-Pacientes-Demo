El Blueprint Final: App Web "Medicamentos de Alto Costo"
1. Definición del Stack Tecnológico
•	Lenguaje: Python 3.10+
•	Framework API: FastAPI 
•	Base de Datos: PostgreSQL
•	ORM: SQLAlchemy 
•	Autenticación: OAuth2 con JWT (JSON Web Tokens).
________________________________________
2. Modelo de Datos (Esquema de Tablas)
Esquema Detallado de Base de Datos (DB Schema)
Tabla: cat_medicamentos (Catálogo Maestro)
•	clave_cnis (PK): Texto. La clave oficial (ej: "010.000..."). Es la Llave Primaria.
•	descripcion: Texto largo. Detalle del medicamento.
•	grupo: Texto.
•	tipo_clave: Texto.
•	es_activo: Booleano (True/False). Para el Soft Delete del catálogo.
Tabla: unidades_medicas
•	clues (PK): Texto. La Clave Única de Establecimientos de Salud.
•	nombre_de_la_unidad: Texto. Nombre del hospital o clínica.
•	id_entidad: Texto. El estado al que pertenece (ej: "Ciudad de México").
•	categoria_gerencial: Texto
Tabla: usuarios
•	id_usuario (PK): Entero (Autoincremental).
•	nombre_usuario: Texto. Nombre del usuario de la plataforma
•	email: Texto único. Será el nombre de usuario para el login.
•	hashed_password: Texto. La contraseña encriptada (nunca en texto plano).
•	rol_nombre: Texto. Los 3 roles que definimos: SUPER_ADMIN, ADMIN_ESTATAL, RESPONSABLE_UNIDAD.
•	clues_unidad_asignada (FK): Texto. Relaciona al usuario con su unidad clues
•	id_entidad: Texto. Relaciona al usuario con una entidad (para el Admin Estatal).
Tabla: pacientes
•	curp_paciente (PK): Texto (18 caracteres). Identificador único oficial.
•	nombre_completo: Texto.
•	diagnostico_actual: Texto largo.
•	fecha_inicio_tratamiento: Fecha. Cuándo empezó el paciente con este tipo de medicamentos.
•	clues_unidad_adscripcion (FK): Entero. Unidad donde se atiende el paciente.
•	es_activo: Booleano. Soft Delete para pacientes que se dan de baja.
•	fecha_registro: Timestamp. Fecha y hora automática de cuando se creó en el sistema.
Tabla: suministros (Asignación de tratemiento)
•	id_suministro (PK): Entero (Autoincremental).
•	curp_paciente (FK): Texto. A qué paciente se le dio.
•	clave_cnis_med (FK): Texto. Qué medicamento se le dio.
•	dosis_administrada: Texto. (Ej: "200 mg", "1 ampolleta").
•	fecha_primera_administracion: Fecha en que se comenzó a administrar el medicamento
•	fecha_registro_sistema: fecha en la que se creo el regsitro o se modifico. 
•	id_usuario_registro (FK): Entero. Quién capturó este dato (Auditoría).
•	es_activo: Booleano. Soft Delete por si capturaron un suministro por error.




________________________________________
3. Lógica de Negocio y Reportes (El "Cerebro")
Aquí es donde preparamos el terreno para tus análisis de Big Data:
•	Soft Delete: Ningún DELETE físico. Solo cambiar es_activo = False.
•	Trazabilidad: Cada vez que se registra un paciente nuevo o se edita un suministro a un paciente guardamos qué usuario lo hizo (usuario_id) y en qué momento exacto (creado_en) cuando se hizo este cambio. 
•	Campos de Reporte: Incluiremos una vista o función que calcule la "Adherencia": cuántos días han pasado desde la fecha_inicio_tratamiento 
________________________________________
4. Matriz de Seguridad (RBAC)
Usaremos el estándar CRUD (Create, Read, Update, Delete).
Entidad	Responsable Unidad	Administrador Estatal	Super Admin (Nosotros)
Pacientes	C, R, U (Solo su unidad)	R (Todo su estado)	R (Todo el país)
Suministros	C, R, U (Solo su unidad)	R (Todo su estado)	R (Todo el país)
Medicamentos	R (Lectura)	R (Lectura)	C, R, U, D (Gestión total)
Usuarios	No tiene acceso	No tiene acceso	C, R, U, D (Crea cuentas)
Unidades/Edo	R (Lectura)	R (Lectura)	C, R, U, D


Instrucción para el backend: Toda consulta de datos debe pasar por un filtro de pertenencia.
•	Si Rol == ResponsableUnidad: WHERE clues_unidad_asignada = usuario. clues_unidad_asignada
•	Si Rol == AdminEstatal: WHERE id_entidad = usuario. id_entidad
•	Si Rol == SuperAdmin: Sin filtro.
________________________________________
5. Definición de Endpoints (Rutas de la API)

5.1Módulo de Autenticación (Seguridad)
•	POST /auth/login
o	Función: Recibe credenciales, valida y entrega un Token JWT.
o	Respuesta: Token de acceso + Rol del usuario (SUPER_ADMIN, ADMIN_ESTATAL o RESPONSABLE_UNIDAD).
________________________________________
5.2. Módulo de Pacientes (Gestión Clínica)
•	GET /pacientes
o	Función: Lista de pacientes. El backend aplica el filtro automático según el rol (Su unidad, su estado o todo el país).
•	POST /pacientes
o	Función: Registro de un nuevo paciente (incluyendo Diagnóstico y Fecha de Inicio).
•	GET /pacientes/{curp_paciente}
o	Función: Detalle completo de un paciente y su historial de suministros.
•	PATCH /pacientes/{curp_paciente}
o	Función: Actualización de datos (diagnóstico, nombre, etc.).
•	DELETE /pacientes/{curp_paciente}
o	Función: Ejecuta el Soft Delete (cambia es_activo a false).
________________________________________
5.3. Módulo de Suministros (Operación)
•	GET /suministros
o	Función: Historial de todas las aplicaciones de medicamentos registradas (filtrado por rol).
•	POST /suministros
o	Función: Registrar la aplicación de una dosis a un paciente específico.
•	DELETE /suministros/{id_suministro}
o	Función: Anular un registro de suministro en caso de error de captura (Soft Delete).
________________________________________
5.4. Módulo de Inteligencia y Reportes (Big Data)
•	GET /reportes/resumen-detallado
o	Función: Entrega un JSON con datos crudos y filtros de fecha. Ideal para que el frontend genere el Excel/PDF general.
•	GET /reportes/estatal
o	Función: Entrega datos agregados (sumatorias por unidad) diseñado exclusivamente para el Admin Estatal.
________________________________________
5.5. Módulo de Catálogos (Solo Super Admin)
•	GET /catalogos/medicamentos
o	Función: Consultar la lista oficial de medicamentos (Clave CNIS).
•	POST /catalogos/medicamentos
o	Función: Agregar nuevas claves al catálogo oficial.


