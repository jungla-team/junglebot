# Changelog

## [4.1.2]

- Se actualiza versión de las dependencias pyTelegramBotAPI y netaddr
- Cambiado menú Bugs Bunny por Speedy
- Se arreglan las opciones de Junglescript: forzado de lista de canales /jungle_junglescript_force_channels y forzado de picons /jungle_junglescript_force_channels

## [4.1.1]

- Corregido comando /start de inicio bot ahora funciona correctamente
- Depuración código en la función instalación, ahora si una utilidad se intenta instalar y ya esta instalada devuelve mensaje.
- Correccion de salida comando sobre errores de objeto no encontrado
- Depuracion codigo en algunas funciones
- Eliminado codigo que ya no se usa
- Eliminado codigo compatibilidad con VTI
- Corregido bloqueo ip, ahora las ips bloqueadas se conservan en reinicio completo del receptor
- Restructuracion y ordenamiento menus botones con orden mas logico y mas facil de interactuar
- Añadido al mensajes de bienvenida y ayuda el alias del usuario
- Añadidas nuevas funciones al menu información del receptor
- Añadida funcion gestion tailscale
- Añadida funcion tareas crontab
- Añadida funcion cambio password receptor
- Añadida funcion de envio al bot telegram de una lista m3u de un favorito determinado
- Añadida funcion enviar cualquier archivo al receptor desde el bot telegram
- Añadida funcion bugs bunny para poder instalar muchos paquetes en el receptor

## [3.0.6]

- Añadida opción para enviar ficheros al deco simplemente arrastrando al bot el fichero que queramos subir. En el caption hay que indicar la ruta.
- Añadida opción de descargar ficheros del deco /command_getfile (ej. tmp/oscam.log) - sin poner la primera barra para evitar que telegram lo interprete como si fuera un comando.
- Añadido soporte para backup de las herramientas de Jungle-Team. Nos crea un zip y nos lo envía a nuestro bot de Telegram.

## [3.0.3]

- Bug fixed en las opciones de red de comprobación de ip y en el chequeo de puerto abierto

## [3.0.2]

- Añadida compatibilidad con Python3 para OpenATV 7
- Quitado aviso en bucle de streams intrusos. Avisa una única vez y se guarda dicho intruso en un fichero de intrusos
- Gestión fichero intrusos (listar y borrar intrusos) en el menú /streams y /conexiones 
- Corregido bug para arrancar/parar ghostreamy (gracias @JokerToco por el reporte)
- Actualización vía ipk únicamente, para ello ver la entrada del blog
- Documentación: https://jungle-team.com/junglebot-version-compatible-con-python-3-openatv-7-0/

## [3.0.1]

- Añadida compatibilidad con Python3 para OpenATV 7
- Quitado aviso en bucle de streams intrusos. Avisa una única vez y se guarda dicho intruso en un fichero de intrusos
- Gestión fichero intrusos (listar y borrar intrusos) en el menú /streams y /conexiones 

## [2.6.3]

    Añadida opción para enviar ficheros al deco simplemente arrastrando al bot el fichero que queramos subir. En el caption hay que indicar la ruta.
    Añadida opción de descargar ficheros del deco /command_getfile (ej. tmp/oscam.log) - sin poner la primera barra para evitar que telegram lo interprete como si fuera un comando.
    Añadido soporte para backup de las herramientas de Jungle-Team. Nos crea un zip y nos lo envía a nuestro bot de Telegram.
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-263-06-12

## [2.6.2]

    Bug fixed en las opciones de red de comprobación de ip y en el chequeo de puerto abierto
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-262-11-11

## [2.6.1]

    Quitado aviso en bucle de streams intrusos. Avisa una única vez y se guarda dicho intruso en un fichero de intrusos
    Gestión fichero intrusos (listar y borrar intrusos) en el menú /streams y /conexiones
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-261-09-02

## [2.5.33]

    Bug fixes
    Fix para usar el test de velocidad en VTi
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2533-04-13

## [2.5.32]

    Fix para usar el test de velocidad speedtest-cli
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2532-04-09

