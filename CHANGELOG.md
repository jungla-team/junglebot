# Changelog

## [2.5.2] - 05/10/2020 

- Añadidos botones en opciones de elección tipo qué amigo quiero borrar de mi lista
- Añadidos parametros AUTORAM para que envíe aviso si se supera el 80% de consumo de memoria RAM
- Añadidos parametros AUTOTEMP para que envíe aviso si se superan los 90 grados de temperatura del micro
- Reducción de opciones en /emu y listado de emus con la que está activa marcada con asterisco
- En test de velocidad la posibilidad de elegir contra qué servidor lanzar la prueba a través de botones
- Mejora en cómo obtener la información de la RAM en /info_sistema
- Para más info consultar: https://telegra.ph/Nueva-version-junglebot-252-10-05

## [2.5.1] - 28/09/202

- Posibilidad de elegir qué emuladora usar en imágenes VTi
- Añadida temperatura para todos los receptores e imágenes
- Añadida geolocalización de IPs
- Añadida opción para bloquear, desbloquear ip y ver ips bloqueadas
- Cambiar la opción de speedtest para que envíe el png
- Fixes varios

## [2.5.0] - 25/09/2020

- Se ha añadido soporte a múltiples idiomas: español, inglés y alemán
- Soporte para teamblue en los avisos de streamings
- Posibilidad de elegir qué emuladora usar (no se da soporte en OpenSPA y VTi)
- Fixes varios

## [2.4.1] - 02/09/2020

- Añadidos parámetros para evitar las caídas del bot con las pérdidas de conectividad de red

## [2.4.0] - 27/08/2020

- Añadidas opciones en /emu para instalar oscam conclave, para ejecutarlo, para forzar la actualización y para actualizar el fichero autooscam.sh
- Añadida opción bajo /command opción para lanzar comandos de linux desde el bot /command_runcommand

## [2.3.14] - 22/08/2020

- Upgrade librería pyTelegramBotAPI a la versión 3.7.2 (errores caídas bot)
- Añadida opción para ver la versión de la emu oscam
- Añadida opción para ver la versión de la emu cccam
- Fix en el top 10 de procesos por cpu

## [2.3.13] - 14/08/2020

- Fix errores varios en código
- Fix para ver la fecha de actualización de los picons

## [2.3.12] - 13/08/2020

- Fix en el calculo del consumo de RAM
- Fix para ver la fecha de actualización de los picons

## [2.3.11] - 07/08/2020
- Cambiada forma de añadir líneas cccam
- Añadidas opciones para consultar la fecha de actualización de la lista y de los picons
- Añadida opción para añadir/borrar favoritos a fav_bouquets
- Aviso si hay nueva versión del bot publicada en cada inicio

## [2.3.10] - 11/07/2020

- Fix en el que se añaden reintentos a la conexión con la api de openwebif
- Se añade opción para que se pueda arrancar/parar/reiniciar oscam en cualquier imagen
- Se añaden trazas de streams en el log
- Se cambia el aviso de puerto cerrado en pystreamy

## [2.3.9] - 24/06/2020

- Fix en la opción de desinstalar junglescript
- Quitado el link para donaciones

## [2.3.8] - 24/06/2020

- Añadido filtrado de direcciones del tipo 127.0.x.x en los streamings
- Añadida opción para poder ver el log de pystreamy

## [2.3.7] - 16/06/2020

- Añadida opción para cambio de canal desde /junglebot
- Añadidos links a pystreamy, junglescript, junglebot, oscamconclave y a paypal para donaciones (en /ayuda)
- Actualización de la librería pyTelegramBotAPI a la versión 3.7.1

## [2.3.6] - 14/06/2020

- Corregido aviso /stream_ver en VTI
- Correcciones de código

## [2.3.5] - 11/06/2020

- Corregida instalación vía ipk en VTI
- Corregido aviso AUTOSTREAM

## [2.3.4] - 07/06/2020

