# 📘 Guía de Preguntas y Respuestas para Administración de Linux

## 1. Bash y Shell Scripting

**Pregunta 1:** Con `set -e` habilitado, ¿en qué caso Bash NO sale inmediatamente aunque un comando retorne estado distinto de cero?

**Respuesta:** Cuando el comando fallido es parte de la prueba de un `if`, `while`, `until`, o de una lista AND/OR (`&&`/`||`) que forma parte de una expresión condicional.

---

**Pregunta 2:** Con `set -u` habilitado, necesitas expandir una variable posiblemente no definida sin abortar, usando un valor por defecto. ¿Cuál forma de expansión es la correcta?

**Respuesta:** `${var:-valor_por_defecto}` permite expandir la variable, pero si no está definida, usa `valor_por_defecto` sin generar error.

---

**Pregunta 3:** ¿Qué efecto tiene `shopt -s inherit_errexit` sobre la sustitución de comandos `$(...)`?

**Respuesta:** Hace que `$(...)` herede `errexit` en lugar de desactivarlo en el subshell. Por defecto, Bash desactiva `set -e` dentro de una sustitución de comando; con esta opción el subshell mantiene `-e` si está activado.

---

**Pregunta 4:** ¿Qué opción de `shopt` hace que un patrón de glob sin coincidencias se elimine (expanda a nada) en vez de quedar literal?

**Respuesta:** `nullglob`. Con esta opción habilitada, si un patrón no encuentra archivos que coincidan, se elimina (expande a cadena vacía) en lugar de quedar como texto literal.

---

**Pregunta 5:** Si se define `trap 'acción' RETURN`, ¿cuándo se ejecuta acción?

**Respuesta:** Cada vez que termina una función del shell o un script ejecutado con `.` o `source`. No se ejecuta al salir del shell principal.

---

**Pregunta 6:** En el builtin `printf` de Bash, ¿qué describe mejor el especificador de formato `%q`?

**Respuesta:** Imprime el argumento con comillas para reusarlo como entrada del shell, escapando o entrecomillando caracteres especiales para que sea una palabra válida y segura.

---

**Pregunta 7:** Para reenviar todos los argumentos recibidos por un script o función preservando los límites de cada argumento (incluyendo espacios) al estar entre comillas, ¿qué expansión es la correcta?

**Respuesta:** `"$@"` expande todos los argumentos posicionales como palabras separadas, respetando espacios y comillas originales.

---

**Pregunta 8:** En Bash, ¿a qué es equivalente `&>archivo`?

**Respuesta:** Es equivalente a `>archivo 2>&1`. Redirige tanto stdout como stderr al archivo indicado.

---

**Pregunta 9:** Tienes `trap 'handler' ERR` y necesitas que el trap ERR se herede también en funciones, sustituciones de comando y comandos ejecutados en subshell. ¿Qué opción debes habilitar?

**Respuesta:** `set -E` (o activar `errtrace`). Con esta opción, el trap `ERR` se hereda en funciones, sustituciones y subshells.

---

**Pregunta 10:** En un script se usa `while getopts ':ab:c' opt; do ...; done` y se invoca con `-b` sin argumento (siendo `b:` una opción que requiere argumento). ¿Qué resultado es el correcto para `opt` y `OPTARG` en ese caso?

**Respuesta:** `opt` vale `:` y `OPTARG` vale `b`. Cuando el primer carácter de la cadena de opciones es `:`, se activa el modo silencioso: si falta un argumento, `opt` toma `:` y `OPTARG` toma el nombre de la opción que falló.

---

**Pregunta 11:** ¿Para qué sirve `wait -n -p varname` en Bash?

**Respuesta:** `wait -n` espera al siguiente job que termine; en versiones recientes de Bash algunas implementaciones soportan `-p varname` para guardar el PID del job terminado en `varname`. Verifica la versión de Bash si dependes de `-p`.

---

**Pregunta 12:** En Bash, con `set -o pipefail` habilitado, ¿cuál es el criterio correcto para el exit status de un pipeline?

**Respuesta:** Es el estado del último comando que falle (no cero) hacia la derecha; o cero si todos salen bien. Con `pipefail` activado, el pipeline retorna el estado del último comando que falló.

---

## 2. Señales y Procesos

**Pregunta 1:** En `kill(1)`, ¿qué efecto tiene usar la señal 0 (por ejemplo, "kill -s 0 PID")?