## [2.5.31]

    Añadido nuevo menú de gestión para /zerotier
    Subida versión speedtest-cli resolviendo sivel/speedtest-cli#769
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2531-04-09

## [2.5.30]

    Fix en /red_status para que funcione el acceso a ifconfig.me
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2530-03-27

## [2.5.29]

    Arreglado bug con el borrado de líneas cccam /emu_dellineacccam
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2529-03-04

## [2.5.28]

    Arreglado bug con reinicio programado de alimentación para el arranque de los servicios AUTO
    Redistribución menú /command y /junglebot
    Añadido nuevo menú /remotecontrol con las opciones del mando
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2528-02-22

## [2.5.27]

    Nueva opción para activar y desactivar líneas oscam bajo las opciones /emu_activatelineoscam y /emu_deactivatelineoscam
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2527-02-16

## [2.5.26]

    Arreglado bug a la hora de visualizar streams de ghostreamy con autostream
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2526-02-11

## [2.5.25]

    Arreglado bug a la hora de visualizar la versión instalada de ghostreamy /ghostreamy_ver_version
    Arreglado bug a la hora de consultar CHANGELOG /junglebot_changelog
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2525-02-10

## [2.5.24]

    Mejoras bajo el menú /ghostreamy
    Añadida opción de visualizar la versión instalada de ghostreamy /ghostreamy_ver_version
    Corregida la salida de borrado de línea oscam si la emuladora está parada previamente
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2524-02-10

## [2.5.23]

    A la hora de añadir una línea oscam se puede definir también el label (lo pedirá por parámetro)
    Corrección mensaje si no existe fichero /etc/Cccam.cfg
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-2523-02-08

## [2.5.22]

    Opción añadida para poder añadir como amigo en amigos.cfg un usuario de ghostreamy (ghostreamy:usuario)
    Opción añadida para poder borrar líneas oscam /emu_dellineoscam
    Opción añadida para poder borrar líneas cccam /emu_dellineacccam
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2522-02-07

## [2.5.21]

    Opción para quitar hide marked en vti /junglescript_del_hidemarked_vti
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2521-02-02

## [2.5.20]

    Mejora en la captura de pantalla para que salgan las imágenes con más calidad en Telegram (como archivo en vez de foto)
    Añadidas opciones de añadir y borrar entrada en el fichero save_bouquets bajo la opción /junglescript
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2520-01-31

## [2.5.19]

    Corrección de errores
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2519-01-08

## [2.5.18]

    Mejoras en el AUTOSTREAM para VTi
    Añadida opción para visualizar versión de junglescript /junglescript_show_version
    Cambio url para el servicio de chequeo de puertos remotos
    Se han quitado las guías rápidas, ya que ahora son interactivas y hay que hacerlo por terminal
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2518-12-17

## [2.5.17]

    Corregidas opciones para ghostreamy
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2517-12-03

## [2.5.16]

    Añadido mensaje para instalar y actualizar ghostreamy
    Se ha quitado el menú y opciones de letsencrypt
    Correcciones en mensajes
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2516-12-01

## [2.5.15]

    Corrección de errores
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2515-11-30

## [2.5.14]

    Añadido soporte para ghostreamy
    Quitado soporte para pystreamy
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2514-11-27

## [2.5.13]

    Adaptación dl bot para instalación a través de un unico ipk tanto para imágenes oealliance como para VTi
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-2513-11-11

## [2.5.12]

    Fix en el chequeo de versión
    Para más info consultar https://telegra.ph/Nueva-version-junglebot-2512-10-30

## [2.5.11]

    Adaptaciones para usar nuestro feed en las instalaciones de nuestras utilidades
    Para más info consultar https://telegra.ph/Nueva-version-junglebot-2511-10-29

## [2.5.10]

    Fix a la hora de comprobar la versión del propio bot en el server
    Fix a la hora de consultar el fichero de log de JungleScript
    Para más info consultar https://telegra.ph/Nueva-version-junglebot-2510-10-27

## [2.5.9]

    Corrección de errores en comprobación de puertos
    Cambiadas las url para descarga desde el servidor feed
    Para más info consultar https://telegra.ph/Nueva-version-junglebot-259-10-25

