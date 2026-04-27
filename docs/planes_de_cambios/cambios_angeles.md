Vamos a hacer varios cambios en la forma en la que se registran los datos y en la forma en la que se administraran los datos. después de una revisión con la primera área que pidió esta aplicación hicieron algunos cambios en la lógica. 

El cambio más importante es que cambiará el concepto de la unidad mínima que buscamos registrar, lo que quieren es tener combinaciones de pacientes-medicamento, a un paciente se le prescribe un mediamento, solo se registra una vez, una vez que termina el tiempo de esa prescripción, se debe validar si continua con el mediamento (mediante una función nueva llamada validación de continuidad), de lo contrario se le consideraría como inactiva esa combinación. ojo pero el mismo paciente puede tener otra combinación con otro mediamento, esa podría seguir activa. 


Te pasare, una imagen  del nuevo modelo de datos para que veas los nombres. veras que la tabla de recetas cambio de nombre a "registros", y como a la tabla de "pacientes" se le agregaron algunas columnas. revisala para ve si consideras que cambiemos algo para cumplir con los cambios. 


Requerimientos:
1.El registro de pacientes será llenara desde el que era el formulario de recetas, que ahora es de Prescripciones. 

comentario sam: aquí debemos cambiar como se registraran los pacientes y las recetas (ahora llamadas "Prescripciones"), anteriormente teníamos dos modulos separados para registrar un paciente y una receta, ahora la idea es que registremos un paciente al mismo tiempo que su Prescripción, en el nuevo modelo de datos cabiaremos de nombre de la tabla "recetas" por "registros", en esta tabla registros colocaremos los datos de la Prescripciones, y los datos del paciente. agregaríamos mas datos a este formulario combinado, al que accederíamos por el modulo de Recetas, (también le cambiaremos el nombre a la etiqueta de este modulo para llamarlo "Registrar un paciente" ), entonces en el modulo de "Registrar un paciente" ingresariamos los datos de la prescripción y los datos del Pacientes. la idea es que ahora manejemos paciente y medicamentos, ver las prescripciones que se le han dado a un paciente. te pasare, una imagen  del nuevo modelo de datos para que veas los nombres. si agregamos la nueva tabla de pacientes-medicamento por este formulario agregaríamos un registro a esa nueva tabla. 

Te dare un ejemplo al registrar un paciente, cuando llega un nuevo paciente a una unidad, el medico al registrar una nueva precripción en donde se invluyen los datos del paciente, al colocar el curp del paciente le debería aprecer un enlace al historial de prescripciones del paciente, podrá regresar al modulo de prescripciones que estaba llenando, ahora podrá continuar



2. El formulario de recetas se le agregaran 
a.Diagnóstico 
b.Estatus del diagnóstico (lista desplegable)
c.Peso
d.Talla
e.Prescripción

Comentario sam: estos campos nuevos se agregan al formulario de registro de iran en el formulario del frontend, en la base de datos se llamaran un poco diferente, te pasare, una imagen  del nuevo modelo de datos para que veas los nombres.

3.La función de actualizar el registro con base con la operación matemática del tiempo del registro y la prescripción más un mes.
a.Si no actualizas en este tiempo se pasa inactivo

Comentario sam: el medico indicara la fecha en la que la prescripción termina, se contara un mes a partir de esa fecha, en ese momento el medico deberá validar si el paciente continua con el medicamento, con la prescripción que ya se le dio al paciente, si el paciente no continua o el medico no hace la validación, por medio de una función nueva que viene en el punto siguiente.

4.Alerta de toca actualizar. 

Comentario sam: esta es la función mencionada en el punto anterior, cuando se haya cumplido el tiempo del tratamiento de un paciente más un mes, al medico (Responsable de unidad) asociado al paciente le aparecerá un mensaje, podría ser una una zona de notificaciones en los que se indique que un paciente a cumplido con el tiempo del tratamiento más un mes, y es necesario confirmar que el paciente continua con ese medicamento o tener la opcion de editar la información de su prescripción. 

5.El módulo de recetas se llamará -> Registrar un paciente 

6.Modulo -> pacientes de activos 

Comentario sam: este es como el modulo de pacientes que ya teníamos pero  se llamara "Pacientes activos"

7.Un buscador de paciente dentro de la base cuando inicie el registro.

Comentario sam: esta función lo que pretende es que cuando uno quiera ingresar una nueva prescripción (en el formulario de prescripciones, que ahora se fusionaría con los datos del paciente) cuando uno busque a un paciente por su curp, si el paciente ya esta en la tabla de pacientes, aparecera un enlace a "Ver detalles del paciene" que se ve en el modulo de pacientes, podrá buscarlo en todos los registros de todos los estados, el objetivo es saber si ya existe esa bombinacion (paciente/medicamento, ya sea activo o inactivo), aquí el botón de regresar debera regresar al formulario de prescripción que se estaba llenando.