**Respuesta:** No envía una señal real; solo realiza verificación de errores. La señal 0 se usa para comprobar si el proceso existe y si el usuario tiene permiso para enviarle señales.

---

**Pregunta 2:** Según `proc_pid_io`, ¿qué describe correctamente el contenido de `/proc/PID/io`?

**Respuesta:** Estadísticas de I/O del propio proceso (y sus hilos) como `rchar`, `wchar`, `read_bytes`, `write_bytes`, `syscr` y `syscw`. No es un agregado automático del I/O de procesos hijo recolectados con `wait`.

---

**Pregunta 3:** En `kill(1)`, ¿qué significa pasar el destino "0" (por ejemplo, "kill -TERM 0")?

**Respuesta:** Señala a todos los procesos del grupo de proceso actual. Usar PID igual a 0 envía la señal a todos los procesos del mismo grupo que el proceso que ejecuta `kill`.

---

**Pregunta 4:** Según `bash(1)`, cuando bash es interactivo y no hay traps, ¿qué señal ignora para que "kill 0" no mate el shell interactivo?

**Respuesta:** No existe una señal que bash interactivo ignore de manera universal; el comportamiento depende de la versión de Bash y de traps/ajustes del entorno. No se debe asumir que `SIGTERM` esté siempre ignorada.

---

**Pregunta 5:** En `setpriority`, si `which` es `PRIO_PGRP` y `who` es 0, ¿sobre qué objetivo se aplica la prioridad?

**Respuesta:** Sobre el grupo de procesos del proceso que llama. Con `PRIO_PGRP` y `who=0`, actúa sobre el grupo de procesos actual.

---

**Pregunta 6:** Según `getrlimit`, ¿qué ocurre al alcanzar el soft limit y luego el hard limit de `RLIMIT_CPU`?

**Respuesta:** En soft se entrega SIGXCPU y en hard el proceso es terminado con SIGKILL. Al alcanzar el soft limit se envía SIGXCPU; si se alcanza el hard limit, se envía SIGKILL.

---

**Pregunta 7:** ¿Qué pseudoarchivo en `/proc` es usado por `ps` y expone información del proceso en formato de campos?

**Respuesta:** `/proc/PID/status`. Contiene información del proceso en formato legible con campos etiquetados como `Name:`, `Pid:`, `State:`, etc.

---

**Pregunta 8:** Según `signal(7)`, en Linux algunas interfaces bloqueantes pueden fallar con qué error tras detenerse por una stop signal y reanudarse con SIGCONT, incluso sin handlers.

**Respuesta:** `EINTR`. Cuando un proceso se detiene y se reanuda, algunas llamadas bloqueantes pueden retornar error de interrupción.

---

**Pregunta 9:** Según `kill(2)`, si el pid es menor que -1, ¿a qué destino se envía la señal?

**Respuesta:** Al grupo de procesos cuyo ID es el valor absoluto del pid. Si `pid` es menor que -1, la señal se envía a todos los procesos del grupo de procesos con ID igual al valor absoluto.

---

**Pregunta 10:** Según `proc_pid_cmdline(5)`, ¿qué ocurre al leer `/proc/pid/cmdline` si el proceso es un zombie?

**Respuesta:** La lectura devuelve 0 caracteres (archivo vacío). Cuando un proceso es zombie, el archivo `cmdline` está vacío.

---

**Pregunta 11:** En `prlimit`, ¿qué sintaxis se usa para modificar solo el soft limit y dejar el hard limit sin cambios para un recurso?

**Respuesta:** Usar un valor con dos puntos final como `--nproc=512:`. Esto establece el soft limit en 512 y conserva el hard limit actual.

---

**Pregunta 12:** En Bash, ¿qué opción de `ulimit` selecciona explícitamente el hard limit?

**Respuesta:** La opción `ulimit -H`. `-S` para soft limit, `-H` para hard limit.

---

## 3. Permisos y ACLs

**Pregunta 1:** Al modificar ACLs con `setfacl` sin especificar una máscara explícita, ¿qué ocurre por defecto con la entrada `mask`?

**Respuesta:** Se recalcula la máscara como unión de permisos relevantes. La máscara se recalcula automáticamente como la unión de permisos de todas las entradas que no son del propietario, grupo propietario ni otros.

---

**Pregunta 2:** En el modelo de ACLs mostrado por `getfacl`, ¿a qué entradas NO afecta la "effective rights mask"?