## [2.5.8]

    Corrección de errores en speedtest
    Para más info consultar https://telegra.ph/Nueva-version-junglebot-258-10-20

## [2.5.7]

    Corrección de errores
    Para más info consultar :https://telegra.ph/Nueva-version-junglebot-257-10-20

## [2.5.6]

    Corrección de errores
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-256-10-19

## [2.5.5]

    Añadida opción para poder forzar la actualización de picons /junglescript_force_picons
    Corrección de errores
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-255-10-19

## [2.5.4]

    Añadido parámetro AUTOFLASH para que envÃ­e aviso si se supera el 90% de ocupación en la FLASH
    Corrección de errores
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-254-10-08

## [2.5.3]

    Corrección de errores
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-253-10-05

## [2.5.2]

    Añadidos botones en opciones de elección tipo qué amigo quiero borrar de mi lista
    Añadidos parametros AUTORAM para que envÃ­e aviso si se supera el 80% de consumo de memoria RAM
    Añadidos parametros AUTOTEMP para que envÃ­e aviso si se superan los 90 grados de temperatura del micro
    Reducción de opciones en /emu y listado de emus con la que está activa marcada con asterisco
    En test de velocidad la posibilidad de elegir contra qué servidor lanzar la prueba a través de botones
    Mejora en cómo obtener la información de la RAM en /info_sistema
    Para más info consultar: https://telegra.ph/Nueva-version-junglebot-252-10-05

## [2.5.1]

    Posibilidad de elegir qué emuladora usar en imágenes VTi
    Añadida temperatura para todos los receptores e imágenes
    Añadida geolocalización de IPs
    Añadida opción para bloquear, desbloquear ip y ver ips bloqueadas
    Cambiar la opción de speedtest para que envÃ­e el png
    Fixes varios

## [2.5.0]

    Se ha añadido soporte a múltiples idiomas: español, inglés y alemán
    Soporte para teamblue en los avisos de streamings
    Posibilidad de elegir qué emuladora usar (no se da soporte en OpenSPA y VTi)
    Fixes varios

## [2.4.1] 

    Añadidos parámetros para evitar las caÃ­das del bot con las pérdidas de conectividad de red

## [2.4.0]

    Añadidas opciones en /emu para instalar oscam conclave, para ejecutarlo, para forzar la actualización y para actualizar el fichero autooscam.sh
    Añadida opción bajo /command opción para lanzar comandos de linux desde el bot /command_runcommand

## [2.3.14] 

    Upgrade librerÃ­a pyTelegramBotAPI a la versión 3.7.2 (errores caÃ­das bot)
    Añadida opción para ver la versión de la emu oscam
    Añadida opción para ver la versión de la emu cccam
    Fix en el top 10 de procesos por cpu

## [2.3.13]

    Fix errores varios en código
    Fix para ver la fecha de actualización de los picons

## [2.3.12]

    Fix en el calculo del consumo de RAM
    Fix para ver la fecha de actualización de los picons

## [2.3.11]

    Cambiada forma de añadir lÃ­neas cccam
    Añadidas opciones para consultar la fecha de actualización de la lista y de los picons
    Añadida opción para añadir/borrar favoritos a fav_bouquets
    Aviso si hay nueva versión del bot publicada en cada inicio

## [2.3.10]

    Fix en el que se añaden reintentos a la conexión con la api de openwebif
    Se añade opción para que se pueda arrancar/parar/reiniciar oscam en cualquier imagen
    Se añaden trazas de streams en el log
    Se cambia el aviso de puerto cerrado en pystreamy

## [2.3.9]

    Fix en la opción de desinstalar junglescript
    Quitado el link para donaciones

## [2.3.8]

    Añadido filtrado de direcciones del tipo 127.0.x.x en los streamings
    Añadida opción para poder ver el log de pystreamy

## [2.3.7]

    Añadida opción para cambio de canal desde /junglebot
    Añadidos links a pystreamy, junglescript, junglebot, oscamconclave y a paypal para donaciones (en /ayuda)
    Actualización de la librerÃ­a pyTelegramBotAPI a la versión 3.7.1

