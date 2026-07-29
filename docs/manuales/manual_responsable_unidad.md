# Manual de Usuario
## Rol: Responsable de Unidad
### Sistema: Censo de Pacientes — Medicamentos de Alto Costo
### Institución: IMSS Bienestar

---

> **Versión:** 1.0  
> **Fecha:** Julio 2026  
> **Dirigido a:** Personal responsable de la gestión de pacientes en una unidad médica

---

## Índice

1. [Introducción](#1-introducción)
2. [Primer acceso al sistema](#2-primer-acceso-al-sistema)
3. [Módulo: Pacientes Activos](#3-módulo-pacientes-activos)
   - 3.1 [Buscar un paciente](#31-buscar-un-paciente)
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
7. [Preguntas frecuentes](#7-preguntas-frecuentes)
8. [Glosario de términos](#8-glosario-de-términos)

---

## 1. Introducción

Como **Responsable de Unidad**, usted tiene acceso completo a la gestión de pacientes y prescripciones dentro de **su propia unidad médica**. Es el rol operativo principal del sistema.

### Lo que SÍ puede hacer:

- Registrar pacientes nuevos y agregarles prescripciones de medicamentos de alto costo.
- Consultar, editar y dar de baja a los pacientes de su unidad.
- Crear, editar y anular prescripciones de medicamentos.
- Registrar y editar médicos adscritos a su unidad.
- Recibir y atender notificaciones de revalidación de tratamientos y traslados de pacientes.
- Trasladar pacientes hacia su propia unidad cuando llegan de otra.

### Lo que NO puede hacer:

- Ver pacientes de otras unidades médicas.
- Crear o gestionar cuentas de usuario del sistema.
- Consultar reportes globales o de otras unidades.
- Acceder a catálogos de otras unidades.

---

## 2. Primer acceso al sistema

Si es la primera vez que ingresa al sistema, siga los siguientes pasos:

[IMAGEN: Pantalla de inicio de sesión con enlace "¿Primera vez? Solicita tu acceso"]

1. Abra el sistema en su navegador web (solicite la dirección a su administrador).
2. En la pantalla de inicio de sesión, haga clic en **"¿Primera vez? Solicita tu acceso"**.
3. Escriba su **correo institucional** en el campo que aparece y presione **"Solicitar acceso"**.
4. Revise su bandeja de entrada. Recibirá un correo con el asunto **"Acceso al Censo de Pacientes"** que contiene su **contraseña temporal**.

> ⚠️ **Nota:** Si no recibe el correo en los siguientes minutos, revise su carpeta de spam. Si el correo no llega, es posible que su dirección no esté registrada en el sistema. Comuníquese con su administrador.

5. Regrese a la pantalla de inicio de sesión, escriba su correo y la contraseña temporal, y presione **"Ingresar"**.
6. El sistema le pedirá que complete su registro. Escriba su **nombre completo** y una **contraseña nueva** (mínimo 8 caracteres). Confirme la contraseña y presione **"Guardar nueva contraseña"**.

[IMAGEN: Pantalla de cambio de contraseña con campos nombre, contraseña nueva y confirmar contraseña]

7. A partir de este momento, utilice su correo y la contraseña nueva para ingresar.

---

## 3. Módulo: Pacientes Activos

En este módulo encontrará la lista de todos los pacientes registrados en su unidad.

[IMAGEN: Vista general del módulo Pacientes Activos con tabla de pacientes y barra de búsqueda]

### 3.1 Buscar un paciente

1. En el menú lateral, haga clic en **"Pacientes activos"**.
2. Utilice la barra de búsqueda en la parte superior para buscar por:
   - **Nombre** del paciente
   - **CURP**
   - **Medicamento** que recibe
3. Los resultados se actualizarán automáticamente conforme escribe.

### 3.2 Ver el detalle de un paciente

1. Localice al paciente en la lista (use la búsqueda si es necesario).
2. Haga clic en el botón **"Ver detalle"** en la fila del paciente.

[IMAGEN: Vista de detalle del paciente con información personal y tabla de historial de prescripciones]

En esta pantalla encontrará:
- **Datos personales:** nombre completo, CURP, fecha de nacimiento, unidad de adscripción.
- **Historial de prescripciones:** lista de todos los medicamentos prescritos, con columnas de medicamento, días de adherencia, fechas de inicio y fin, y estado activo/inactivo.

### 3.3 Editar datos de un paciente

1. Desde la lista de pacientes, haga clic en **"Ver detalle"** y luego en el botón **"Editar"**, o bien haga clic directamente en el ícono de edición de la fila.
2. Modifique los campos que necesite:
   - **Nombre completo**
   - **Fecha de nacimiento**
   - **Unidad médica de adscripción** (si requiere trasladar al paciente)
3. Presione **"Guardar cambios"**.

> ⚠️ **Nota:** Cambiar la unidad médica de adscripción desde este formulario generará automáticamente una notificación de traslado en ambas unidades (la de origen y la de destino).

### 3.4 Dar de baja a un paciente

La baja de un paciente se utiliza cuando éste ya no requiere seguimiento activo (por ejemplo: defunción, cambio definitivo a otra institución, suspensión de tratamiento).

1. Localice al paciente en la lista.
2. Haga clic en el ícono de baja (papelera o similar) en la fila del paciente.
3. El sistema le pedirá que indique el **motivo de baja**. Escríbalo en el campo de texto.
4. Confirme la acción.

> ⚠️ **Nota:** Un paciente dado de baja desaparece de la lista de activos y deja de generar notificaciones. Esta acción puede revertirse si el paciente vuelve a requerir tratamiento, simplemente registrándole una nueva prescripción.

### 3.5 Trasladar a un paciente a otra unidad

El traslado registra que un paciente cambiará su atención a una unidad diferente.

1. Localice al paciente y haga clic en **"Editar"**.
2. En el campo **"Unidad médica de adscripción"**, seleccione la nueva unidad de destino.
3. Presione **"Guardar cambios"**.
4. El sistema generará automáticamente una **notificación de traslado** visible para ambas unidades.

> ⚠️ **Nota:** Solo puede trasladar pacientes hacia o desde su propia unidad. No puede reasignar un paciente entre dos unidades distintas a la suya.

---

## 4. Módulo: Registrar Paciente

Este módulo permite registrar un paciente nuevo junto con su primera prescripción, o agregar una nueva prescripción a un paciente que ya existe en el sistema.

[IMAGEN: Formulario de registro combinado con secciones: búsqueda de paciente, datos generales y prescripción]

### 4.1 Registrar un paciente nuevo con prescripción

1. En el menú lateral, haga clic en **"Registrar paciente"**.
2. En el campo **CURP**, escriba la CURP del paciente y presione **"Buscar"**.
   - Si el sistema no encuentra al paciente, aparecerá el formulario completo para ingresar sus datos.
3. Complete la sección **"Datos del paciente"**:
   - **Nombre completo** (obligatorio): apellido paterno, materno y nombre(s).
   - **Fecha de nacimiento** (opcional).
   - **Unidad médica de adscripción** (obligatorio): seleccione la unidad. Como Responsable de Unidad, solo podrá seleccionar la suya.
4. Complete la sección **"Datos de la prescripción"**:
   - **Médico** (obligatorio): seleccione el médico que prescribe de la lista.
   - **Medicamento** (obligatorio): seleccione la clave CNIS del medicamento.
   - **Diagnóstico** (obligatorio): seleccione el diagnóstico del catálogo.
   - **Fecha de inicio de tratamiento** (obligatorio).
   - **Fecha de fin de tratamiento** (obligatorio): esta fecha determina cuándo el sistema generará la alerta de revalidación.
   - **Fecha de primera administración** (obligatorio): debe ser igual o posterior a la fecha de inicio de tratamiento.
   - **Número de expediente** (opcional).
5. Complete la sección **"Posología"**:
   - **Dosis, frecuencia, duración y unidad de tiempo**: el sistema generará automáticamente el texto de la prescripción.
   - **Peso y talla** del paciente.
6. Revise la vista previa de la prescripción que aparece en pantalla.
7. Presione **"Registrar"**.

> ⚠️ **Nota:** No es posible registrar dos prescripciones activas del mismo medicamento para el mismo paciente. Si necesita actualizar la prescripción, primero anule la anterior.

### 4.2 Agregar una prescripción a un paciente existente

1. En **"Registrar paciente"**, escriba la CURP del paciente en el campo de búsqueda y presione **"Buscar"**.
2. El sistema mostrará los datos del paciente ya registrado. Verifique que sea el paciente correcto.
3. Complete únicamente la sección de **prescripción** (los datos del paciente ya estarán llenos).
4. Presione **"Registrar"**.

---

## 5. Módulo: Notificaciones

Este módulo centraliza dos tipos de alertas: **revalidación de prescripciones** y **traslados de pacientes**.

[IMAGEN: Módulo de Notificaciones con dos pestañas: Prescripciones y Traslados]

### 5.1 Revalidar una prescripción

Las prescripciones aparecen en la pestaña **"Prescripciones"** cuando su fecha de fin de tratamiento está próxima a vencer o ya venció. La revalidación extiende el tratamiento del paciente.

1. En el menú lateral, haga clic en **"Notificaciones"**.
2. Seleccione la pestaña **"Prescripciones"**.
3. Localice la prescripción que desea revalidar.
4. Haga clic en el botón **"Revalidar"** (ícono de palomita o check).
5. El sistema calculará automáticamente la nueva fecha de fin de tratamiento con base en la duración original de la prescripción.
6. Confirme la acción.

### 5.2 Anular una prescripción

La anulación marca una prescripción como inactiva sin eliminar el historial.

1. En la pestaña **"Prescripciones"** de Notificaciones, localice la prescripción.
2. Haga clic en el botón **"Anular"** (ícono de papelera).
3. Confirme la acción en el cuadro de diálogo que aparece.

> ⚠️ **Nota:** Una prescripción anulada no puede reactivarse. Si el paciente necesita continuar con el medicamento, deberá registrar una nueva prescripción.

### 5.3 Notificaciones de traslado

La pestaña **"Traslados"** muestra los movimientos de pacientes hacia o desde su unidad.

1. Seleccione la pestaña **"Traslados"**.
2. Revise la lista de traslados pendientes. Cada notificación indica:
   - Nombre del paciente
   - Unidad de origen
   - Unidad de destino
   - Fecha del traslado
   - Quién realizó el traslado
3. Una vez revisada, marque la notificación como leída haciendo clic en **"Marcar como leída"**.

---

## 6. Módulo: Médicos

Aquí podrá consultar y gestionar el catálogo de médicos registrados en su unidad.

[IMAGEN: Lista de médicos con columnas nombre, cédula, puesto y botones de acción]

### 6.1 Registrar un médico nuevo

1. En el menú lateral, haga clic en **"Médicos"**.
2. Haga clic en el botón **"Nuevo médico"**.
3. Complete el formulario:
   - **Nombre completo** (obligatorio).
   - **Cédula profesional** (obligatorio): número oficial de la SEP. El sistema no permitirá duplicados.
   - **CURP** (opcional).
   - **Correo electrónico** (opcional).
   - **Puesto** (opcional): seleccione del catálogo de puestos.
4. Presione **"Guardar"**.

### 6.2 Editar datos de un médico

1. Localice al médico en la lista.
2. Haga clic en el ícono de edición de su fila.
3. Modifique los campos necesarios y presione **"Guardar cambios"**.

---

## 7. Preguntas frecuentes

**¿Qué hago si el paciente ya existe en el sistema pero en otra unidad?**
Búsquelo por CURP en el módulo "Registrar paciente". El sistema lo encontrará y podrá agregarle una nueva prescripción en su unidad. Si requiere cambiar su unidad de adscripción, edítelo desde "Pacientes activos".

**¿Puedo ver pacientes de otras unidades?**
No. Como Responsable de Unidad, solo tiene acceso a los pacientes registrados en su unidad médica asignada.

**¿Qué significa que una prescripción esté "por vencer"?**
El sistema genera una alerta cuando faltan 7 días o menos para que venza el plazo de continuidad de la prescripción (30 días después de la fecha de fin de tratamiento). Esto aparece en el módulo de Notificaciones.

**¿Qué pasa si anulo una prescripción por error?**
Una vez anulada, la prescripción no puede reactivarse. Deberá registrar una nueva prescripción para el mismo medicamento. Comuníquese con su Super Administrador si necesita asesoría.

**¿Puedo registrar dos medicamentos distintos para el mismo paciente?**
Sí. Un paciente puede tener múltiples prescripciones activas de medicamentos diferentes. Lo que no está permitido es tener dos prescripciones activas del mismo medicamento.

**¿Cómo traslado un paciente que llega a mi unidad desde otra?**
El traslado lo realiza quien edita la unidad de adscripción del paciente. Usted recibirá la notificación en la pestaña "Traslados" cuando un paciente sea asignado a su unidad.

**¿Qué hago si olvidé mi contraseña?**
En la pantalla de inicio de sesión, haga clic en "¿Primera vez? Solicita tu acceso", ingrese su correo institucional y el sistema le enviará un nuevo acceso temporal.

---

## 8. Glosario de términos

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