**Respuesta:** Al propietario del archivo y a otros. La máscara limita los permisos máximos de grupo propietario, usuarios nombrados y grupos nombrados, pero no afecta al propietario ni a otros.

---

**Pregunta 3:** En Linux, ¿qué efecto tiene el bit `setgid` aplicado a un directorio compartido sobre los archivos nuevos creados dentro?

**Respuesta:** Los archivos nuevos heredan el GID del directorio. Cuando un directorio tiene setgid activado, los archivos creados heredan el grupo del directorio, no el grupo principal del usuario.

---

**Pregunta 4:** Según el modelo de ACL mostrado por `getfacl`, ¿a quién limita la entrada `mask`?

**Respuesta:** A todos los grupos y a los usuarios nombrados; no afecta a owner ni a others. La máscara limita los permisos efectivos de grupo propietario, usuarios nombrados y grupos nombrados.

---

**Pregunta 5:** ¿Qué hace `setfacl` con la opción `-b` (`--remove-all`) sobre un archivo que tiene ACL extendidas?

**Respuesta:** Elimina todas las entradas ACL extendidas y conserva las entradas base de owner, group y others. Elimina ACL extendidas pero mantiene las tres entradas base equivalentes a permisos tradicionales.

---

**Pregunta 6:** Según GNU Coreutils, ¿por qué scripts portables no deben depender de que `chmod` establezca o limpie bits setuid o setgid en directorios de forma uniforme?

**Respuesta:** Porque POSIX permite que las implementaciones ignoren solicitudes de set o clear en directorios. El comportamiento es "implementation-defined", variando entre sistemas.

---

**Pregunta 7:** Cuando el directorio padre tiene una Default ACL, ¿qué ocurre con `umask` al crear un archivo o directorio mediante llamadas como `open` o `mkdir`?

**Respuesta:** Se ignora umask, se hereda la Default ACL y luego se apagan bits ausentes del modo solicitado. La umask se ignora y los permisos finales son la intersección entre el modo solicitado y la Default ACL.

---

**Pregunta 8:** En `chmod` aplicado a directorios, ¿cómo se limpian los bits setuid y setgid usando modo numérico?

**Respuesta:** Especificando el primer dígito octal (por ejemplo `chmod 0755 <archivo>`) o usando la forma simbólica para quitar los bits especiales: `chmod u-s,g-s <archivo>`. Estas formas eliminan setuid/setgid explícitamente.

---

## 4. sudo y Privilegios

**Pregunta 1:** ¿Qué realiza `sudo -v` (validate) cuando el plugin soporta cache de credenciales?

**Respuesta:** Actualiza credenciales en caché y autentica si hace falta sin ejecutar un comando. Extiende el tiempo de validez de la caché de credenciales sin ejecutar ningún comando.

---

**Pregunta 2:** Cuando un usuario invoca `sudo` con asignaciones `VAR=valor`, ¿en qué caso puede establecer variables que normalmente serían rechazadas por la política?

**Respuesta:** Si `setenv` está habilitado, o el comando tiene tag `SETENV`, o el comando coincidente es `ALL`. Se necesita alguna de estas condiciones para poder pasar variables de entorno en la línea de comandos.

---

**Pregunta 3:** Para permitir que un binario sin setuid pueda escuchar en un puerto menor a 1024 (por ejemplo 443), ¿qué capability es la indicada?

**Respuesta:** `CAP_NET_BIND_SERVICE`. Permite enlazar un socket a un puerto privilegiado (menor a 1024) sin ejecutarse como root.

---

**Pregunta 4:** En sudoers, ¿qué flag suele estar habilitado por defecto para ejecutar comandos con un entorno nuevo y mínimo?

**Respuesta:** El flag `env_reset`. Limpia el entorno del usuario y lo reemplaza con un entorno mínimo y seguro.

---

## 5. systemd: Unidades y Servicios

**Pregunta 1:** En una unidad `.socket`, ¿para qué sirve la directiva `Service=`?

**Respuesta:** Cambia el nombre del servicio que se activará por el socket (en lugar del `.service` con el mismo nombre). Por defecto, `foo.socket` activa `foo.service`; con `Service=` se puede especificar otro nombre.

---

**Pregunta 2:** En un unit file, ¿cuál afirmación es correcta sobre `Wants=` y el orden de arranque entre unidades?

