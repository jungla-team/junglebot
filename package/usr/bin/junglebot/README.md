![enter image description here](https://jungle-team.com/wp-content/uploads/2023/03/logobot.png)

[![Junglebot version](https://jungle-team.com/wp-content/uploads/2023/03/releases.png)](https://jungle-team.com/guia-junglebot-revolution-4-1-1/) [   ![Licencia Junglebot](https://jungle-team.com/wp-content/uploads/2023/03/licence.png)
](https://github.com/jungla-team/junglebot/blob/master/LICENSE) [![chat telegram](https://jungle-team.com/wp-content/uploads/2023/03/telegram.png)
](https://t.me/joinchat/R_MzlCWf4Kahgb5G) [![donar a jungle](https://jungle-team.com/wp-content/uploads/2023/03/donate.png)
](https://paypal.me/jungleteam)

Hemos realizado un bot telegram en python para poder gestionar receptores enigma2, el cual una vez probado no podrás dejar de usar.

Si deseas obtener ayudas asi como prestarlas sobre este desarrollo, asi como con enigma2 en general, tenemos  [grupo de Telegram](https://t.me/joinchat/R_MzlCWf4Kahgb5Gp) . ¡Únete a nosotros!

Si deseas estar a la ultima sobre novedades desarrolladas por jungle team [canal de Telegram noticias](https://t.me/+myB-5lmtSZ1hZDlk) .

## [](jungle-team#introduction)Introducción

JungleBot proporciona una interfaz de conexión con receptor enigma2, con el cual podremos realizar su gestion y recibir información del mismo. Es compatible con las versiones de Python **3.x+** , especialmente diseñado sobre **3.11+**.

Para su implementación se usa la  API de la  biblioteca `telebot`, ademas para recibir ciertas informaciones de uso del receptor se usa la API de `OpenWebif`

### [](jungleteam#note)Nota

JungleBot esta desarrollado bajo  `OpenATV 7.2` no es compatible con imagenes que usen `python 2.x` , en otras imagenes que usen `python 3.x`, puede ser compatible y funcional pero igual no estan disponibles todas las funciones.

## [](jungleteam#instalando)Instalando

Puede instalar o actualizar `jungleBot` previa instalación en el receptor del [Repositorio Paquetes jungle-team](https://jungle-team.com/jungle-feed-repositorio-paquetes-jungle-team/)

$ wget [http://tropical.jungle-team.online/script/jungle-feed.conf](http://tropical.jungle-team.online/script/jungle-feed.conf) -P /etc/opkg/

Una vez tenemos en nuestro receptor instalado el repositorio de paquetes, simplemente para instalar `junglebot`desde la fuente, ejecutaremos:

$ opkg update

$ opkg install enigma2-plugin-extensions-junglebot

## Inicio rápido

Tienes un manual completo de uso [Guia Junglebot](https://jungle-team.com/guia-junglebot-revolution-4-1-1/) que explica cómo se puede acceder al receptor enigma2 a través de `junglebot`.  No obstante para un inicio rapida simplemente debera introducir en el archivo `/usr/bin/junglebot/parametros.py` los datos relativos a su `Token` y `Chat_id` de su bot telegram creado.

Una vez introducidos, bastara reiniciar `junglebot` con el comando:

$ /etc/init.d/junglebot-daemon restart

## Obteniendo ayuda

Si los recursos mencionados anteriormente no responden a sus preguntas o dudas,  o te ha resultado muy complicado, tienes varias formas de obtener ayuda.

1.  Tenemos una comunidad donde se intenta que se ayudan unos a otros en nuestro [grupo de Telegram](https://t.me/joinchat/R_MzlCWf4Kahgb5G) . ¡Únete a nosotros! Hacer una pregunta aquí suele ser la forma más rápida de obtener respuesta y poder hablar directamente con los desarrolladores.
2.  Tambien puedes leer con detenimiento la [Guia avanzada de junglebot](https://jungle-team.com/guia-junglebot-revolution-4-1-1/) .

## contribuir

Junglebot esta desarrollado bajo codigo abierto, por lo que las contribuciones de todos los tamaños son bienvenidas para mejorar o ampliar las posibilidades de junglebot. También puede ayudar [informando errores o solicitudes de funciones a traves del grupo telegram](https://t.me/joinchat/R_MzlCWf4Kahgb5G) .

## [](jungleteam#donating)donando

De vez en cuando nos preguntan si aceptamos donaciones para apoyar el desarrollo. Si bien, mantener `junglebot`  es nuestro hobby y  pasatiempo, si tenemos un coste de mantenimiento de servidor de repositorios asi como [del blog enigma2](https://jungle-team.com/), por lo que si deseas colaborar en su mantenimiento sirvase de realizar [Donacion](https://paypal.me/jungleteam)

## [](junglebot#license)Licencia

Puede copiar, distribuir y modificar el software siempre que las modificaciones se describan y se licencien de forma gratuita bajo [LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html) . Los trabajos derivados (incluidas las modificaciones o cualquier cosa vinculada estáticamente a la biblioteca) solo se pueden redistribuir bajo LGPL-3.


