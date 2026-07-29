# Manual de Usuario
## Rol: Super Administrador
### Sistema: Censo de Pacientes — Medicamentos de Alto Costo
### Institución: IMSS Bienestar

---

> **Versión:** 1.0  
> **Fecha:** Julio 2026  
> **Dirigido a:** Personal técnico o directivo con acceso total al sistema a nivel nacional

---

## Índice

1. [Introducción](#1-introducción)
2. [Primer acceso al sistema](#2-primer-acceso-al-sistema)
3. [Módulo: Pacientes Activos](#3-módulo-pacientes-activos)
   - 3.1 [Consultar y buscar pacientes](#31-consultar-y-buscar-pacientes)
   - 3.2 [Ver el detalle de un paciente](#32-ver-el-detalle-de-un-paciente)
   - 3.3 [Editar datos de un paciente](#33-editar-datos-de-un-paciente)
   - 3.4 [Dar de baja a un paciente](#34-dar-de-baja-a-un-paciente)
   - 3.5 [Trasladar a un paciente a otra unidad](#35-trasladar-a-un-paciente-a-otra-unidad)
4. [Módulo: Registrar Paciente](#4-módulo-registrar-paciente)
   - 4.1 [Registrar un paciente nuevo con prescripción](#41-registrar-un-paciente-nuevo-con-prescripción)
   - 4.2 [Agregar una prescripción a un paciente existente](#42-agregar-una-prescripción-a-un-paciente-existente)
5. [Módulo: Notificaciones](#5-módulo-notificaciones)
   - 5.1 [Revalidar una prescripción](#51-revalidar-una-prescripción)
   - 5.2 [Anular una prescripción](#52-anular-una-prescripción)
   - 5.3 [Notificaciones de traslado](#53-notificaciones-de-traslado)
6. [Módulo: Médicos](#6-módulo-médicos)
   - 6.1 [Registrar un médico nuevo](#61-registrar-un-médico-nuevo)
   - 6.2 [Editar datos de un médico](#62-editar-datos-de-un-médico)
7. [Módulo: Usuarios](#7-módulo-usuarios)
   - 7.1 [Crear un usuario nuevo](#71-crear-un-usuario-nuevo)
   - 7.2 [Editar un usuario existente](#72-editar-un-usuario-existente)
   - 7.3 [Eliminar un usuario](#73-eliminar-un-usuario)
8. [Módulo: Reportes](#8-módulo-reportes)
9. [Módulo: Catálogos](#9-módulo-catálogos)
10. [Preguntas frecuentes](#10-preguntas-frecuentes)
11. [Glosario de términos](#11-glosario-de-términos)

---

## 1. Introducción

El **Super Administrador** tiene acceso completo y sin restricciones geográficas a todos los módulos y datos del sistema. Es el único rol que puede crear y gestionar cuentas de usuario, y tiene visibilidad total de pacientes, prescripciones y estadísticas de todas las entidades y unidades del país.

### Lo que SÍ puede hacer:

- Ver, registrar, editar y dar de baja pacientes de cualquier unidad y estado.
- Crear, editar y anular prescripciones de cualquier paciente.
- Gestionar el catálogo de médicos de cualquier unidad.
- Crear, editar y eliminar cuentas de usuario de cualquier rol.
- Consultar todos los reportes y notificaciones a nivel nacional.
- Configurar qué medicamentos están disponibles en cada unidad médica.
- Trasladar pacientes entre cualquier unidad del país.

### Lo que implica este rol:

> ⚠️ **Nota:** El Super Administrador tiene capacidad de modificar o eliminar cualquier dato del sistema. Se recomienda utilizar este acceso con responsabilidad y solo para las operaciones que correspondan. Las acciones de baja y eliminación son irreversibles o difíciles de revertir.

---

## 2. Primer acceso al sistema

Si es la primera vez que ingresa al sistema, siga los siguientes pasos:

[IMAGEN: Pantalla de inicio de sesión con enlace "¿Primera vez? Solicita tu acceso"]

1. Abra el sistema en su navegador web.
2. En la pantalla de inicio de sesión, haga clic en **"¿Primera vez? Solicita tu acceso"**.
3. Escriba su **correo institucional** y presione **"Solicitar acceso"**.
4. Revise su bandeja de entrada. Recibirá un correo con su **contraseña temporal**.

> ⚠️ **Nota:** Para cuentas de Super Administrador, el correo debe estar registrado previamente por el equipo técnico central. Si no recibe el correo, contacte al equipo de soporte técnico del sistema.

5. Regrese a la pantalla de inicio de sesión, ingrese su correo y la contraseña temporal, y presione **"Ingresar"**.
6. El sistema le pedirá que complete su registro: escriba su **nombre completo** y una **contraseña nueva** (mínimo 8 caracteres). Confirme y presione **"Guardar nueva contraseña"**.

[IMAGEN: Pantalla de cambio de contraseña con campos nombre, contraseña nueva y confirmar contraseña]

7. A partir de este momento, use su correo y contraseña nueva para ingresar.

---

## 3. Módulo: Pacientes Activos

Este módulo muestra todos los pacientes activos registrados en el sistema, sin importar la unidad o estado al que pertenezcan.

[IMAGEN: Vista general del módulo Pacientes Activos con tabla y filtros disponibles]

### 3.1 Consultar y buscar pacientes

1. En el menú lateral, haga clic en **"Pacientes activos"**.
2. Use la barra de búsqueda para encontrar pacientes por nombre, CURP o medicamento.
3. Use los filtros para acotar resultados por unidad médica, estado o medicamento específico.

### 3.2 Ver el detalle de un paciente

1. Localice al paciente en la lista.
2. Haga clic en **"Ver detalle"**.

[IMAGEN: Vista de detalle del paciente con historial de prescripciones y adherencia]

En esta pantalla encontrará:
- **Datos personales:** nombre, CURP, fecha de nacimiento, unidad de adscripción actual.
- **Historial de prescripciones:** todos los medicamentos prescritos con columna de adherencia (días activos), fechas de inicio/fin y estado.

### 3.3 Editar datos de un paciente

1. Desde la lista de pacientes, haga clic en el ícono de edición, o en "Ver detalle" y luego en "Editar".
2. Modifique los campos necesarios: nombre, fecha de nacimiento o unidad de adscripción.
3. Presione **"Guardar cambios"**.

> ⚠️ **Nota:** Cambiar la unidad de adscripción genera automáticamente una notificación de traslado para las unidades involucradas.

### 3.4 Dar de baja a un paciente

1. Localice al paciente y haga clic en el ícono de baja.
2. Ingrese el **motivo de baja** en el campo de texto.
3. Confirme la acción.

> ⚠️ **Nota:** Los pacientes dados de baja dejan de aparecer en la lista activa y sus prescripciones dejan de generar notificaciones. El historial se conserva y puede consultarse.

### 3.5 Trasladar a un paciente a otra unidad

1. Desde "Editar" en la ficha del paciente, cambie el campo **"Unidad médica de adscripción"** a la unidad de destino.
2. Presione **"Guardar cambios"**.
3. El sistema generará la notificación de traslado para ambas unidades involucradas.

---

## 4. Módulo: Registrar Paciente

### 4.1 Registrar un paciente nuevo con prescripción

1. En el menú lateral, haga clic en **"Registrar paciente"**.
2. Escriba la CURP del paciente y presione **"Buscar"**.
   - Si no existe, aparecerá el formulario completo.
3. Complete la sección **"Datos del paciente"**:
   - **Nombre completo** (obligatorio).
   - **Fecha de nacimiento** (opcional).
   - **Unidad médica de adscripción** (obligatorio): como Super Admin puede seleccionar cualquier unidad del país.
4. Complete la sección **"Datos de la prescripción"**:
   - **Médico** (obligatorio): médico que prescribe.
   - **Unidad de la prescripción** (obligatorio): puede diferir de la adscripción si aplica.
   - **Medicamento** (obligatorio): clave CNIS.
   - **Diagnóstico** (obligatorio).
   - **Fecha de inicio** y **fecha de fin de tratamiento** (obligatorias).
   - **Fecha de primera administración** (obligatoria, igual o posterior a la fecha de inicio).
   - **Número de expediente** (opcional).
5. Complete la sección **"Posología"**: dosis, frecuencia, duración, unidad de tiempo, peso y talla.
6. Revise la vista previa de la prescripción.
7. Presione **"Registrar"**.

> ⚠️ **Nota:** No es posible registrar dos prescripciones activas del mismo medicamento para un mismo paciente. Anule la prescripción anterior antes de crear una nueva.

### 4.2 Agregar una prescripción a un paciente existente

1. En **"Registrar paciente"**, busque al paciente por CURP.
2. El sistema mostrará sus datos. Complete solo la sección de prescripción.
3. Presione **"Registrar"**.

---

## 5. Módulo: Notificaciones

Como Super Admin, tiene acceso a todas las notificaciones del sistema, sin importar la unidad o estado.

[IMAGEN: Módulo de Notificaciones con pestañas Prescripciones y Traslados]

### 5.1 Revalidar una prescripción

1. Haga clic en **"Notificaciones"** en el menú lateral.
2. Seleccione la pestaña **"Prescripciones"**.
3. Localice la prescripción por vencer o vencida.
4. Haga clic en el botón **"Revalidar"**.
5. El sistema extenderá automáticamente la fecha de fin con base en la duración original. Confirme.

### 5.2 Anular una prescripción

1. En la pestaña **"Prescripciones"**, localice la prescripción.
2. Haga clic en el botón **"Anular"** (ícono de papelera).
3. Confirme en el cuadro de diálogo.

> ⚠️ **Nota:** La anulación es irreversible. Si el paciente necesita continuar el tratamiento, deberá registrarse una nueva prescripción.

### 5.3 Notificaciones de traslado

1. Seleccione la pestaña **"Traslados"**.
2. Visualice todos los traslados pendientes en el sistema, de cualquier unidad.
3. Marque como leídas las notificaciones revisadas haciendo clic en **"Marcar como leída"**.

---

## 6. Módulo: Médicos

### 6.1 Registrar un médico nuevo

1. En el menú lateral, haga clic en **"Médicos"**.
2. Haga clic en **"Nuevo médico"**.
3. Complete el formulario:
   - **Nombre completo** (obligatorio).
   - **Cédula profesional** (obligatorio): el sistema valida que no existan duplicados.
   - **Unidad de adscripción** (obligatorio): como Super Admin puede asignar cualquier unidad del país.
   - **CURP** (opcional).
   - **Correo electrónico** (opcional).
   - **Puesto** (opcional).
4. Presione **"Guardar"**.

### 6.2 Editar datos de un médico

1. Localice al médico en la lista.
2. Haga clic en el ícono de edición de su fila.
3. Modifique los campos necesarios y presione **"Guardar cambios"**.

---

## 7. Módulo: Usuarios

Este módulo es exclusivo del Super Administrador. Permite gestionar todas las cuentas de acceso al sistema.

[IMAGEN: Lista de usuarios con columnas nombre, correo, rol, unidad/entidad y botones de acción]

### 7.1 Crear un usuario nuevo

1. En el menú lateral, haga clic en **"Usuarios"**.
2. Haga clic en el botón **"Nuevo usuario"**.
3. Complete el formulario:
   - **Correo electrónico** (obligatorio): debe ser el correo institucional del usuario. No puede repetirse en el sistema.
   - **Rol** (obligatorio): seleccione entre:
     - *Responsable de Unidad*: deberá asignar también una unidad médica (CLUES).
     - *Administrador Estatal*: deberá asignar la entidad federativa correspondiente.
     - *Super Administrador*: sin asignación de unidad ni entidad.
   - **Unidad médica** (solo para Responsable de Unidad): seleccione la unidad asignada.
   - **Entidad federativa** (solo para Administrador Estatal): seleccione el estado.
4. Presione **"Crear usuario"**.

[IMAGEN: Modal de nuevo usuario con campos correo, rol, unidad o entidad]

5. El sistema generará automáticamente una **contraseña temporal** y la mostrará en pantalla. Además, enviará el acceso al correo del nuevo usuario.

> ⚠️ **Nota:** Anote o comparta la contraseña temporal de inmediato. La pantalla que la muestra no estará disponible después de cerrarla. El usuario deberá cambiarla en su primer ingreso.

### 7.2 Editar un usuario existente

1. Localice al usuario en la lista.
2. Haga clic en el ícono de edición de su fila.
3. Podrá modificar:
   - **Nombre de usuario**
   - **Rol**
   - **Unidad médica** o **entidad federativa** asignada
4. Presione **"Guardar cambios"**.

> ⚠️ **Nota:** Cambiar el rol de un usuario modifica inmediatamente su nivel de acceso al sistema. El usuario verá los cambios en su próxima sesión.

### 7.3 Eliminar un usuario

1. Localice al usuario en la lista.
2. Haga clic en el ícono de eliminar (papelera).
3. Confirme la acción en el cuadro de diálogo que aparece.

> ⚠️ **Nota:** Eliminar un usuario es una acción permanente. El usuario perderá acceso al sistema de inmediato. Los registros que haya creado se conservan en la base de datos.

---

## 8. Módulo: Reportes

Como Super Admin, tiene acceso a reportes de cualquier entidad, unidad o período.

[IMAGEN: Módulo de Reportes con filtros por estado, unidad, período y tipo de reporte]

1. En el menú lateral, haga clic en **"Reportes"**.
2. Seleccione los filtros deseados:
   - **Entidad federativa** o **unidad médica**
   - **Período de fechas**
   - **Medicamento** específico (opcional)
3. Haga clic en **"Generar reporte"** o **"Exportar"** para descargar el archivo.

---

## 9. Módulo: Catálogos

Este módulo permite configurar qué medicamentos están disponibles para prescripción en cada unidad médica.

[IMAGEN: Módulo de Catálogos con lista de medicamentos por unidad]

1. En el menú lateral, haga clic en **"Catálogos"**.
2. Podrá consultar:
   - **Medicamentos:** catálogo nacional de medicamentos de alto costo con clave CNIS.
   - **Diagnósticos:** catálogo de diagnósticos disponibles para prescripción.
   - **Unidades:** catálogo de unidades médicas registradas.
3. Para agregar un medicamento a una unidad específica, localice la unidad en el catálogo y asigne los medicamentos correspondientes.

> ⚠️ **Nota:** Solo los medicamentos asignados a una unidad estarán disponibles al registrar prescripciones desde esa unidad. Si un Responsable de Unidad no ve un medicamento en el formulario, es posible que no esté asignado a su unidad.

---

## 10. Preguntas frecuentes

**¿Puedo ver pacientes de cualquier estado del país?**
Sí. Como Super Administrador, tiene acceso a todos los pacientes registrados en el sistema sin restricción geográfica.

**¿Qué hago si un Responsable de Unidad no puede ver cierto medicamento en el formulario?**
Verifique en el módulo de Catálogos que el medicamento esté asignado a la unidad del responsable. Si no está, agréguelo desde la configuración de esa unidad.

**¿Puedo recuperar un usuario eliminado?**
No. La eliminación de usuarios es permanente. Si necesita restablecer el acceso, cree una nueva cuenta con el mismo correo (siempre que no esté duplicado en el sistema).

**¿Qué pasa si creo un usuario con un correo que ya existe?**
El sistema rechazará la operación e indicará que ya existe un usuario con ese correo. Verifique la lista de usuarios antes de crear una cuenta nueva.

**¿Cómo sé qué unidades existen para asignar a un Responsable de Unidad?**
Al seleccionar la unidad en el formulario de nuevo usuario, aparecerá un buscador de unidades. Puede buscar por nombre o por CLUES.

**¿Puedo cambiar el rol de un usuario de Responsable de Unidad a Administrador Estatal?**
Sí. Edite el usuario, cambie el rol y asigne la entidad federativa correspondiente. El usuario verá los cambios en su próxima sesión.

**¿Por qué el sistema no me permite crear una prescripción para un medicamento específico en cierta unidad?**
El medicamento puede no estar asignado a esa unidad en el catálogo. Revise y agregue el medicamento en el módulo de Catálogos.

**¿Qué hago si olvidé mi contraseña?**
En la pantalla de inicio de sesión, haga clic en "¿Primera vez? Solicita tu acceso", ingrese su correo institucional y el sistema le enviará un nuevo acceso temporal.

---

## 11. Glosario de términos

| Término | Definición |
|---|---|
| **CURP** | Clave Única de Registro de Población. Identificador oficial de 18 caracteres asignado a cada ciudadano mexicano. |
| **CLUES** | Clave Única de Establecimientos de Salud. Código que identifica de forma única a cada unidad médica en México. |
| **Prescripción** | Registro de un medicamento de alto costo asignado a un paciente, que incluye dosis, duración y médico responsable. |
| **Revalidación** | Proceso de extender o confirmar la continuidad de un tratamiento activo antes de que venza su fecha de fin. |
| **Medicamento de alto costo** | Medicamento con un costo elevado, incluido en el catálogo institucional bajo la clave CNIS. |
| **Clave CNIS** | Código del Cuadro Nacional de Insumos para la Salud que identifica a cada medicamento. |
| **Adherencia** | Número de días que un paciente lleva con un tratamiento activo desde la fecha de inicio. |
| **Baja de paciente** | Acción que marca a un paciente como inactivo en el sistema, suspendiendo sus alertas y seguimiento. |
| **Traslado** | Cambio de la unidad médica de adscripción de un paciente de una unidad a otra. |
| **Posología** | Indicaciones sobre la dosis, frecuencia y duración de un medicamento. |
| **Anular prescripción** | Acción que marca una prescripción como inactiva. No elimina el historial. |
| **Contraseña temporal** | Clave de acceso generada automáticamente por el sistema que el usuario debe cambiar en su primer ingreso. |
| **Catálogo** | Lista de elementos disponibles en el sistema (medicamentos, diagnósticos, unidades) que se usan al registrar prescripciones. |
| **Entidad federativa** | Estado de la República Mexicana al que pertenece una unidad médica o un usuario Administrador Estatal. |