**Respuesta:** `Wants=` no define orden y suele combinarse con `After=` o `Before=` para ordenar. `Wants=` establece dependencia débil pero no impone orden.

---

**Pregunta 3:** ¿Cuál descripción corresponde correctamente a `systemctl mask foo.service`?

**Respuesta:** Crea un enlace a `/dev/null` e impide cualquier forma de activación. Hace que el servicio sea completamente imposible de iniciar, tanto manualmente como por dependencias.

---

**Pregunta 4:** ¿Qué hace `systemctl preset nginx.service` según su definición?

**Respuesta:** Resetea el estado enable/disable según la política de preset configurada. Aplica las reglas definidas en los archivos de política de preset.

---

**Pregunta 5:** Según `systemd.kill(5)`, ¿qué hace `KillMode=mixed` al detener una unidad?

**Respuesta:** Envía SIGTERM al proceso principal y luego SIGKILL al resto de procesos del cgroup de la unidad. Primero SIGTERM al principal, luego si no termina, SIGKILL a todos.

---

**Pregunta 6:** En un servicio, ¿cuál afirmación es correcta sobre múltiples `ExecStart=` y la asignación vacía `ExecStart=`?

**Respuesta:** Múltiples `ExecStart=` se permiten con `Type=oneshot`; un `ExecStart=` vacío resetea la lista de comandos. Solo con `Type=oneshot` se permiten múltiples comandos, y vacío limpia la lista.

---

**Pregunta 7:** ¿Qué muestra `systemctl cat foo.service` según `systemctl(1)`?

**Respuesta:** Muestra los archivos "fragment" y "drop-ins" en disco con comentarios de ruta. Muestra el contenido completo de la unidad tal como systemd la ve, incluyendo todos los drop-ins.

---

**Pregunta 8:** Respecto a `systemctl list-dependencies --reverse foo.service`, ¿cuál afirmación es correcta según `systemctl(1)`?

**Respuesta:** Solo lista unidades actualmente cargadas en memoria, no un inventario completo de dependencias inversas. Muestra solo unidades que están cargadas en memoria en ese momento.

---

## 6. systemd: Timers y Dependencias

**Pregunta 1:** Según `systemd.timer(5)`, ¿qué describe correctamente `RandomizedOffsetSec=`?

**Respuesta:** Aplica un retardo aleatorio entre 0 y el valor indicado a timers basados en `OnCalendar=`, ayudando a desincronizar ejecuciones. El comportamiento exacto y si el offset persiste entre reinicios puede depender de la versión de systemd.

---

**Pregunta 2:** Sobre `Persistent=` en `systemd.timer`, ¿cuál afirmación es correcta?

**Respuesta:** Solo afecta timers con `OnCalendar` y permite "ponerse al día" de ejecuciones perdidas. Si el sistema estaba apagado en el momento programado, el servicio se ejecuta inmediatamente después del arranque.

---

**Pregunta 3:** En `systemd.unit(5)`, si no se cumplen las directivas `Condition...=` o `Assert...=` antes de arrancar una unidad, ¿qué comportamiento describe mejor la documentación?

**Respuesta:** `Condition` omite el arranque casi silenciosamente; `Assert` aborta el arranque con error, sin marcar la unidad como failed. Condition salta la unidad, Assert la hace fallar.

---

**Pregunta 4:** En `systemd.socket`, ¿qué efecto tiene `Accept=yes` sobre el tipo de servicio activado por la unidad de socket?

**Respuesta:** `Accept=yes` activa instancias de un servicio template; `Accept=no` activa un servicio regular. Con Accept=yes, systemd lanza una instancia separada por cada conexión.

---

## 7. journald y journalctl

**Pregunta 1:** Con `journalctl --output=export`, ¿cuál es el objetivo principal del modo export?

**Respuesta:** Serializar el journal en un stream (mayormente textual) apto para backup y transferencia, e importable con herramientas de systemd. Formato estable de intercambio de entradas del journal.

---

**Pregunta 2:** Respecto a `journalctl --output-fields=...`, ¿qué campos se imprimen siempre (aunque no se incluyan en la lista) en los modos que normalmente muestran todos los campos?

**Respuesta:** `__CURSOR`, `__REALTIME_TIMESTAMP`, `__MONOTONIC_TIMESTAMP` y `_BOOT_ID`. Estos cuatro campos siempre se imprimen incluso si no se incluyen en la lista.