- Añadida opción de enviar mensajes al receptor
- Se han filtrado en /stream_ver para que saque todos los canales no locales

## [2.3.3] - 06/06/2020

- Añadida fecha para cada línea insertada en el log
- Añadida opción de purgar el log de propio bot

## [2.3.2] - 01/06/2020

- Corregida la desinstalación de junglescript para que borre correctamente el fichero de configuración
- Añadido el reinicio de oscam cuando se añade una línea nueva y así aparezca en el estado
- Añadida la excepción de conexiones locales 127.0.0.1 para /stream_ver

## [2.3.1] - 29/05/2020

- Arreglados temas de oscam si estaba el daemon parado
- Cambiado el comando screenshot para que funcione en todos los dispositivos (incluído Octagon)

## [2.3.0] - 26/05/2020

- Modificación para que no sean necesarios los parámetros USUARIO_URL, PASSWORD_URL, PUERTO_URL en el parametros.py (se pueden quitar de dicho fichero o si aparacen no se van a tomar en cuenta)

## [2.2.9] - 24/05/2020

- Corrección de errores opciones AUTOSTREAM, AUTOSSH, AUTOFTP

## [2.2.8] - 23/05/2020

- Lista de comandos poniendo "/"
- Añadidos botones de confirmación si/no
- Nuevo menú para lanzar scripts de las guías rápidas desde el propio bot
- Nueva opción para el reinicio de interfaz cuando se actualizar el epg
- Añadida opción de borrar EPG

## [2.2.7] - 18-05-2020

- Corregido errores sobre AUTOSTREAM, AUTOSSH, AUTOFTP
- Corregido error al añadir parámetro

## [2.2.6] - 18-05-2020

- Arreglados errores al insertar parámetros en el fichero de configuración
- Añadidas opciones en /epg para desinstalar EPGImport y CrossEPG
- Cambiado formato de algunas salidas

## [2.2.5] - 14-05-2020

- Nuevo menú /conexiones para los avisos FTP y SSH (variables AUTOSSH y AUTOFTP en parametros por defecto las mete a 0 el propio bot)
- Añadida la opción para la actualización forzada de la lista de canales desde /junglescript
- Arreglado aviso de oscam_info para que diga que no se están usando tunners
- Arreglado el tema de las líneas de oscam
- Se ha añadido la confirmación a más opciones
- Añadida opción para ver los usuarios conectados a oscam
- Añadido comando para ver el changelog
- Añadida la opción de parar streamproxy dentro de /streams
- Añadir ruta completa parametros.py en función add_variable_parametros
- Añadida la descarga del requirements.txt su instalación mediante pip en la update del bot

## [2.2.4b] - 10-05-2020

- Arreglados errores de conexión con Telegram
- Añadido ver log de junglescript
- Añadido ver log de junglebot
- Añadido meter rangos de IPs y DNS (ej: 192.168.1.* , prueba.duckdns.org...)

## [2.2.3] - 06-05-2020

- Fix para errores varios

## [2.2.2] - 05-05-2020

- Optimización de código

## [2.2.1] - 05-05-2020

- Arreglado error en el reinicio del propio bot
- Añadida opción de reiniciar el bot
- Arreglados errores con el login con password en blanco
- Captura de excepciones para evitar que se caiga el bot
- Arreglado error en la captura de imagen

## [2.2.0] - 02-05-2020

- Arreglados errores con el login de OpenWebif
- Añadido update del propio bot en las opciones /junglebot
- Arreglados errores con las rutas de los ficheros epg.dat

## [2.1.0] - 01-05-2020

- Renovación del bot a la versión 2.0 con aspecto visual con botones
- Añadidas nuevas funcionalidades para cambiar parámetros del deco desde el propio bot
- Añadida funcionalidad pystreamy, epg, grabaciones...

## [1.0.0] - 15-05-2019 

- Primera versión del bot (sin ipk asociado) 