## [2.3.6]

    Corregido aviso /stream_ver en VTI
    Correcciones de código

## [2.3.5]

    Corregida instalación vÃ­a ipk en VTI
    Corregido aviso AUTOSTREAM

## [2.3.4]

    Añadida opción de enviar mensajes al receptor
    Se han filtrado en /stream_ver para que saque todos los canales no locales

## [2.3.3]

    Añadida fecha para cada lÃ­nea insertada en el log
    Añadida opción de purgar el log de propio bot

## [2.3.2]

    Corregida la desinstalación de junglescript para que borre correctamente el fichero de configuración
    Añadido el reinicio de oscam cuando se añade una lÃ­nea nueva y asÃ­ aparezca en el estado
    Añadida la excepción de conexiones locales 127.0.0.1 para /stream_ver

## [2.3.1]

    Arreglados temas de oscam si estaba el daemon parado
    Cambiado el comando screenshot para que funcione en todos los dispositivos (incluÃ­do Octagon)

## [2.3.0]

    Modificación para que no sean necesarios los parámetros USUARIO_URL, PASSWORD_URL, PUERTO_URL en el parametros.py (se pueden quitar de dicho fichero o si aparacen no se van a tomar en cuenta)

## [2.2.9]

    Corrección de errores opciones AUTOSTREAM, AUTOSSH, AUTOFTP

## [2.2.8]

    Lista de comandos poniendo "/"
    Añadidos botones de confirmación si/no
    Nuevo menú para lanzar scripts de las guÃ­as rápidas desde el propio bot
    Nueva opción para el reinicio de interfaz cuando se actualizar el epg
    Añadida opción de borrar EPG

## [2.2.7]

    Corregido errores sobre AUTOSTREAM, AUTOSSH, AUTOFTP
    Corregido error al añadir parámetro

## [2.2.6]

    Arreglados errores al insertar parámetros en el fichero de configuración
    Añadidas opciones en /epg para desinstalar EPGImport y CrossEPG
    Cambiado formato de algunas salidas

## [2.2.5]

    Nuevo menú /conexiones para los avisos FTP y SSH (variables AUTOSSH y AUTOFTP en parametros por defecto las mete a 0 el propio bot)
    Añadida la opción para la actualización forzada de la lista de canales desde /junglescript
    Arreglado aviso de oscam_info para que diga que no se están usando tunners
    Arreglado el tema de las lÃ­neas de oscam
    Se ha añadido la confirmación a más opciones
    Añadida opción para ver los usuarios conectados a oscam
    Añadido comando para ver el changelog
    Añadida la opción de parar streamproxy dentro de /streams
    Añadir ruta completa parametros.py en función add_variable_parametros
    Añadida la descarga del requirements.txt su instalación mediante pip en la update del bot

## [2.2.4b]

    Arreglados errores de conexión con Telegram
    Añadido ver log de junglescript
    Añadido ver log de junglebot
    Añadido meter rangos de IPs y DNS (ej: 192.168.1.* , prueba.duckdns.org...)

## [2.2.3]

    Fix para errores varios

## [2.2.2]

    Optimización de código

## [2.2.1]

    Arreglado error en el reinicio del propio bot
    Añadida opción de reiniciar el bot
    Arreglados errores con el login con password en blanco
    Captura de excepciones para evitar que se caiga el bot
    Arreglado error en la captura de imagen

## [2.2.0]

    Arreglados errores con el login de OpenWebif
    Añadido update del propio bot en las opciones /junglebot
    Arreglados errores con las rutas de los ficheros epg.dat

## [2.1.0]

    Renovación del bot a la versión 2.0 con aspecto visual con botones
    Añadidas nuevas funcionalidades para cambiar parámetros del deco desde el propio bot
    Añadida funcionalidad pystreamy, epg, grabaciones...

## [1.0.0]

    Primera versión del bot (sin ipk asociado)
    Para más info consultar: https://telegra.ph/Nueva-version-JungleBot-301-09-03