---

**Pregunta 3:** Sobre filtros de tiempo (`--since=` y `--until=`), ¿cuál afirmación es correcta?

**Respuesta:** Si omites la parte de hora, asume 00:00:00; acepta yesterday, today, tomorrow, now y tiempos relativos con prefijo + o -. Acepta expresiones flexibles de fecha y hora.

---

**Pregunta 4:** En `journalctl`, ¿qué valor de `--namespace=` muestra el namespace indicado y el namespace por defecto intercalados, pero no incluye otros namespaces?

**Respuesta:** `--namespace=NOMBRE` selecciona el namespace indicado. La sintaxis con prefijo `+` no es la forma estándar documentada; consulte `journalctl --help` o la documentación de su versión para opciones avanzadas de combinación de namespaces.

---

**Pregunta 5:** ¿Qué describe correctamente `-b` o `--boot` en `journalctl`?

**Respuesta:** Muestra logs de un boot específico y agrega un match `_BOOT_ID=`; sin argumento usa el boot actual; y `-b -1` revierte el efecto de un `-b` previo. Filtra por arranque específico.

---

**Pregunta 6:** Al usar `journalctl -u nginx.service`, ¿qué hace `-u/--unit=` además de filtrar por la unidad?

**Respuesta:** Agrega un match `_SYSTEMD_UNIT=nginx.service` y además incluye coincidencias adicionales para mensajes de systemd y sobre coredumps de esa unidad. Construye una consulta OR con múltiples filtros relacionados.

---

**Pregunta 7:** ¿Qué comando selecciona explícitamente los logs de la última invocación (runtime cycle) de una unidad, usando soportes de journalctl para invocaciones?

**Respuesta:** Algunas versiones recientes de systemd/journalctl soportan `--invocation=` para filtrar por número de invocación; la disponibilidad y el significado exacto (por ejemplo, si `0` representa la última) dependen de la versión. Compruebe `journalctl --version` y la ayuda local antes de usarla.

---

**Pregunta 8:** ¿Qué describe con precisión la salida de `journalctl --show-cursor`?

**Respuesta:** Muestra el cursor después de la última entrada, tras dos guiones, en una línea tipo `--cursor: ...`. Añade al final una línea con el cursor de la última entrada mostrada.

---

**Pregunta 9:** ¿Qué describe correctamente `journalctl --truncate-newline`?

**Respuesta:** Corta cada mensaje al primer salto de línea y muestra solo la primera línea. Trunca cada mensaje después del primer salto de línea.

---

**Pregunta 10:** En `journald.conf`, ¿qué significa `Storage=auto` y cómo se relaciona con la persistencia?

**Respuesta:** `auto` se comporta como `persistent` si existe `/var/log/journal`, y como `volatile` si no existe. Si existe `/var/log/journal`, almacena persistentemente; si no, usa memoria volátil.

---

**Pregunta 11:** ¿Cuál afirmación describe correctamente `journalctl -k` (o `--dmesg`)?

**Respuesta:** Añade el match `_TRANSPORT=kernel` e implica `--boot=0` salvo que se especifique otro boot. Muestra solo mensajes del kernel del arranque actual.

---

**Pregunta 12:** ¿Para qué sirve `--cursor-file=FILE` cuando quieres consumir el journal de forma incremental?

**Respuesta:** Para iniciar desde el cursor guardado en FILE (si existe) y al final escribir allí el cursor del último registro procesado. Permite implementar consumidores incrementales que recuerdan hasta dónde leyeron.

---

## 📌 Resumen para el Administrador

| Tema | Puntos Clave |
|------|--------------|
| **Bash** | `set -euo pipefail`, `${var:-}`, `trap`, `getopts`, `"$@"`, `&>` |
| **Señales** | `kill -0`, `/proc/PID/status`, `prlimit`, `ulimit -H`, `EINTR` |
| **Permisos** | ACLs, máscara efectiva, `setgid` en directorios, `setfacl -b`, `chmod 0755` |
| **sudo** | `env_reset`, `SETENV`, `CAP_NET_BIND_SERVICE` |
| **systemd** | `Wants=` vs `Requires=`, `KillMode=`, `Accept=`, `systemctl cat`, `list-dependencies --reverse` |
| **journalctl** | `--since/--until`, `-b`, `--invocation`, `--output-fields`, `--cursor-file`, `Storage=` |
