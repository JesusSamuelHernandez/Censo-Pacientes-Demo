# Protocolo Multi-Agentes — Claude Code

> Versión: 1.0  
> Fecha: 2026-05-26  
> Aplicable a: cualquier proyecto gestionado con Claude Code CLI/IDE

---

## 1. Filosofía

Claude Code permite lanzar **subagentes** — instancias aisladas del mismo modelo que corren dentro de la sesión activa. Cada subagente tiene su propio contexto vacío, acceso completo al sistema de archivos y herramientas del proyecto, y devuelve su resultado al agente principal sin contaminar el contexto de la conversación principal.

Este protocolo define cuándo, cómo y con qué estructura lanzar esos subagentes para maximizar la calidad del trabajo y minimizar el desgaste del contexto principal.

**Principios:**
- El agente principal **razona y decide**. Los subagentes **ejecutan y reportan**.
- Los subagentes son **desechables** — no persisten entre sesiones.
- La **memoria persistente** entre sesiones vive en los archivos `.context/`.
- Un subagente bien briefeado produce mejor resultado que uno con instrucciones vagas.

---

## 2. Sistema de memoria persistente (.context/)

Estos archivos se actualizan al final de cada sesión significativa y son lo primero que el agente principal debe leer al iniciar.

| Archivo | Contenido | Cuándo actualizar |
|---|---|---|
| `projectBrief.md` | Objetivo del proyecto, usuarios objetivo, alcance | Al inicio del proyecto o cambio de dirección |
| `productContext.md` | Reglas de negocio, flujos principales, decisiones de diseño | Cuando cambian requisitos o se añaden módulos |
| `techContext.md` | Stack, versiones, dependencias, configuración de entorno | Al agregar/cambiar tecnologías |
| `activeContext.md` | En qué se está trabajando ahora, decisiones recientes, bloqueadores | Al inicio/fin de cada sesión |
| `progress.md` | Qué está completado, qué está pendiente, hitos | Al completar módulos o pasos de un blueprint |

**Regla:** Si una sesión dura más de 30 minutos o produce cambios significativos, actualiza `activeContext.md` y `progress.md` antes de cerrar.

---

## 3. Tipos de subagente disponibles

| Tipo | Ideal para | Herramientas |
|---|---|---|
| `Explore` | Búsqueda rápida de código, localizar símbolos, mapear estructura | Glob, Grep, Read (solo lectura) |
| `Plan` | Diseñar la implementación de un cambio antes de escribir código | Lectura + análisis, produce plan de pasos |
| `general-purpose` | Documentación, análisis de logs, investigación, tareas mixtas | Todas las herramientas |
| `simplify` | Revisión de calidad del código recién escrito | Lectura + análisis de calidad |
| `claude` | Tareas que no encajan en los anteriores | Todas las herramientas |

---

## 4. Cuándo usar cada tipo de subagente

### `Explore` — Investigación focalizada
Úsalo cuando necesites responder: *"¿dónde está X?", "¿qué archivos usan Y?", "¿qué campos tiene el modelo Z?"*

```
Ejemplos:
- "Encuentra todos los endpoints que usan apply_rbac_filter"
- "Lista todos los componentes que importan useAuthStore"
- "¿Qué campos tiene el schema RegistroResponse?"
```

**Cuándo NO usarlo:** Si necesitas leer archivos completos o cruzar información de muchos archivos — usa `general-purpose`.

---

### `Plan` — Diseño antes de implementar
Úsalo antes de un cambio no trivial para producir un plan de pasos, identificar archivos afectados y considerar efectos secundarios.

```
Ejemplos:
- "Diseña cómo agregar un módulo de reportes PDF"
- "¿Qué pasos y archivos implica agregar un nuevo rol COORDINADOR?"
- "Planifica la migración de la tabla registros para agregar el campo X"
```

**Salida esperada:** Lista de pasos numerados, archivos afectados, riesgos.

---

### `general-purpose` — Documentación y análisis complejo
Úsalo para tareas que requieren leer muchos archivos grandes y producir documentos o análisis.

```
Ejemplos:
- Actualizar docs/arquitectura_backend.md leyendo el código actual
- Analizar logs de producción y resumir errores
- Generar un resumen del estado del proyecto para un nuevo colaborador
```

---

### `simplify` — Revisión de calidad
Úsalo después de implementar un cambio grande para detectar código duplicado, abstracciones innecesarias o problemas de calidad.

```
Ejemplos:
- "Revisa RegistroFormPage.jsx que acabo de modificar"
- "Verifica que los nuevos endpoints en main.py son consistentes con el resto"
```

---

## 5. Estructura de un prompt de subagente

Un subagente no ve la conversación actual — su prompt debe ser **autocontenido**. Usa siempre esta estructura:

```markdown
## Contexto del proyecto
[Stack, objetivo, convenciones importantes — 10-15 líneas máximo]

## Lo que ya se hizo / estado actual
[Qué cambios recientes son relevantes para esta tarea]

## Archivos a leer
[Lista explícita con rutas absolutas]

## Tu tarea
[Instrucción precisa de qué producir y en qué formato]

## Restricciones
[Qué NO hacer: no inventar, no refactorizar más de lo pedido, etc.]
```

**Regla de oro:** El prompt debe probar que quien lo escribe entendió el problema. Incluye rutas exactas, nombres de funciones/modelos, y el formato esperado del resultado.

---

## 6. Flujos de trabajo por tipo de tarea

### Flujo A — Nuevo módulo o feature

```
1. [Plan]       Diseña la arquitectura del cambio
2. Revisar plan con el usuario
3. [Explore]    Mapea archivos que serán afectados
4. Implementar paso a paso (el agente principal)
5. [simplify]   Revisión de calidad del código nuevo
6. Actualizar .context/activeContext.md y progress.md
```

### Flujo B — Investigación / bug

```
1. [Explore]    Localiza el código relevante
2. Diagnosticar (agente principal con el reporte del Explore)
3. Implementar fix
4. [Explore]    Verificar que no hay otros archivos afectados
```

### Flujo C — Actualización de documentación

```
1. [general-purpose]  Lee código fuente + docs actuales
                       Produce contenido actualizado
2. Agente principal revisa y escribe los archivos con Write/Edit
3. Actualizar .context/
```

### Flujo D — Inicio de sesión

```
1. Leer .context/activeContext.md y progress.md
2. [Explore] (opcional) Verificar estado actual del código si hay dudas
3. Continuar desde donde se dejó
```

---

## 7. Paralelismo

Cuando dos tareas son **independientes**, se pueden lanzar múltiples subagentes en el mismo mensaje. Ejemplo:

```
Tarea A: Actualizar arquitectura_backend.md   → subagente general-purpose
Tarea B: Actualizar arquitectura_frontend.md  → subagente general-purpose (paralelo)
```

**Regla:** No lanzar en paralelo subagentes que trabajan sobre los mismos archivos — pueden producir resultados inconsistentes.

---

## 8. Límites y cuándo NO usar subagentes

- **Tarea trivial (< 3 consultas):** Usa Glob/Grep/Read directamente.
- **El resultado depende del resultado anterior:** Ejecuta secuencialmente, no en paralelo.
- **Cambios de código pequeños:** El agente principal los hace directamente con Edit.
- **Conversación en curso con contexto fresco:** Si ya tienes el contexto en la sesión, no dupliques trabajo en un subagente.

---

## 9. Plantillas de prompt por rol

### Plantilla: Exploración de impacto
```
Proyecto: [nombre]
Stack: [backend + frontend]

Necesito saber qué archivos y funciones se verían afectados si [cambio X].

Lee estos archivos:
- [ruta 1]
- [ruta 2]

Reporta:
1. Archivos directamente afectados
2. Archivos indirectamente afectados (importan o dependen de los anteriores)
3. Riesgos o efectos secundarios
Respuesta en menos de 300 palabras.
```

### Plantilla: Actualización de documentación
```
Proyecto: [nombre]
Cambios recientes: [lista de 5-10 puntos]

Lee:
- [doc actual a actualizar]
- [archivos de código fuente relevantes]

Produce el contenido completo actualizado para [nombre del doc].
Mantén el mismo formato y estilo del original.
No inventes — solo documenta lo que encuentres en el código.
```

### Plantilla: Plan de implementación
```
Proyecto: [nombre]
Stack: [backend + frontend]
Convenciones: [RBAC, soft delete, Fernet, etc.]

Requerimiento: [descripción del feature]

Lee los archivos relevantes y produce un plan de implementación con:
1. Pasos numerados en orden
2. Archivos a crear o modificar por cada paso
3. Dependencias entre pasos
4. Estimación de complejidad (Baja/Media/Alta) por paso
```

---

## 10. Convención para este proyecto (Censo de Pacientes)

Al iniciar una sesión nueva en este proyecto:

1. Leer `.context/activeContext.md` para saber dónde se dejó
2. Leer `.context/progress.md` para saber qué está pendiente
3. Si hay blueprints activos en `docs/planes_de_cambios/`, revisarlos
4. Al terminar: actualizar `activeContext.md` con decisiones tomadas y `progress.md` con avances

Los blueprints en `docs/planes_de_cambios/` son la fuente de verdad de qué se está construyendo. Los archivos `docs/arquitectura_*.md` son la fuente de verdad del estado actual del sistema.
