#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import time
import os
from os import path
import subprocess
from subprocess import *
import getopt
import json
import socket
import threading
import subprocess
sys.path.extend(["/opt/lib/python3.8/site-packages/"])
import telebot
from telebot import *
import requests
from requests.auth import HTTPDigestAuth
from io import StringIO
import re
from netaddr import *
import logging
import urllib
import i18n
from datetime import date
from crontab import CronTab
import psutil
import socket
import shlex

VERSION="4.1.5"   
CONFIG_FILE = '/usr/bin/junglebot/parametros.py' 
openatv="openatv"
new_version = False

alias_permitidos = {}
alias_desconoidentificacionos = []

g_autoftp_thread = None
g_autossh_thread = None
g_autostream_thread = None
g_autoram_thread = None
g_autotemp_thread = None
g_autoflash_thread = None

def execute_os_commands(commands, message = None, background = False):
    from subprocess import PIPE, Popen
   
    if not background:
        p = Popen(commands, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        return "{}\n{}".format(stdout, stderr)
    else:
        Popen(commands, close_fds=True)

def read_config_file (file_path):
    execute_os_commands("touch {}".format(file_path))
    config = []
    with open(file_path) as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split('=', 1)
                key = parts[0].strip()
                value = parts[1].strip()
                config.append((key, value))
            else:
                config.append(('#', line))
    return config

# Normalize config file
new_lines = []
with open(CONFIG_FILE) as f:
    lines = f.readlines()
    for line in lines:
        if line and line.startswith('#'):
            new_lines.append(line)
        else:
            for idx, part in enumerate(line.split('#')):
                if idx == 0:
                    new_lines.append(part)
                else:
                    new_lines.append("\n#{}".format(part))
with open(CONFIG_FILE, "w") as outfile:
    outfile.write(''.join(new_lines))

G_CONFIG = {
    'bot_token': '',
    'chat_id': '',
    'timer_bot': '30',
    'oscamserver': '',
    'log': '0',
    'rutalog': '/tmp/junglebot.log',
    'autostream': '0',
    'autossh': '0',
    'autoftp': '0',
    'locales_path': '/usr/bin/junglebot/locales',
    'locale': 'es',
    'ga': True,
    'autoram': '0',
    'autotemp': '0',
    'autoflash': '0'
}

G_CONFIG.update({ k.lower(): v.strip().strip('"').strip("'") for k,v in read_config_file(CONFIG_FILE) })
G_CONFIG['chat_id'] = int(G_CONFIG['chat_id'])
G_CONFIG['timerbot'] = int(G_CONFIG['timerbot'])
if G_CONFIG['log'] == '1':
    log_level = logging.DEBUG
else:
    log_level = logging.INFO
logging.basicConfig(filename=G_CONFIG['rutalog'],level=logging.DEBUG,format='%(asctime)s %(message)s')
logger = logging.getLogger('junglebot')

i18n.set('filename_format', '{locale}.{format}')
i18n.set('file_format', 'yml')
i18n.load_path.append(G_CONFIG['locales_path'])
i18n.set('locale', G_CONFIG['locale'])

bot = telebot.TeleBot(G_CONFIG['bot_token'], threaded=False)

def fill_command_list():
    command_list = []
    for i in g_menu:
        command_list.append({"command":i.name, "description":i.description})
    getMyCommands_url = "https://api.telegram.org/bot{}/getMyCommands".format(G_CONFIG["bot_token"])
    getMyCommands = json.loads(requests.get(getMyCommands_url).text)['result']
    if getMyCommands != command_list:
        setMyCommands_url = "https://api.telegram.org/bot{}/setMyCommands?commands={}".format(G_CONFIG["bot_token"], json.dumps(command_list))
        requests.get(setMyCommands_url)
    
class MenuOption:
    def __init__(self, name, description, command = None, params = [], info = ""):
        self.name = name
        self.description = description
        self.options = []
        self.command = command
        self.parent = None
        self.params = params
        self.info = info
        self.reset_params()
        
    def add_option(self, option):
        self.options.append(option)
        option.set_parent(self)
        return self
    
    def set_parent(self, parent):
        self.parent = parent
    
    def run_command(self):
        try:
            return self.command(*self.param_values)
        except Exception as e:
            return i18n.t('msg.unknown_error', error= str(e))

    def options(self):
        return self.options

    def description(self):
        return self.description

    def info(self):
        return self.info

    def callback_id(self):
        if self.parent:
            return "{}_{}".format(self.parent.callback_id(), self.name)
        else:
            return self.name 
    
    def find_by_callback_id(self, callback_id):
        if callback_id == self.callback_id():
            return self
        else:
            item = None
            for option in self.options:
                item = option.find_by_callback_id(callback_id)
                if item:
                    break
            return item

    def reset_params(self):
        self.param_values = []
        self.current_param = 0

    def has_all_params(self):
        return len(self.param_values) == len(self.params)
    
    def next_param(self):
        return self.params[self.current_param]

    def set_current_param(self, value):
        self.param_values.append(value)
        self.current_param += 1

def inicio_alias(uid):
    if uid in alias_permitidos:
        return alias_permitidos[uid]
    else:
        alias_desconoidentificacionos.append(uid)
        alias_permitidos[uid] = 0

def allowed(m):
    identificacion = m.chat.id
    if identificacion != G_CONFIG['chat_id']:
        bot.send_message(identificacion, i18n('msg.unauthorized'))
        return False
    else:
        return True 

def find_menu_option(command):
    global g_menu
    menu_option = None
    for item in g_menu:
        menu_option = item.find_by_callback_id(command)
        if menu_option:
            menu_option.reset_params()
            break
    return menu_option

def execute_command(chat_id, menu_option):
    global g_current_menu_option
    if menu_option == None:
        bot.send_message(chat_id, i18n('msg.command_not_found')) # TODO
    else:
        if g_current_menu_option != menu_option:
            g_current_menu_option = menu_option
        if g_current_menu_option.command:
            if g_current_menu_option.has_all_params():
                option = g_current_menu_option
                g_current_menu_option = None
                command_output = option.run_command() or ''
                send_large_message(chat_id, command_output.strip(), "{} (/{})".format(option.description, option.callback_id()))
            else:
                next_param = g_current_menu_option.next_param()
                if isinstance(next_param, list):
                    if next_param[0] == JB_BUTTONS:
                        jb_buttons= next_param[1]()
                        buttons = []
                        keyboard = types.InlineKeyboardMarkup()
                        keyboard.row_width = 2
                        for b in jb_buttons:
                            buttons.append(types.InlineKeyboardButton(text=b[1], callback_data="{}_{}".format(JB_BUTTONS,b[0])))
                        keyboard.add(*buttons)
                        bot.send_message(chat_id, i18n.t('msg.choose_option'), reply_markup=keyboard)
                elif (next_param == JB_CONFIRM):
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.row_width = 2
                    button1 = types.InlineKeyboardButton(text=i18n.t('msg.text_yes'), callback_data="{}_si".format(JB_CONFIRM))
                    button2 = types.InlineKeyboardButton(text=i18n.t('msg.text_no'), callback_data="{}_no".format(JB_CONFIRM)) 
                    keyboard.add(button1, button2)
                    bot.send_message(chat_id, i18n.t('msg.confirmation'), reply_markup=keyboard)
                else:
                    markup = types.ForceReply(selective=False)
                    bot.send_message(chat_id, i18n.t('msg.next_param', param=next_param),
                                    reply_markup=markup, parse_mode='Markdown')
        else:
            g_current_menu_option = None
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row_width = 2
            options = menu_option.options if (len(menu_option.options) % 2) == 0 else (menu_option.options + [None]) 
            pair_options = [(options[i],options[i+1]) for i in range(0,len(options),2)]
            for option1, option2 in pair_options:        
                button1 = types.InlineKeyboardButton(text=option1.description, callback_data=option1.callback_id())
                if option2:
                    button2 = types.InlineKeyboardButton(text=option2.description, callback_data=option2.callback_id())
                    keyboard.add(button1, button2)
                else:
                    keyboard.add(button1)
            if menu_option.info:
                bot.send_message(chat_id, menu_option.info)
            bot.send_message(chat_id, i18n.t('msg.click_button'), reply_markup=keyboard)

# DECORATORS
JB_CONFIRM='jb_confirm'
params_confirmation = [JB_CONFIRM]
JB_BUTTONS = 'jb_buttons'
params_buttons = ["jb_buttons"]

def with_confirmation(func):
    def wrapper_with_confirmation(*args, **kwargs):
        result = i18n.t("msg.operation_canceled")
        if len(args) > 0:
            args = list(args)
            ok = args.pop(0).lower()
            args = tuple(args)
            if ok == "si" or ok == "yes":
                result = func(*args, **kwargs)
        return result
    return wrapper_with_confirmation

# BOT handlers
@bot.message_handler(commands=['start'])
def command_inicio(m):
    if allowed(m):
        identificacion = m.chat.id
        alias_permitidos[identificacion] = 0
        time.sleep(1)
        bot.send_photo(identificacion, photo=open('/usr/bin/junglebot/images/logojungle.jpeg', 'rb'))
        bot.send_message(identificacion, i18n.t('msg.init', username=m.chat.username) + "\n")

@bot.message_handler(commands=['ayuda', 'help'])
def command_ayuda(m):
    global g_menu
    if allowed(m):
        identificacion = m.chat.id
        help = "" 
        telegram_url = "'https://t.me/joinchat/AFo2KEfzM5Tk7y3VgcqIOA'"
        brand = info_brand()
        for menu in g_menu:
            help = help + "/{} {}\n".format(menu.name, menu.description)
        bot.send_message(identificacion, i18n.t('msg.text_help', version=VERSION, username=m.chat.username, brand=brand, telegram_url=telegram_url) + help, parse_mode='html')
    
@bot.message_handler(func=lambda call:True)
def get_text_messages(message):
    global g_current_menu_option
    identificacion = message.chat.id
    bot.send_chat_action(identificacion, 'typing')
    if allowed(message):
        try:
            if message.text[:1] == '/':
                print("Processing command {}".format(message.text))
                command = message.text.strip()[1:]
                menu_option = find_menu_option(command)
                execute_command(identificacion, menu_option)
            else:
                if g_current_menu_option:
                    g_current_menu_option.set_current_param(message.text)
                    execute_command(identificacion, g_current_menu_option)
        except Exception as e:
            bot.send_message(identificacion, i18n.t('msg.unknown_error', error=str(e)))

@bot.callback_query_handler(func=lambda call:True)
def callback_menu(call):
    identificacion = call.message.chat.id # call.message.text, mensaje que se imprimio, puede valer para saber el menu
    bot.send_chat_action(identificacion, 'typing')
    print("Processing command {}".format(call.data))
    if allowed(call.message):
        try:
            data = call.data
            if data.startswith('jb_'):
                parts = data.split('_')
                value = data[len("{}_{}_".format(parts[0], parts[1])):]
                global g_current_menu_option
                if g_current_menu_option:
                    g_current_menu_option.set_current_param(value)
                    execute_command(identificacion, g_current_menu_option)
            else:
                command = call.data
                menu_option = find_menu_option(command)
                execute_command(identificacion, menu_option)
        except Exception as e:
            bot.send_message(identificacion, i18n.t('msg.unknown_error', error=str(e)))
            
def check_version():
    global new_version
    if os.path.isfile("/run/opkg.lock"):
        execute_os_commands("killall opkg")
    execute_os_commands("opkg update")
    time.sleep(5)
    hay_new_version_bot = int(getoutput("opkg list-upgradable | grep 'enigma2-plugin-extensions-junglebot ' | wc -l"))
    if hay_new_version_bot > 0:
        new_version = True
        new_version_bot = getoutput("opkg list-upgradable | grep 'enigma2-plugin-extensions-junglebot '").split(' ')[4]
        logger.info('Existe nueva versión de Junglebot {}'.format(new_version_bot))
        bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.new_version', version=new_version_bot))

def machine_id():
    return getoutput("cat /etc/machine-id")

# COMMANDS

# GHOSTREAMY
def ghostreamy_stop():
    return getoutput("/etc/init.d/ghostreamy stop")

def ghostreamy_start():
    return getoutput("/etc/init.d/ghostreamy start")

def ghostreamy_restart():
    return getoutput("/etc/init.d/ghostreamy restart")

def ghostreamy_status():
    running = hay_ghostreamy()
    if running > 0:
        return i18n.t('msg.ghostreamy_started')
    else:
        return i18n.t('msg.ghostreamy_stopped')

def hay_ghostreamy():
    if os.path.isfile("/etc/init.d/ghostreamy"):
        return int(getoutput("/etc/init.d/ghostreamy status | grep running | wc -l"))
    else:
        return 0

def ghostreamy_log():
    get_file("/var/log/ghostreamy.log")
    
 
@with_confirmation  
def ghostreamy_install():
    command = "opkg update"
    execute_os_commands(command)
    hay_ghostreamy = int(getoutput("opkg list-installed | grep enigma2-plugin-extensions-ghostreamy | wc -l"))
    if hay_ghostreamy > 0:
        commands = "opkg upgrade enigma2-plugin-extensions-ghostreamy-{}".format(info_arquitecture())
        message = "ghostreamy esta instalado. Upgrading si procede..."
    else:
        commands = "opkg install enigma2-plugin-extensions-ghostreamy-{}".format(info_arquitecture())
        message = "Instalando Ghostreamy..."
    output = getoutput(commands)
    return f"{message}\n{output}"

@with_confirmation
def ghostreamy_uninstall():
    commands = "opkg remove --force-remove enigma2-plugin-extensions-ghostreamy-{}".format(info_arquitecture())
    return getoutput(commands)

def ghostreamy_version():
    commands = "opkg list-installed | grep ghostreamy | cut -d ' ' -f3"
    return getoutput(commands)

def config(file_path):
    return getoutput("cat {}".format(file_path))

def set_value(file_path, param, new_value):
    execute_os_commands("touch {}".format(file_path))
    new_lines = []
    lines = read_config_file(file_path)
    if len(lines) == 0:
        new_lines.append("{}={}".format(param, new_value))
    found = False
    for (key, value) in lines:
        if key != '#' :
            if key == param:
                value = new_value
                found = True
            new_lines.append("{}={}".format(key, value))
        else:
            new_lines.append(value)
    if not found:
        new_lines.append("{}={}".format(param, new_value))
    with open(file_path, "w") as outfile:
        outfile.write("\n".join(new_lines))
    return config(file_path)

def set_value_parameters(param, new_value):
    file_path = "/usr/bin/junglebot/parametros.py"
    set_value(file_path, param, new_value)
    send_large_message(G_CONFIG['chat_id'], config(file_path))
    junglebot_restart()

def get_file(filepath):
    if os.path.isfile(filepath):
        bot.send_document(G_CONFIG['chat_id'], open(filepath, 'r'))
    else:
        bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.file_notfound', file=filepath))
    return ''

@bot.message_handler(content_types=['document', 'photo', 'audio', 'video', 'voice'])
def file_upload(message):
    try:
        try:
            save_dir = message.caption
        except:
            save_dir = os.getcwd()
            s = i18n.t('msg.dir_notexist', file=save_dir)
            bot.send_message(message.chat.id, str(s))
        file_name = message.document.file_name
        file_id = message.document.file_name
        file_id_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_id_info.file_path)
        src = file_name
        with open(save_dir + "/" + src, 'wb') as new_file:
            new_file.write(downloaded_file)
        bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.file_upload') + " " + str(save_dir) + "/" + str(file_name))
    except Exception as ex:
        if message.caption:
            bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.dir_notexist', file=message.caption))
        else:
            bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.dir_empty'))

def file_download(filepath):
    filepath = "/" + filepath
    if os.path.isfile(filepath):
        if os.path.getsize(filepath) > 0:
            bot.send_document(G_CONFIG['chat_id'], open(filepath, 'rb'))
        else:
            bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.file_empty'))
    else:
        bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.file_notfound', file=filepath))
    return ''

def inicializar_intrusos():
    file_path = "/tmp/intrusos.txt"
    if os.path.exists(file_path):
        execute_os_commands("cat /dev/null > {}".format(file_path))
        logger.info("Vaciando fichero de intrusos")
    else:
        execute_os_commands("touch {}".format(file_path))
        logger.info("Creando fichero de intrusos")

def ips_intrusos():
    intrusos = IPSet()
    with open ("/tmp/intrusos.txt", 'r') as f:
        for linea in f:
            linea = linea.rstrip('\n')
            if len(linea) > 0:
                try:
                    if valid_ipv4(linea) or valid_glob(linea):
                        intrusos.add(IPGlob(linea))
                    else:
                        ip = socket.gethostbyname(linea)
                        if valid_ipv4(ip):
                            intrusos.add(ip)                            
                except Exception as e:
                    continue
    f.close()
    return intrusos

def addipintruso(intruso):
    fichero = "/tmp/intrusos.txt"
    with open (fichero,'a') as f:
        f.write(intruso + "\n")
        logger.info("Añadido intruso " + intruso)

def stream_delintruso(intruso):
    lines = None
    fichero = "/tmp/intrusos.txt"
    with open(fichero, 'r') as file:
        lines = file.readlines()
    with open (fichero, 'w') as f:
        for line in lines:
            if line.strip("\n") != intruso:
                f.write(line)
    junglebot_restart()
    return intrusos()

def stream_intrusos():
    fichero = "/tmp/intrusos.txt"
    if os.path.isfile(fichero):
        return getoutput("cat " + fichero).split('\n')
    else:
        return []

def intrusos():
    fichero = "/tmp/intrusos.txt"
    items = stream_intrusos()
    if len(items) > 0:
        return '\n'.join(items)
    else:
        return i18n.t('msg.file_notfound', file=fichero)

def ips_autorizadas():
    autorizadas = IPSet()
    with open ("/usr/bin/junglebot/amigos.cfg", 'r') as f:
        for linea in f:
            linea = linea.rstrip('\n')
            if len(linea) > 0:
                try:
                    if valid_ipv4(linea) or valid_glob(linea):
                        autorizadas.add(IPGlob(linea))
                    else:
                        ip = socket.gethostbyname(linea)
                        if valid_ipv4(ip):
                            autorizadas.add(ip)                            
                except Exception as e:
                    continue
    f.close()
    return autorizadas

def amigos_autorizados():
    amigos = []
    with open ("/usr/bin/junglebot/amigos.cfg", 'r') as f:
        for linea in f:
            linea = linea.rstrip('\n')
            if len(linea) > 0:
                try:
                    es_ghost = linea.split(":")[0]
                    if es_ghost == "ghostreamy":
                        amigos.append(linea.split(":")[1])
                except Exception as e:
                    continue
    f.close()
    return amigos

def controlstream_background():
    while True:
        ip_autorizadas = ips_autorizadas()
        amigo_autorizados = amigos_autorizados()
        intrusos = ips_intrusos()
        output = []
        #### Sacar streams
        j = webif_api("about?")
        lineas = j['info']['streams']  
        ip_deco = obtener_ip_deco()
        for linea in lineas:	
            ip = linea['ip'].replace("::ffff:", "")
            if ip_deco != ip and ip != "::1":
                if ip and not ip in ip_autorizadas and not ip in intrusos:
                    addipintruso(ip)
                    output.append(i18n.t('msg.control_access') + linea['ip'].replace("::ffff:", "") + ": " + linea['name'])
        ### Sacar streams ghostreamy
        if os.path.exists("/tmp/ghostreamy.status"):
            for linea in open('/tmp/ghostreamy.status'):
                user_stream = linea.split("##")[0]
                ip_stream = linea.split("##")[1]
                trans_stream = linea.split("##")[2]
                canal_stream = linea.split("##")[3]
                if ip_stream in ip_autorizadas or user_stream in amigo_autorizados:
                    logger.info("Amigo autorizado para stream: " + ip_stream + ": " + user_stream + ": " + canal_stream + ": " + trans_stream)
                else:
                    if not ip_stream in intrusos:
                        addipintruso(ip_stream)
                        intrusos = ips_intrusos()
                        output.append(i18n.t('msg.control_access') + ip_stream + ": " + user_stream + ": " + canal_stream + ": " + trans_stream)
        if output:
            logger.info("\n".join(output))
            bot.send_message(G_CONFIG['chat_id'], "\n".join(output))
        time.sleep(G_CONFIG['timerbot'])

def controlssh_background():
    while True:
        ip_autorizadas = ips_autorizadas()
        intrusos = ips_intrusos()
        conexiones = getoutput("netstat -tan | grep \:'22 ' | grep ESTAB | awk '{print $5}' |sed -e 's/::ffff://'| cut -d: -f1 | sort")      
        conexiones = conexiones.split('\n')
        output = []
        for linea in conexiones:
            if linea and not linea in ip_autorizadas and not linea in intrusos:
                addipintruso(linea)
                intrusos = ips_intrusos()
                output.append(i18n.t('msg.control_ssh_unauthorized') + " = " + linea)
        if output:
            logger.info(output)
            bot.send_message(G_CONFIG['chat_id'], "\n".join(output))
        time.sleep(G_CONFIG['timerbot'])
        
def controlftp_background():
    while True:
        ip_autorizadas = ips_autorizadas()
        intrusos = ips_intrusos()
        conexiones = getoutput("netstat -tan | grep \:'21 ' | grep ESTAB | awk '{print $5}' |sed -e 's/::ffff://'| cut -d: -f1 | sort") 
        conexiones = conexiones.split('\n')
        output = []
        for linea in conexiones:
            if linea and not linea in ip_autorizadas and not linea in intrusos:
                addipintruso(linea)
                intrusos = ips_intrusos()
                output.append(i18n.t('msg.control_ftp_unauthorized') + " = " + linea) 
        if output:
            logger.info(output)
            bot.send_message(G_CONFIG['chat_id'], output)
        time.sleep(G_CONFIG['timerbot'])   

def controlram_background():
    while True:
        ram = info_ram()
        if int(ram) >= 80:
            logger.info('controlram_background - ' + i18n.t('msg.control_ram_background'))
            bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.control_ram_background'))
        time.sleep(G_CONFIG['timerbot'])

def controltemp_background():
    while True:
        temperatura = info_temperatura()
        if int(temperatura) >= 90:
            logger.info('controltemp_background - ' + i18n.t('msg.control_temp_background'))
            bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.control_temp_background'))
        time.sleep(G_CONFIG['timerbot'])

def controlflash_background():
    while True:
        temp = len(diskSpace()[3])
        espacio_ocupado = diskSpace()[3]
        espacio_ocupado = espacio_ocupado[:temp - 1]
        if int(espacio_ocupado) >= 90:
            logger.info('controlflash_background -' + i18n.t('msg.control_flash_background'))
            bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.control_flash_background'))
        time.sleep(G_CONFIG['timerbot'])
        
#INFO BOX
def info_brand():
    j = webif_api("about?")
    if j['info']['brand'] and j['info']['model']:
        return "<b><i>" + j['info']['brand'] + " " + j['info']['model'] + "</i></b>"

# INFO HD
def obtener_ip_deco():
    j = webif_api("about?")
    lineas = j['info']['ifaces']
    for linea in lineas:
        if linea['gw'] != "0.0.0.0" and ("eth" in linea['name'] or "wlan" in linea['name']):
            return linea['ip'].strip()

def oscam_get(path):
    emuoscam_conf = oscam_config_dir() + '/oscam.conf'
    USEROSCAM = getoutput("grep httpuser " + emuoscam_conf).split("=")
    USEROSCAM = USEROSCAM[1].strip() if 1 < len(USEROSCAM) else None
    PASSOSCAM = getoutput("grep 'httppwd' " + emuoscam_conf).split("=")
    PASSOSCAM = PASSOSCAM[1].strip() if 1 < len(PASSOSCAM) else None
    PUERTOOSCAM = getoutput("grep 'httpport' " + emuoscam_conf).split("=")
    PUERTOOSCAM = PUERTOOSCAM[1].strip() if 1 < len(PUERTOOSCAM) else "8081"
    s = requests.Session()
    auth = HTTPDigestAuth(USEROSCAM, PASSOSCAM)
    http = "http://127.0.0.1:{}/{}".format(PUERTOOSCAM, path)
    try:
        response = s.get(http, auth=auth, params={}, timeout=5)
        return response.text
    except Exception as e:
        logger.error("Unknown error: " + str(e))
        return None

def cccam_get(path):
    data = do_get("http://127.0.0.1:{}/{}".format(16001, path))
    return data

def webif_url():
    comando = "http://127.0.0.1"       
    return comando

def webif_get(path):
    s = requests.Session()
    auth = {}
    http = "http://127.0.0.1"
    param = {}
    response = s.get(http, auth=auth, params=param)
    data = requests.get("{}/web/{}".format(webif_url(), path))
    return data.text

def webif_api(path):
    data = do_get("{}/api/{}".format(webif_url(), path), retries=5)
    return json.loads(data.text)


def do_get(url, retries=0):
    resp = None
    try:
        resp = requests.get(url)
    except Exception as e:
        if retries:
            logger.error( "Error open url: {}, retries: {}, {}".format(url, retries, e.args))
            time.sleep(10)
            return do_get(url, retries - 1)
    return resp


if G_CONFIG['rutalog'] == 1:
    import logging
    logging.basicConfig(filename=G_CONFIG['rutalog'],level=logging.DEBUG)

def send_large_message(chat_id, output, message = None):
    try:
        if message:
            bot.send_message(chat_id, message)
        for text in util.split_string(output, 3000):
            bot.send_message(chat_id, "```\n{}\n```".format(text), parse_mode='Markdown')
    except Exception as e:
        logger.exception(e)
        return i18n.t("msg.unknown_error", error=str(e))

def start_autostream():
    global g_autostream_thread
    if G_CONFIG['autostream'] == '1' and not g_autostream_thread:
        distro = enigma_distro()
        g_autostream_thread = threading.Thread(target=controlstream_background)
        g_autostream_thread.start()
        logger.info("Autostream iniciado")
        return i18n.t("msg.autostream_started")

def start_autossh():
    global g_autossh_thread
    if G_CONFIG['autossh'] == '1' and not g_autossh_thread:
        g_autossh_thread = threading.Thread(target=controlssh_background)
        g_autossh_thread.start()
        logger.info("Autossh iniciado")
        return i18n.t("msg.autossh_started")
    
def start_autoftp():
    global g_autoftp_thread
    if G_CONFIG['autoftp'] == '1' and not g_autoftp_thread:
        g_autoftp_thread = threading.Thread(target=controlftp_background)
        g_autoftp_thread.start() 
        logger.info("Autoftp iniciado")
        return i18n.t("msg.autoftp_started")

def start_autoram():
    global g_autoram_thread
    if G_CONFIG['autoram'] == '1' and not g_autoram_thread:
        g_autoram_thread = threading.Thread(target=controlram_background)
        g_autoram_thread.start()
        logger.info("Autoram iniciado")
        return i18n.t("msg.autoram_started")
        
def start_autotemp():
    global g_autotemp_thread
    if G_CONFIG['autotemp'] == '1' and not g_autotemp_thread:
        g_autotemp_thread = threading.Thread(target=controltemp_background)
        g_autotemp_thread.start()
        logger.info("Autotemp iniciado")
        return i18n.t("msg.autotemp_started")

def start_autoflash():
    global g_autoflash_thread
    if G_CONFIG['autoflash'] == '1' and not g_autoflash_thread:
        g_autoflash_thread = threading.Thread(target=controlflash_background)
        g_autoflash_thread.start()
        logger.info("Autoflash iniciado")
        return i18n.t("msg.autoflash_started")
        
# INFO
def diskSpace():
    p = os.popen("df -h /")
    i = 0
    while 1:
        i += 1
        line = p.readline()
        if i == 2:
            return(line.split()[1:5])

def info_channel():
    j1 = webif_api("about?")
    j = webif_api("signal")
    output = []
    if j['snr']:
        output.append("CHANNEL: " + j1['service']['name'])
        output.append("SNR: " + str(j['snr']) + "%")
        output.append("AGC: " + str(j['agc']) + "%")
    else:
        output.append(i18n.t('msg.not_signal'))
    return "\n".join(output)

def enigma_distro():
    distro = getoutput("cat /etc/opkg/all-feed.conf | cut -d'-' -f1 | awk '{ print $2 }'")
    if distro:
        imagedistro = distro 
    return imagedistro

def enigma_version():          
    j = webif_api("about?")
    imagedistro = j['info']['imagedistro']
    imagever = j['info']['imagever']
    return imagedistro + " " + imagever             

def system_info():
    output = ["* Imagen: " + enigma_version()]
    output.append("* " + info_uptime())
    output.append("* FLASH")
    output.append("  Total: %s" % diskSpace()[0])
    output.append("  Used: %s" % diskSpace()[1])
    output.append("  Available: %s" % diskSpace()[2])
    output.append("* RAM")
    output.append("  MemTotal:  %s" % getoutput("free | grep Mem  | awk '{ print $2 }'") + " kb")
    output.append("  MemFree:  %s" % getoutput("free | grep Mem  | awk '{ print $4 }'") + " kb")
    output.append("  MemAvailable:  %s" % getoutput("free | grep Mem  | awk '{ print $7 }'") + " kb")
    output.append(i18n.t('msg.info_ram') + ": " + str(round(info_ram(),2)) + "%")
    output.append("* CPU")
    output.append("  %s" % info_cpu())
    output.append("  %s" % i18n.t('msg.info_temp') + " " + str(info_temperatura()) + "°C")
    return "\n".join(output)

def info_arquitecture():
    es_arm = int(getoutput("uname -m | grep arm | wc -l"))
    if es_arm == 1:
        return "arm"
    else:
        return "mips"

def info_ram():
    memAvailable = float(getoutput("free | grep Mem | awk '{ print $7 }'"))
    memTotal = float(getoutput("free | grep Mem | awk '{ print $2 }'"))
    menusada = float(getoutput("free | grep Mem | awk '{ print $3 }'"))
    porcentajeMemoria = (menusada / memTotal) * 100
    return porcentajeMemoria

def info_cpu():
    line = getoutput("grep 'cpu ' /proc/stat | awk '{print($2+$4)*100/($2+$4+$5)}'")
    return i18n.t('msg.info_cpu') + ": " + line + "%"

def info_top():
    line = getoutput("top -n 1 -b | sed -n '7,17 p'")
    return i18n.t('msg.info_top') + ":\n\n" + line

def info_conexiones():
    line = getoutput("netstat -tp | grep ESTAB | awk '{print $5,$7}'")
    return i18n.t('msg.info_connections') + ":\n\n" + line
            
def info_uptime():
    line = getoutput("uptime -p")
    return i18n.t('msg.info_uptime') + ":" + line

def info_hostname():
    return getoutput("cat /etc/hostname")

def info_mac():
    line = getoutput("LANG=C ip link show | awk '/link\/ether/ {print $2}'")
    return i18n.t('msg.info_mac') + ":\n" + line
    
def info_machineid():
    return i18n.t('msg.info_machineid') + ":\n" + machine_id()

def info_ip():
    return getoutput("curl -s ifconfig.me")

def info_tarjetared():
    line = getoutput("ethtool eth0").split("Speed: ")[1]
    return i18n.t('msg.info_networkcard') + ":\n" + line
    
def list_speedtest():
    lista = getoutput("/usr/bin/speedtest-cli --list")
    return lista

def info_speedtest_options():
    result = []
    items = []
    for item in list_speedtest().split('\n')[1:]:
        m = re.search('(\d+)\)(.+)\(.+\)\s\[(\d+.\d+)', item)
        items.append((m.group(1), m.group(2), m.group(3)))
    seen = set()
    seen_add = seen.add
    items = [i for i in items if i[2] not in seen and not seen_add(i[2])]
    for i in items[:10]:
        result.append((i[0], "{} [{} km]".format(i[1], i[2])))
    return result

def info_speedtest(hostspeed):
    try:
        bin_velocidad = "/usr/bin/speedtest-cli"
        command = bin_velocidad + " --share --simple " + " --server "+ hostspeed +  " | awk 'NR==4' | awk '{print $3}'"
        velocidad = getoutput(command)
        bot.send_photo(G_CONFIG['chat_id'], photo=velocidad)
    except:
        return i18n.t('msg.info_speedtest_error')
        
def network_status():
    output = ["* Hostname: {}".format(info_hostname())]
    output.append("* IP local: {}".format(obtener_ip_deco()))
    output.append("* Public IP: {}".format(info_ip()))
    output.append("* " + info_mac())
    output.append("* " + info_tarjetared())
    return "\n".join(output)
    
def info_temperatura():
    temperatura = ""
    tempinfo = ""
    if path.exists('/proc/stb/sensors/temp0/value'):
        f = open('/proc/stb/sensors/temp0/value', 'r')
        tempinfo = f.read()
        f.close()
    elif path.exists('/proc/stb/fp/temp_sensor'):
        f = open('/proc/stb/fp/temp_sensor', 'r')
        tempinfo = f.read()
        f.close()
    elif path.exists('/proc/stb/sensors/temp/value'):
        f = open('/proc/stb/sensors/temp/value', 'r')
        tempinfo = f.read()
        f.close()
    if tempinfo and int(tempinfo.replace('\n', '')) > 0:
        temperatura = tempinfo.replace('\n', '').replace(' ', '')

    tempinfo = ""
    if path.exists('/proc/stb/fp/temp_sensor_avs'):
        f = open('/proc/stb/fp/temp_sensor_avs', 'r')
        tempinfo = f.read()
        f.close()
    elif path.exists('/proc/stb/power/avs'):
        f = open('/proc/stb/power/avs', 'r')
        tempinfo = f.read()
        f.close()
    elif path.exists('/sys/devices/virtual/thermal/thermal_zone0/temp'):
        try:
            f = open('/sys/devices/virtual/thermal/thermal_zone0/temp', 'r')
            tempinfo = f.read()
            tempinfo = tempinfo[:-4]
            f.close()
        except:
            tempinfo = ""
    elif path.exists('/proc/hisi/msp/pm_cpu'):
        try:
            for line in open('/proc/hisi/msp/pm_cpu').readlines():
                line = [x.strip() for x in line.strip().split(":")]
                if line[0] in ("Tsensor"):
                    temp = line[1].split("=")
                    temp = line[1].split(" ")
                    tempinfo = temp[2]
                    if getMachineBuild() in ('u41', 'u42', 'u43', 'u45'):
                        tempinfo = str(int(tempinfo) - 15)
        except:
            tempinfo = ""
    if tempinfo and int(tempinfo.replace('\n', '')) > 0:
        temperatura = tempinfo.replace('\n', '').replace(' ', '')
#    if temperatura:
#        temperatura = int(filter(str.isdigit, temperatura))
    return temperatura                       

def info_check_duckdns_ip(host):
    public_ip = info_ip()
    args = { 'host': host }
    host_ip = requests.get(url = 'https://check-port.duckdns.org/info_hostname', params = args, verify = False).text.replace('"','')
    if public_ip == host_ip:
        return i18n.t('msg.info_duckdns_ok', host=host, public_ip=public_ip)
    else:
        return i18n.t('msg.info_duckdns_ko', public_ip=public_ip, host=host, host_ip=host_ip)
    
def info_check_open_port(host,port):
    args = { 'host': host, 'port': port }
    is_open = int(requests.get(url = 'https://check-port.duckdns.org/info_check_open_port', params = args, verify = False).text)
    if is_open == 0:
        return i18n.t('msg.info_port_open', host=host, port=port)
    else:
        return i18n.t('msg.info_port_closed', host=host, port=port)

# COMMAND   

def command_update():
    line = getoutput("opkg update")
    return i18n.t('msg.command_update') + "\n\n" + line

def command_stopstream():
    line = getoutput("killall -9 streamproxy")
    return i18n.t('msg.command_stopstream') + " \n" + line

@with_confirmation
def command_upgrade():
    line = getoutput("opkg update && opkg upgrade && reboot")
    return i18n.t('msg.command_upgrade') + "\n\n" + line

@with_confirmation
def command_restaurar():
    line = getoutput("rm -r /etc/enigma2 && reboot")
    return i18n.t('msg.command_restore') + "\n\n" + line
    
@with_confirmation
def command_resetpass():
    line = getoutput('/usr/bin/passwd -d root')
    return i18n.t('msg.command_resetpass') + "\n" + line

def command_freeram():
    line = getoutput("sync; echo 3 > /proc/sys/vm/drop_caches ")
    return i18n.t('msg.command_freeram') + "\n" + line

def command_runcommand(command):
    salida = getoutput(command)
    if not salida.isspace():
        return salida
    else:
        return i18n.t('msg.command_execute_success')

def backup_jungle_configs():
    today = date.today().strftime("%d%m%Y")
    backup_file = "/tmp/backup_{}.zip".format(today)
    comando1 = "zip -9r {} /usr/bin/enigma2_pre_start.conf /etc/tuxbox/config/oscam-* /etc/tuxbox/config/ncam /etc/CCcam.cfg /usr/bin/junglebot/parametros.py /usr/bin/junglebot/amigos.cfg /usr/bin/junglebot/ips_bloqueadas.txt /etc/enigma2/ghostreamy*".format(backup_file)
    execute_os_commands(comando1)
    backup_zip = open(backup_file, 'rb')
    bot.send_document(G_CONFIG['chat_id'], backup_zip)
    comando2 = "sleep 2 & rm -f {}".format(backup_file)
    execute_os_commands(comando2)
    return ''
    
# STREAM
def cotillearamigos():
    count_streams = 0
    output = []
    distro = enigma_distro()
    j = webif_api("about?")
    ip_deco = obtener_ip_deco()
    if j['info']['streams']:
        for s in j['info']['streams']:
            count_streams = count_streams + 1
            ip_cliente = s['ip'].replace("::ffff:","")
            if ip_deco != ip_cliente and "127.0." not in ip_cliente and ip_cliente != "::1":
                output.append(ip_cliente + ": " + s['name'])               
    ### Sacar streams ghostreamy
    if os.path.exists("/tmp/ghostreamy.status"):
        for linea in open('/tmp/ghostreamy.status'):
            count_streams = count_streams + 1
            user_stream = linea.split("##")[0]
            ip_stream = linea.split("##")[1]
            trans_stream = linea.split("##")[2]
            canal_stream = linea.split("##")[3]
            output.append(ip_stream + ": " + user_stream + ": " + canal_stream + ": " + trans_stream)
    if count_streams == 0:
        output.append(i18n.t('msg.streams_notexist'))
    return "\n".join(output)

def stream_amigos():
    fichero = "/usr/bin/junglebot/amigos.cfg"
    if os.path.isfile(fichero):
        file = open(fichero).read()
        return file.splitlines()
    else:
        return []

def amigos():
    fichero = "/usr/bin/junglebot/amigos.cfg"
    items = stream_amigos()
    if len(items) > 0:
        return '\n'.join(items)
    else:
        return i18n.t('msg.file_notfound', file=fichero)

def stream_addamigo(amigo):
    with open ('/usr/bin/junglebot/amigos.cfg','a') as f:
        f.write(amigo + "\n")
    junglebot_restart()
    return amigos()
	
def stream_delamigo(amigo):
    lines = None
    with open('/usr/bin/junglebot/amigos.cfg', 'r') as file:
        lines = file.readlines()
    with open ('/usr/bin/junglebot/amigos.cfg', 'w') as f:
        for line in lines:
            if line.strip("\n") != amigo:
                f.write(line)
        junglebot_restart()
    return amigos()

@with_confirmation
def stream_autocheck():
    G_CONFIG['autostream'] = '1'
    return start_autostream()

# CCCAM
def addlinea_cccam(cline):
    cccam_cfg = '/etc/CCcam.cfg'
    if not os.path.exists(cccam_cfg):
        os.mknod(cccam_cfg)
    params = cline.split(" ")
    if len(params) != 5 or params[0] != "C:":
        return i18n.t('msg.cline_bad_format')
    clines = [cline]

    with open(cccam_cfg, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line != cline:
                clines.append(line)
    data = '\n'.join(clines)
    with open (cccam_cfg,'w') as f:
        f.write(data + "\n")
    return cccam_cfg + "\n" + data

def addlinea_oscam(protocol, label, cline):
    response = oscam_get('status.html')
    if not response:
        return i18n.t('msg.oscam_conn_error')
    oscam_cfg = oscam_config_dir() + "/oscam.server"
    if not os.path.exists(oscam_cfg):
        return i18n.t('msg.file_notfound', file=oscam_cfg) 
    params = cline.split(" ")
    if len(params) != 5 or params[0] != "C:":
        return i18n.t('msg.cline_bad_format')
    with open (oscam_cfg,'a') as file:
        file.write("\n" + "[reader]" + "\n"
                "label                         = " + label.replace(" ", "") + "\n"
                "protocol                      = " + protocol + "\n"
                "device                        = " + params[1] + "," + params[2] + "\n"
                "user                          = " + params[3] + "\n"
                "password                      = " + params[4] + "\n"
                "inactivitytimeout             = 30" + "\n"
                "fallback                      = 1" + "\n"
                "group                         = 1" + "\n"
                "cccversion                    = 2.3.2" + "\n"
                "ccckeepalive                  = 1" + "\n")
    oscam_restart()
    return oscam_status()

def estado_clines_oscam():
    response = oscam_get('status.html')
    if not response:
        return i18n.t('msg.oscam_conn_error')
    lines = response.split("\n")
    output = []
    started = False
    ip = None
    connect = None
    port = None
    name = None
    table = False
    for line in lines:
        if table:
            if line.find('<TD CLASS="statuscol4"') >= 0:
                started = True
                name = re.split('[<>]', line)[4]
            if line.find('<TD CLASS="statuscol7">') >= 0:
                ip = re.split('[<>]', line)[2]
            if line.find('<TD CLASS="statuscol8">') >= 0:
                port = re.split('[<>]', line)[2]
            if line.find('<TD CLASS="statuscol16">') >= 0:
                connect = re.split('[<>]', line)[2]
                output.append(i18n.t('msg.cline_info', name=name, ip=ip, port=port, connect=connect))
                started = False
                ip = None
                connect = None
                port = None
                name = None
        if line.find('<tbody id="tbodyp">') >= 0:
            table = True
        if line.find('</tbody>') >= 0:
            table = False
        
    return "\n".join(output)
    
def oscam_config_dir():
    oscamdir = ''
    oscam_version = '/tmp/.oscam/oscam.version'
    if os.path.exists(G_CONFIG['oscamserver']) and os.path.isdir(os.path.dirname(G_CONFIG['oscamserver'])):
        oscamdir = os.path.dirname(G_CONFIG['oscamserver'])
    elif os.path.exists(oscam_version):
        oscamdir = getoutput("grep -i ConfigDir {}".format(oscam_version)).split("ConfigDir: ")
        oscamdir = oscamdir[1].strip() if 1 < len(oscamdir) else ''
    else:
        logger.info("No se encuentra el directorio de configuracion de OSCAM")
    return oscamdir

def emu_init_command():
    distro = enigma_distro()
    openspa_script = getoutput("ls -t /usr/script/Oscam* | head -1")
    all_script = "/etc/init.d/softcam"
    if os.path.exists(openspa_script) and distro == "openspa":
        return openspa_script
    elif os.path.exists(all_script) and (distro == "openatv" or distro == "openpli" or distro == "teamblue"):
        return all_script
    else:
        return None

def oscam_info():
    response = oscam_get('status.html')
    if not response:
        return i18n.t('msg.oscam_conn_error')
    archivo = "/tmp/ecm.info"
    output = i18n.t('msg.oscam_tunner')
    if os.path.isfile(archivo):
        output = getoutput("cat " + archivo)
    return "\n" + i18n.t('msg.emu_info_sharing') + ":\n" + output

def cccam_status():
    response = cccam_get('servers')
    if not response:
        return i18n.t('msg.cccam_stopped')
    else:
        output = []
        lines = response.text.split("\n")
        for line in lines:
            if line.find('<H2') >= 0:
                output.append(re.split('[<>]', line)[14])
            if line.startswith('|'):
                data = line.split('|')
                if not data[1].startswith(" Host "):
                    output.append("* Cline: {} | {} | {}".format(data[1], data[3], data[4]))
        archivo = "/tmp/ecm.info"
        if os.path.isfile(archivo):
            output.append("\n" + i18n.t('msg.emu_info_sharing') + ":\n")
            output.append(getoutput("cat " + archivo))
        return "\n".join(output)
    
def emucam_status():
    if cccam_get('servers'):
        return cccam_status()
    elif oscam_get('status.html'):
        return oscam_status()
    else:
        return i18n.t("msg.emu_stopped")

def oscam_status():
    response = oscam_get('status.html')
    if not response:
        return i18n.t("msg.oscam_stopped")
    else:
        output = []
        lines = response.split("\n")
        user = None
        status = None
        table = False
        ip = False
        for line in lines:
            if table:
                if line.find('<TD CLASS="statuscol4"') >= 0:
                    user = re.split('[<>]', line)[4]
                if line.find('<TD CLASS="statuscol7"') >= 0:
                    ip = re.split('[<>]', line)[2]
                if line.find('<TD CLASS="statuscol16">') >= 0:
                    status = re.split('[<>]', line)[2]
                    output.append(i18n.t('msg.user_connected', user=user, ip=ip, status=status))
                    user = None
                    status = None
                    ip = None
            if line.find('<tbody id="tbodyc">') >= 0:
                table = True
            if line.find('</tbody>') >= 0:
                table = False
            if line.find('<title>OSCam') >= 0:
                parts = re.split('[<>]', line)
                version = "Version {}\n".format(parts[2].strip())
        output.insert(0, version)
        output.append(estado_clines_oscam())
        output.append(oscam_info())
        return "\n".join(output) 

def oscam_start():
    command = emu_init_command()
    if command:
        line = getoutput("{} start".format(command)) or i18n.t("msg.starting")
        time.sleep(5)
        line += "\n" + emucam_status()
    else:
        line = i18n.t("msg.emu_not_active")
    return line

def oscam_stop():
    command = emu_init_command()
    if command:
        line = getoutput("{} stop".format(command)) or i18n.t("msg.stoping")
        time.sleep(5)
        line += "\n" + emucam_status()
    else:
        line = i18n.t("msg.emu_not_active")
    return line

def oscam_restart():
    command = emu_init_command()
    if command:
        line = getoutput("{} restart".format(command)) or i18n.t('msg.restarting')
        line += "\n" + emucam_status()
    else:
        line = i18n.t("msg.emu_not_active")
    return line

@with_confirmation
def install_oscam_conclave():
    file_autooscam = "/usr/bin/autooscam.sh"
    file_update_oscam = "/etc/oscam.update"
    if not os.path.exists(file_autooscam) and not os.path.exists(file_update_oscam):
        commands = "opkg install enigma2-plugin-softcams-oscam-conclave"
        return getoutput(commands)
    else:
        return i18n.t('msg.oscam_conclave_installed')

@with_confirmation
def update_autooscam():
    file_autooscam = "/usr/bin/autooscam.sh"
    if os.path.exists(file_autooscam):
        commands = """
            wget -q http://tropical.jungle-team.online/oscam/autooscam.sh -O /usr/bin/autooscam.sh
            chmod +x /usr/bin/autooscam.sh
            """
        return getoutput(commands)
    else:
        return i18n.t("msg.file_notfound", file=file_autooscam)
        
@with_confirmation
def run_autooscam():
    file_autooscam = "/usr/bin/autooscam.sh"
    if os.path.exists(file_autooscam):
        commands = """
            /usr/bin/autooscam.sh
            """
        return getoutput(commands)
    else:
        return i18n.t("msg.file_notfound", file=file_autooscam)
        
@with_confirmation
def force_autooscam():
    file_autooscam = "/usr/bin/autooscam.sh"
    file_update_oscam = "/etc/oscam.update"
    if os.path.exists(file_autooscam) and os.path.exists(file_update_oscam):
        commands = """
            rm -f /etc/oscam.update
            /usr/bin/autooscam.sh
            """
        return getoutput(commands)
    else:
        return i18n.t('msg.oscam_conclave_error')

def get_active_emu():
    active_emu = getoutput("readlink -f {}".format(emu_init_command())).split('/')[-1]
    return active_emu

def emu_list():
    distro = enigma_distro()
    if distro == "openspa":
        command = "ls /usr/script/*cam.sh"
    else: #(distro == "openatv" or distro == "openpli"):
        command = "ls /etc/init.d/softcam.*"
    output = getoutput("{} 2> /dev/null | grep -v None".format(command)).split()
    emus = map(lambda x: x.split('/')[-1], output)
    return emus

def list_installed_emus():
    emus = emu_list()
    active_emu = get_active_emu()
    emus = map(lambda x: "* {}".format(x) if x == active_emu else x, emus)
    return '\n'.join(emus)

def set_active_emu(emuladora):
    distro = enigma_distro()
    script = "/etc/init.d/softcam"
    new_emu = "/etc/init.d/" + emuladora

    if (distro == "openatv" or distro == "openpli" or distro == "teamblue"):
        pass
    else:
        return i18n.t('msg.emu_image_not_found') + distro
    if os.path.exists(new_emu):
        oscam_stop()
        time.sleep(5)
        commands = "{} start; ln -sf {} {}".format(new_emu, new_emu, script)
        execute_os_commands(commands)
        result = i18n.t('msg.emu_active')  
    else:
        result = i18n.t('msg.emu_notification')   
    return "{}\n{}".format(result, list_installed_emus())

def deletelineaoscam(linea):
    fich_temp_lineas = "/tmp/temp_lineas"
    oscam_cfg = oscam_config_dir() + "/oscam.server"
    if not os.path.exists(oscam_cfg):
        return i18n.t('msg.file_notfound', file=oscam_cfg).split("_")
    linea_inicio = word_line_in_file(linea, oscam_cfg) - 1
    commands = "sed '{}q;d' {} | grep 'reader]' | wc -l".format(linea_inicio, oscam_cfg)
    is_reader = int(getoutput(commands))
    if is_reader > 0:
        command = "grep -n 'reader]' {} > {}".format(oscam_cfg, fich_temp_lineas) 
        execute_os_commands(command)
        lineas = 1
        with open(fich_temp_lineas) as f:
            for line in f:
                linea_fic = int(line.split(":")[0])
                if linea_inicio == linea_fic:
                    linea_encon = lineas
                    break
                else:
                    lineas = lineas + 1
        command = "cat {} | wc -l".format(fich_temp_lineas)
        lineas_tot = int(getoutput(command))
        linea_sig = linea_encon + 1
        if linea_sig > lineas_tot:
            linea_final = "$"
        else:
            command = "sed '{}q;d' {} | cut -d':' -f1".format(linea_sig, fich_temp_lineas)
            linea_final = int(getoutput(command)) - 1
        command = "rm -f " + fich_temp_lineas
        execute_os_commands(command)
        command = "sed -i '{},{}d' {}".format(linea_inicio, linea_final, oscam_cfg)
        execute_os_commands(command)
        bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.oscam_delete_line_ok', linea=linea))
        oscam_restart()
        return oscam_status()
    else:
        bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.oscam_delete_line_error', linea=linea))

def list_readers_oscam():
    oscam_cfg = oscam_config_dir() + "/oscam.server"
    if not os.path.exists(oscam_cfg):
        return i18n.t('msg.file_notfound', file=oscam_cfg).split("_") 
    lista = getoutput("grep 'label' " + oscam_cfg + "| cut -d'=' -f2").split()
    return lista

def word_line_in_file(buscar, fichero):
    with open(fichero, "r") as file1:
        num_line = 0
        for line in file1:
            num_line += 1
            line = line.rstrip()
            line_split = line.split(" ")
            if buscar in line_split:
                return num_line

def dellinea_cccam(linea):
    cccam_cfg = "/etc/CCcam.cfg"
    if not os.path.isfile(cccam_cfg):
        return i18n.t('msg.file_notfound', file=cccam_cfg).split("_")
    num_linea = linea.split("[")[1].split("]")[0]
    command = "sed -i '{}d' {}".format(num_linea, cccam_cfg)
    execute_os_commands(command)
    command = "cat {}".format(cccam_cfg)
    return getoutput(command)

def list_lines_cccam():
    cccam_cfg = '/etc/CCcam.cfg'
    if not os.path.exists(cccam_cfg):
        return i18n.t('msg.file_notfound', file=cccam_cfg).split("_")
    else:
        command = "sed -i '/^$/d' {}".format(cccam_cfg)
        execute_os_commands(command)
        lista = []
        with open(cccam_cfg, "r") as file1:
            command = "cat {} | wc -l".format(cccam_cfg)
            lineas_tot = int(getoutput(command))
            if lineas_tot > 0:
                num_linea = 0
                for line in file1:
                    num_linea += 1
                    lista.append("[" + str(num_linea) + "] " + line.split(" ")[0] + " " + line.split(" ")[1] + " " + line.split(" ")[2] + " " + line.split(" ")[3])
                return lista
            else:
                return i18n.t('msg.emu_not_lines', file=cccam_cfg).split("_")

def list_readers_state():
    fich_temp_lines = "/tmp/temp_lines"
    if os.path.exists(fich_temp_lines):
        command = "rm -f " + fich_temp_lines
        execute_os_commands(command)
    fich_temp_readers = "/tmp/temp_readers"
    if os.path.exists(fich_temp_readers):
        command = "rm -f " + fich_temp_readers
        execute_os_commands(command)
    oscam_cfg = oscam_config_dir() + "/oscam.server"
    if not os.path.exists(oscam_cfg):
        return i18n.t('msg.file_notfound', file=oscam_cfg).split("_")
    readers = getoutput("grep 'label' " + oscam_cfg + "| cut -d'=' -f2").split()
    with open(fich_temp_readers, 'a') as f1:
        for reader in readers:
            linea_inicio = word_line_in_file(reader, oscam_cfg) - 1
            commands = "sed '{}q;d' {} | grep 'reader]' | wc -l".format(linea_inicio, oscam_cfg)
            is_reader = int(getoutput(commands))
            if is_reader > 0:
                command = "grep -n 'reader]' {} > {}".format(oscam_cfg, fich_temp_lines) 
                execute_os_commands(command)
                lineas = 1
                with open(fich_temp_lines, 'r') as f2:
                    for line in f2:
                        linea_fic = int(line.split(":")[0])
                        if linea_inicio == linea_fic:
                            linea_encon = lineas
                            break
                        else:
                            lineas = lineas + 1
                command = "cat {} | wc -l".format(fich_temp_lines)
                lineas_tot = int(getoutput(command))
                linea_sig = linea_encon + 1
                if linea_sig > lineas_tot:
                    linea_final = "$"
                else:
                    command = "sed '{}q;d' {} | cut -d':' -f1".format(linea_sig, fich_temp_lines)
                    linea_final = int(getoutput(command)) - 1
                command = "sed -n '{},{}p' {} | grep enable | cut -d'=' -f2".format(linea_inicio, linea_final, oscam_cfg)
                status_reader = getoutput(command).strip()
                if not status_reader:
                    status_reader = 1
                f1.write(reader + ":" + str(status_reader) + "\n")
    
def enable_reader_oscam(reader):
    oscam_cfg = oscam_config_dir() + "/oscam.server"
    if not os.path.exists(oscam_cfg):
        return i18n.t('msg.file_notfound', file=oscam_cfg).split("_")
    fich_temp_lineas = "/tmp/temp_lineas"
    linea_insert = word_line_in_file(reader, oscam_cfg) + 1
    command = "sed -n '{}p' {} | grep enable | wc -l".format(linea_insert, oscam_cfg)
    tiene_enable = int(getoutput(command))
    if tiene_enable > 0:        
        command = "sed -i '{} s/0/1/g' {}".format(linea_insert, oscam_cfg, oscam_cfg)
        execute_os_commands(command)
        oscam_restart()
        return oscam_status()
    else:
        return i18n.t('msg.oscam_line_enable_error', linea=reader).split("_") 

def disable_reader_oscam(reader):
    oscam_cfg = oscam_config_dir() + "/oscam.server"
    if not os.path.exists(oscam_cfg):
        return i18n.t('msg.file_notfound', file=oscam_cfg).split("_")
    linea_insert = word_line_in_file(reader, oscam_cfg) + 1
    command = "sed -n '{}p' {} | grep enable | wc -l".format(linea_insert, oscam_cfg)
    tiene_enable = int(getoutput(command))
    if tiene_enable > 0:
        command = "sed -i '{} s/1/0/g' {}".format(linea_insert, oscam_cfg)
    else:
        command= "sed -i '{}i {}' {}".format(linea_insert, "enable = 0", oscam_cfg)
    execute_os_commands(command)
    oscam_restart()
    return oscam_status()

def list_enabled_readers_oscam():
    list_readers_state()
    fich_temp_readers = "/tmp/temp_readers"
    lista = []
    if not os.path.exists(fich_temp_readers):
        return i18n.t('msg.file_notfound', file=fich_temp_readers).split("_") 
    f = open(fich_temp_readers, 'r')
    for line in f:
        status_reader = int(line.split(":")[1])
        if status_reader == 1:
            lista.append(line.split(":")[0])
    if lista:
        return lista
    else:
        return i18n.t('msg.oscam_not_readers_disabled').split("_")

def list_disabled_readers_oscam():
    list_readers_state()
    fich_temp_readers = "/tmp/temp_readers"
    lista = []
    if not os.path.exists(fich_temp_readers):
        return i18n.t('msg.file_notfound', file=fich_temp_readers).split("_") 
    f = open(fich_temp_readers, 'r')
    for line in f:
        status_reader = int(line.split(":")[1])
        if status_reader == 0:
            lista.append(line.split(":")[0])
    if lista:
        return lista
    else:
        return i18n.t('msg.oscam_not_readers_enabled').split("_")

# JUNGLESCRIPT
@with_confirmation  
def junglescript_install():
    command = "opkg update"
    execute_os_commands(command)
    hay_junglescript = int(getoutput("opkg list-installed | grep enigma2-plugin-extensions-junglescript | wc -l"))
    if hay_junglescript > 0:
        commands = "opkg upgrade enigma2-plugin-extensions-junglescript"
        message = "junglescript esta instalado. Upgrading si procede..."
    else:
        commands = """
                    opkg remove junglescript
                    opkg install enigma2-plugin-extensions-junglescript
                    """
        message = "Instalando junglescript..."
    output = getoutput(commands)
    return f"{message}\n{output}"


@with_confirmation
def junglescript_run():
    return getoutput("/usr/bin/enigma2_pre_start.sh")

@with_confirmation
def junglescript_uninstall():
    commands = "opkg remove enigma2-plugin-extensions-junglescript"
    return getoutput(commands)
       
def junglescript_log():
    if os.path.exists('/tmp/enigma2_pre_start.log'):
        logfile_junglescript = '/tmp/enigma2_pre_start.log'
    else:
        logfile_junglescript = '/var/log/enigma2_pre_start.log'
    get_file(logfile_junglescript)

@with_confirmation
def junglescript_channels():
    commands = """
            sed -i 's/^FECHA_LISTACANALES=.*$/FECHA_LISTACANALES=/' /usr/bin/enigma2_pre_start.conf
            /usr/bin/enigma2_pre_start.sh
            """
    return getoutput(commands)

@with_confirmation
def junglescript_picons():
    commands = """
            sed -i 's/^FECHA_PICONS=.*$/FECHA_PICONS=/' /usr/bin/enigma2_pre_start.conf
            /usr/bin/enigma2_pre_start.sh
            """
    return getoutput(commands)
    
def junglescript_fecha_listacanales():
    junglescript_conf = "/usr/bin/enigma2_pre_start.conf"
    if os.path.exists(junglescript_conf): 
       fecha_listacanales = getoutput("grep -i FECHA_LISTACANALES= " + junglescript_conf)
    return fecha_listacanales     

def junglescript_version():
    junglescript_file = "/usr/bin/enigma2_pre_start.sh"
    if os.path.exists(junglescript_file): 
       junglescript_version = getoutput("grep -i VERSION= " + junglescript_file)
    return junglescript_version   

def buscar_fich_act_picons():
    ruta_picons = "/media/hdd/picon"
    fichero_act_picons = ruta_picons + "/actualizacion"
    if os.path.exists(fichero_act_picons): 
       return fichero_act_picons
    else:
       ruta_picons = "/media/usb/picon"
       fichero_act_picons = ruta_picons + "/actualizacion"
       if os.path.exists(fichero_act_picons): 
          return fichero_act_picons
       else:
           ruta_picons = "/media/mmc/picon"
           fichero_act_picons = ruta_picons + "/actualizacion"
           if os.path.exists(fichero_act_picons):  
              return fichero_act_picons
           else:
               ruta_picons = "/usr/share/enigma2/picon"
               fichero_act_picons = ruta_picons + "/actualizacion"
               if os.path.exists(fichero_act_picons):  
                  return fichero_act_picons
               else:
                   return i18n.t("msg.file_notfound", file=fichero_act_picons)

def junglescript_fecha_picons():
    junglescript_conf = "/usr/bin/enigma2_pre_start.conf"
    if os.path.exists(junglescript_conf): 
       fecha_picons = getoutput("grep -i FECHA_PICONS= " + junglescript_conf)
    return fecha_picons  

def fav_bouquet():
    fichero = "/etc/enigma2/fav_bouquets"
    bouquets = junglescript_fav_bouquets()
    if len(bouquets) > 0:
        return '\n'.join(bouquets)
    else:
        if not os.path.exists(fichero):
            return i18n.t('msg.file_notfound', file=fichero)

def junglescript_addfavbouquet(bouquet):
    with open ('/etc/enigma2/fav_bouquets','a') as f:
        f.write(bouquet + "\n")
    return fav_bouquet()

def junglescript_fav_bouquets():
    fichero = "/etc/enigma2/fav_bouquets"
    if os.path.isfile(fichero):
        file = open(fichero).read()
        items = file.splitlines()
    if len(items) > 0:
        return items
    else:
        return []
        
def junglescript_delfavbouquet(bouquet):
    fichero = "/etc/enigma2/fav_bouquets"
    if os.path.exists(fichero):
        lines = None
        with open(fichero, 'r') as file:
            lines = file.readlines()
        with open (fichero, 'w') as f:
            for line in lines:
                if line.strip("\n") != bouquet:
                    f.write(line)
        return fav_bouquet()
    else:
        return i18n.t('msg.file_notfound', file=fichero)

def save_bouquet():
    fichero = "/etc/enigma2/save_bouquets"
    bouquets = junglescript_save_bouquets()
    if len(bouquets) > 0:
        return '\n'.join(bouquets)
    else:
        if not os.path.exists(fichero):
            return i18n.t('msg.file_notfound', file=fichero)
        
def junglescript_addsavebouquet(bouquet):
    with open ('/etc/enigma2/save_bouquets','a') as f:
        f.write(bouquet + "\n")
    return save_bouquet()

def junglescript_save_bouquets():
    fichero = "/etc/enigma2/save_bouquets"
    if os.path.isfile(fichero):
        file = open(fichero).read()
        items = file.splitlines()
    if len(items) > 0:
        return items
    else:
        return []
        
def junglescript_delsavebouquet(bouquet):
    fichero = '/etc/enigma2/save_bouquets'
    if os.path.exists(fichero):
        lines = None
        with open(fichero, 'r') as file:
            lines = file.readlines()
        with open (fichero, 'w') as f:
            for line in lines:
                if line.strip("\n") != bouquet:
                    f.write(line)
        return save_bouquet()
    else:
        return i18n.t('msg.file_notfound', file=fichero)

#JUNGLEBOT
@with_confirmation 
def junglebot_update():
    check_version()
    if new_version == True:
        distro = enigma_distro()
        package = 'enigma2-plugin-extensions-junglebot'
        command = "opkg remove junglebot --force-remove; opkg upgrade {package}".format(package=package)
        os.system(command)
    else:
        bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.junglebot_update', version=VERSION))

@with_confirmation		
def junglebot_restart():
    os.system("/etc/init.d/junglebot-daemon restart &")

def junglebot_log():
    get_file(G_CONFIG['rutalog'])

def junglebot_purge_log():
    commands = "echo '' > " + G_CONFIG['rutalog']
    execute_os_commands(commands)

def junglebot_changelog():
    commands = "head -n 15 /usr/bin/junglebot/CHANGELOG.md"
    return getoutput(commands)

# GRABACIONES
def list_recordings():
    output = []
    index_rec = 0
    j = webif_api("fullmovielist")
    if j['movies']:
        for s in j['movies']:
            output.append(str(index_rec) + " - " + s['eventname'])
            index_rec = index_rec + 1
    else:
        output.append(i18n.t('msg.recording_notexist', location=j['locations'][0]))
    return "\n".join(output)

def delete_recordings(index_sref):
    j = webif_api("fullmovielist")
    if j['movies']:
        tamano = len(j['movies'])
        indice = int(index_sref)
        salida = i18n.t('msg.recording_indexnotexist')
        if indice <= tamano:
            if j['movies'][indice]:
                filename = j['movies'][indice]['filename']
                command = 'rm -f "' + filename + '"'
                return getoutput(command)
            else:
                return salida
        else:
            return salida
    else:
        return i18n.t('msg.recording_notexist', location=j['locations'][0])

@with_confirmation
def delete_all_recordings():
    j = webif_api("fullmovielist")
    if j['movies']:
        if j['locations'][0]:
            command = "rm -rf " + j['locations'][0] + "*"
            return getoutput(command)
    else:        
        return i18n.t('msg.recording_notexist', location=j['locations'][0])                

def show_path_recordings():
    j = webif_api("fullmovielist")
    if j['locations'][0]:
        return j['locations'][0]
    else:        
        return i18n.t('msg.recording_notexist', location=j['locations'][0])    

def list_recording_timers():
    output = []
    index_timer = 0
    j = webif_api("timerlist")
    if j['timers']:
        for s in j['timers']:
            output.append(str(index_timer) + " - " + s['servicename'] + ", " + s['realbegin'] + " - " + s['realend'])
            index_timer = index_timer + 1
    return "\n".join(output)

@with_confirmation    
def clean_expired_timers():
    j = webif_api("timercleanup")
    if j['result']:
        return j['message']

def record_now():
    j = webif_api("recordnow")
    if j['result']:
        return j['message']

def delete_timer(index_sref):
    j = webif_api("timerlist")
    if j['timers']:
        tamano = len(j['timers'])
        indice = int(index_sref)
        salida = i18n.t('msg.recording_indexnotexist')
        if indice <= tamano:
            if j['timers'][indice]:
                serviceref = j['timers'][indice]['serviceref']
                begin = str(j['timers'][indice]['begin'])
                end = str(j['timers'][indice]['end'])
                k = webif_api("timerdelete?sRef=" + serviceref + "&begin=" + begin + "&end=" + end)
                if k['result']:
                    return i18n.t('msg.recording_delete_success')
                else:
                    return k['message']
            else:
                return salida
        else:
            return salida
    else:
        return i18n.t('msg.recording_schedule_notexist')

#EPG
def find_epg_dat():
    epg_dat = getoutput("grep config.misc.epgcache /etc/enigma2/settings | cut -d'=' -f2")
    if not epg_dat:
        epg_dat = "/etc/enigma2/epg.dat"
    else:
        if not os.path.isfile(epg_dat) and os.path.isdir(epg_dat):
            ultimo = epg_dat[len(epg_dat)-1]
            if ultimo == '/':
                epg_dat = epg_dat + "epg.dat"
            else:
                epg_dat = epg_dat + "/epg.dat"      
    return epg_dat
       
def find_date_epg_dat():
    epg_dat = find_epg_dat()
    if os.path.exists(epg_dat):
        epg_date = i18n.t('msg.updated_at', date=time.ctime(os.path.getmtime(epg_dat)))
    else:        
        epg_date = i18n.t('msg.file_notfound', file=epg_dat)
    return epg_date
    
def find_epg_application():
    crossepg = "enigma2-plugin-systemplugins-crossepg"
    epgimport = "enigma2-plugin-extensions-epgimport"
    appli_crossepg = getoutput("opkg list-installed | grep " + crossepg).strip()
    appli_epgimport = getoutput("opkg list-installed | grep " + epgimport).strip()
    if not appli_crossepg and not appli_epgimport:
         salida = i18n.t('msg.epg_app_install')
    elif appli_crossepg and not appli_epgimport:
         salida = i18n.t('msg.crossepg_installed')
    elif not appli_crossepg and appli_epgimport:
         salida = i18n.t('msg.epgimport_installed')
    else:
        salida = i18n.t('msg.epg_two_apps_installed')
    return salida

def update_epg(days):
    if days == "3" or days == "7" or days == "15" or days == "30":
        epg_dat = find_epg_dat()
        app = find_epg_application()
        commands = ""
        if app:
            if app == "EPGImport instalado":
                http_epgimport = "http://tropical.jungle-team.online/epg/epgimport/"
                ruta_fich_epgimport = "/etc/epgimport/"
                fich_epgimport = "rytec_koala" + days + ".xml"
                if not os.path.exists(ruta_fich_epgimport + fich_epgimport):
                    commands = "cd " + ruta_fich_epgimport + "; curl -O " + http_epgimport + fich_epgimport + ";" 
                commands = commands + " /usr/bin/python /usr/lib/enigma2/python/Plugins/Extensions/EPGImport/OfflineImport.pyo " + ruta_fich_epgimport + fich_epgimport
                execute_os_commands(commands)
                fich_new_epg_dat = getoutput("find / -name 'epg_new.dat' -type f -print0 2>/dev/null |xargs -0")
                if fich_new_epg_dat:
                    commands = "rm -f " + epg_dat + "; mv " + fich_new_epg_dat + " " + epg_dat + "; killall -9 enigma2;"
                    execute_os_commands(commands)
                    return i18n.t('msg.epg_update_success', info=days)
                else:
                    return i18n.t('msg.epg_update_error', info=days)
            elif app == "Crossepg instalado":
                http_crossepg = "http://tropical.jungle-team.online/epg/crossepg/"
                ruta_fich_crossepg = "/usr/crossepg/providers/"
                fich_crossepg = "Koala-epg-" + days + ".conf"
                if not os.path.exists(ruta_fich_crossepg + fich_crossepg):
                    commands = "cd " + ruta_fich_crossepg + "; curl -O " + http_crossepg + fich_crossepg
                commands = commands + " /usr/crossepg/crossepg_downloader -d /tmp -p " + "Koala-epg-" + days + "; "
                commands = commands + " /usr/crossepg/crossepg_dbconverter -d /tmp -e /tmp/epg_new.dat"
                fich_new_epg_dat = getoutput("find / -name 'epg_new.dat' -type f -print0 2>/dev/null |xargs -0")
                if fich_new_epg_dat:
                    commands = "rm -f " + epg_dat + "; mv " + fich_new_epg_dat + " " + epg_dat + "; killall -9 enigma2;"
                    execute_os_commands(commands) 
                    return i18n.t('msg.epg_update_success', info=days)
                else:
                    return i18n.t('msg.epg_update_error', info=days)
            else:
                return app
    else:
        return i18n.t('msg.epg_days_error')

def geolocalizar_ip(geolocalizar=''):
    apiurl='http://ip-api.com/json/'
    r=requests.get(apiurl+geolocalizar)
    return json.dumps(json.loads(r.content),indent=4)
    
def bloquear_ip(bloquear):
    ips_bloqueadas = "/usr/bin/junglebot/ips_bloqueadas.txt"
    if os.path.exists(ips_bloqueadas):
        with open (ips_bloqueadas,'a') as f:
            f.write(bloquear + "\n")
            commands = "route add -host {} reject".format(bloquear)
            execute_os_commands(commands)
            logger.info("Ip Bloqueda: " + bloquear)
            f.close()
    else:
        with open (ips_bloqueadas,'w') as f:
            f.write(bloquear + "\n")
            commands = "route add -host {} reject".format(bloquear)
            execute_os_commands(commands)
            logger.info("Ip Bloqueda: " + bloquear)
            f.close()
    return i18n.t('msg.geo_block_ip')

def desbloquear_ip(desbloquear):
    ips_bloqueadas = "/usr/bin/junglebot/ips_bloqueadas.txt"
    with open(ips_bloqueadas, 'r') as f:
        lines = f.readlines()
        f.close()
    with open (ips_bloqueadas, 'w') as f:
        for line in lines:
            if line.strip("\n") != desbloquear:
                f.write(line)
        commands = "route del {} reject".format(desbloquear)
        execute_os_commands(commands)
        f.close()
        return i18n.t('msg.geo_unblock_ip')

def cargar_ips_bloquedas():
    ips_bloqueadas = "/usr/bin/junglebot/ips_bloqueadas.txt"
    if os.path.exists(ips_bloqueadas):
        with open (ips_bloqueadas, 'r') as f:
            lines = f.readlines()
            for line in lines:
                ip = line.rstrip('\n')
                commands = "route add -host {} reject".format(ip)
                execute_os_commands(commands)
                logger.info("Ip {} bloqueada".format(ip))
        f.close()
    else:
        logger.info(i18n.t('msg.file_notfound', file=ips_bloqueadas))

def rejected_ips():
    ips_bloqueadas = "/usr/bin/junglebot/ips_bloqueadas.txt"
    rejected_ips = []
    if os.path.exists(ips_bloqueadas):
        with open (ips_bloqueadas, 'r') as f:
            lines = f.readlines()
            for line in lines:
                ip = line.rstrip('\n')
                rejected_ips.append(ip)
            return rejected_ips
        f.close()
    else:
        logger.info(i18n.t('msg.file_notfound', file=ips_bloqueadas))

def mostrar_ip():
    return '\n'.join(rejected_ips())

@with_confirmation 
def delete_epg_dat():
    epg_dat = find_epg_dat()
    if os.path.exists(epg_dat):
        commands = "rm -f {}; killall -9 enigma2;".format(epg_dat)
        execute_os_commands(commands)
        salida = i18n.t('msg.file_erased', file=epg_dat)         
    else:        
        salida = i18n.t('msg.file_notfound', file=epg_dat)
    return salida
	
@with_confirmation 
def remove_epgimport():
    epgimport = "enigma2-plugin-extensions-epgimport"
    appli_epgimport = getoutput("opkg list-installed | grep " + epgimport).strip()
    if appli_epgimport:
        command = "opkg remove {}".format(epgimport)
        execute_os_commands(command)
        salida = i18n.t('msg.epgimport_uninstalled')
    else:
        salida = i18n.t('msg.epgimport_uninstall_error')
    return salida

@with_confirmation 
def remove_crossepg():
    crossepg = "enigma2-plugin-systemplugins-crossepg"
    appli_crossepg = getoutput("opkg list-installed | grep " + crossepg).strip()
    if appli_crossepg:
        command = "opkg remove {}".format(crossepg)
        execute_os_commands(command)
        salida = i18n.t('msg.crossepg_uninstalled')
    else:
        salida = i18n.t('msg.crossepg_uninstall_error')
    return salida
       
#CONEXIONES
def controlssh():
    conexiones = getoutput("netstat -tan | grep \:'22 ' | grep ESTAB | awk '{print $5}' |sed -e 's/::ffff://'| cut -d: -f1 | sort") 
    conexiones = conexiones.split('\n')
    output = []
    for linea in conexiones:
        if linea:
            output.append(i18n.t('msg.ssh_conn', info=linea))
    if output:
        return "\n".join(output)
    else:
        return i18n.t('msg.ssh_conn_notfound')
	
def controlftp():
    conexiones = getoutput("netstat -tan | grep \:'21 ' | grep ESTAB | awk '{print $5}' |sed -e 's/::ffff://'| cut -d: -f1 | sort") 
    conexiones = conexiones.split('\n')
    output = []
    for linea in conexiones:
        if linea:
           output.append(i18n.t('msg.ftp_conn', info=linea))
    if output:
        return "\n".join(output)
    else:
        return i18n.t('msg.ftp_conn_notfound')       

@with_confirmation
def conn_autoftp():
    G_CONFIG['autoftp'] = '1'
    return start_autoftp()

@with_confirmation
def conn_autossh():
    G_CONFIG['autossh'] = '1'
    return start_autossh()

# REMOTECONTROL

class hash_table:
    def __init__(self):
        self.size = 113	
        self.table = [None] * self.size

    def __len__(self):
        count = 0
        for value in self.table:
           if value != None:
               count += 1
        return count

    def Hash_func(self, value):
        key = 0
        for i in range(0,len(value)):
            key += ord(value[i])
        return key % self.size

    def Insert(self, key, value):
        hash = self.Hash_func(key)
        if self.table[hash] is None:
            self.table[hash] = value

    def Search(self, key):
        hash = self.Hash_func(key)
        if self.table[hash] is None:
            return None
        else:
            return self.table[hash]	

KEYIDS = {
	"KEY_NUM1": 2,
	"KEY_NUM2": 3,
	"KEY_NUM3": 4,
	"KEY_NUM4": 5,
	"KEY_NUM5": 6,
	"KEY_NUM6": 7,
	"KEY_NUM7": 8,
	"KEY_NUM8": 9,
	"KEY_NUM9": 10,
	"KEY_NUM0": 11,
	"KEY_UP": 103,
	"KEY_LEFT": 105,
	"KEY_RIGHT": 106,
	"KEY_DOWN": 108,
    "KEY_MUTE": 113,
	"KEY_VOLUMEDOWN": 114,
	"KEY_VOLUMEUP": 115,
	"KEY_POWER": 116,
    "KEY_MENU": 139,
    "KEY_EXIT": 174,
    "KEY_OK": 352,
	"KEY_COLOR_RED": 398,
	"KEY_COLOR_GREEN": 399,
	"KEY_COLOR_YELLOW": 400,
	"KEY_COLOR_BLUE": 401
}

tabla = hash_table()

def remotecontrol_status():
    response = webif_get("powerstate")
    if  re.split('[\n\t]', response)[4] == 'true':
        resultado = i18n.t('msg.satbox_standby')
    else:
        resultado = i18n.t('msg.satbox_started')
    return resultado

@with_confirmation
def remotecontrol_reboot():
    line = getoutput("reboot")
    return i18n.t('msg.command_reboot') + "\n" + line

@with_confirmation
def remotecontrol_restartgui():
    line = getoutput("killall -9 enigma2")
    return i18n.t('msg.command_restartgui') + "\n" + line

def remotecontrol_standby_wakeup():
    response = webif_get("powerstate")
    if  re.split('[\n\t]', response)[4] == 'true':
        line = webif_get("powerstate?newstate=0")
        resultado = i18n.t('msg.command_wakeup') + "\n" + line
    else:
        codigo = buscar_valor_tabla("POWER")
        command = "remotecontrol?command={}".format(codigo)
        line = webif_get(command)
        resultado = i18n.t('msg.command_sleep') + "\n" + line
    return resultado

def remotecontrol_screenshot():
    captura = execute_os_commands("wget 127.0.0.1/grab -O /tmp/capturacanal.png > /dev/null 2>&1")
    doc = open('/tmp/capturacanal.png', 'rb')
    bot.send_document(G_CONFIG['chat_id'], doc)
    execute_os_commands("sleep 2 & rm -f /tmp/capturacanal.png")
    return ''

def remotecontrol_send_message(message):
    resp = webif_api("message?type=1&text={}".format(bytearray(message, 'utf8').decode('utf8')))
    if resp.get('result', False):
        return i18n.t('msg.send_msg_success')
    else:
        return i18n.t('msg.send_msg_error') 

def remotecontrol_change_channel(keys):
    # Only numbers
    key_codes = []
    for key in keys:
        if key.isdigit():
            if key == '0':
                key_codes.append(11)
            else:
                key_codes.append(int(key) + 1)
    if len(keys) == len(key_codes):
        for key_code in key_codes:
            webif_api("remotecontrol?command={}".format(key_code))
        return "Ok '{}'".format(keys)
    else:
        return i18n.t('msg.send_remote_error') 

def remotecontrol_send_up():
    valor = buscar_valor_tabla("UP")
    return remotecontrol_send_command(valor)

def remotecontrol_send_down():
    valor = buscar_valor_tabla("DOWN")
    return remotecontrol_send_command(valor)

def remotecontrol_send_left():
    valor = buscar_valor_tabla("LEFT")
    return remotecontrol_send_command(valor)

def remotecontrol_send_right():
    valor = buscar_valor_tabla("RIGHT")
    return remotecontrol_send_command(valor)

def remotecontrol_send_menu():
    valor = buscar_valor_tabla("MENU")
    return remotecontrol_send_command(valor)

def remotecontrol_send_exit():
    valor = buscar_valor_tabla("EXIT")
    return remotecontrol_send_command(valor)

def remotecontrol_send_ok():
    valor = buscar_valor_tabla("OK")
    return remotecontrol_send_command(valor)

def remotecontrol_send_red():
    valor = buscar_valor_tabla("COLOR_RED")
    return remotecontrol_send_command(valor)

def remotecontrol_send_green():
    valor = buscar_valor_tabla("COLOR_GREEN")
    return remotecontrol_send_command(valor)

def remotecontrol_send_yellow():
    valor = buscar_valor_tabla("COLOR_YELLOW")
    return remotecontrol_send_command(valor)

def remotecontrol_send_blue():
    valor = buscar_valor_tabla("COLOR_BLUE")
    return remotecontrol_send_command(valor)

def remotecontrol_send_vol_up():
    valor = buscar_valor_tabla("VOLUMEUP")
    return remotecontrol_send_command(valor)

def remotecontrol_send_vol_down():
    valor = buscar_valor_tabla("VOLUMEDOWN")
    return remotecontrol_send_command(valor)

def remotecontrol_send_mute():
    valor = buscar_valor_tabla("MUTE")
    return remotecontrol_send_command(valor)

def remotecontrol_send_command(codigo):
    command = "remotecontrol?command={}".format(codigo)
    line = webif_get(command)
    return ""

def remotecontrol_send_digit(digit):
    if digit.isdigit() and len(digit) == 1:
        digit = "NUM" + digit
        value_digit = buscar_valor_tabla(digit)
        command = "remotecontrol?command={}".format(value_digit)
        line = webif_get(command)
        return ""
    else:
        return i18n.t('msg.send_remote_error') 

def cargar_tabla_hash():
	if len(tabla) == 0:
		for key, value in KEYIDS.items():
			tabla.Insert(key, value)

def buscar_valor_tabla(clave):
    global tabla
    cargar_tabla_hash()
    clave = "KEY_{}".format(clave)
    valor = tabla.Search(clave)
    return valor
# ZEROTIER

def zerotier_status():
    var_zerotier = getoutput("which /usr/sbin/zerotier-cli")
    output = []
    if var_zerotier:
        output.append(i18n.t('msg.info_zerotier'))
        # estado zerotier
        line = getoutput("/usr/sbin/zerotier-cli info")
        output.append(line)
        # per zerotier
        line = getoutput("/usr/sbin/zerotier-cli listpeers")
        output.append("  [i] " + line)
        # network zerotier
        line = getoutput("/usr/sbin/zerotier-cli listnetworks")
        output.append("  [i] " + line)
    else:
        output.append(i18n.t('msg.info_zerotier_notinstalled'))
    return "\n".join(output)

def zerotier_stop():
    var_zerotier = getoutput("which /usr/sbin/zerotier-cli")
    output = []
    if var_zerotier:
        command = "/etc/init.d/zerotier stop"
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_zerotier_notinstalled'))
    return "\n".join(output)

def zerotier_start():
    var_zerotier = getoutput("which /usr/sbin/zerotier-cli")
    output = []
    if var_zerotier:
        command = "/etc/init.d/zerotier start"
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_zerotier_notinstalled'))
    return "\n".join(output)

def zerotier_force_reload():
    var_zerotier = getoutput("which /usr/sbin/zerotier-cli")
    output = []
    if var_zerotier:
        command = "/etc/init.d/zerotier force-reload"
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_zerotier_notinstalled'))
    return "\n".join(output)

def zerotier_join_network(netid):
    var_zerotier = getoutput("which /usr/sbin/zerotier-cli")
    output = []
    if var_zerotier:
        command = "/usr/sbin/zerotier-cli join {}".format(netid)
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_zerotier_notinstalled'))
    return "\n".join(output)

def zerotier_leave_network(netid):
    var_zerotier = getoutput("which /usr/sbin/zerotier-cli")
    output = []
    if var_zerotier:
        command = "/usr/sbin/zerotier-cli leave {}".format(netid)
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_zerotier_notinstalled'))
    return "\n".join(output)

@with_confirmation
def zerotier_install():
    hay_zerotier = int(getoutput("opkg list-installed | grep zerotier | wc -l"))
    output = []
    if hay_zerotier == 0:
        command = "opkg install zerotier"
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_zerotier_installed'))
    return "\n".join(output)

@with_confirmation
def zerotier_uninstall():
    hay_zerotier = int(getoutput("opkg list-installed | grep zerotier | wc -l"))
    output = []
    if hay_zerotier > 0:
        command = "opkg remove zerotier"
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_zerotier_notinstalled'))
    return "\n".join(output)
    
# TAILSCALE
def tailscale_up():
    var_tailscale = getoutput("which /usr/bin/tailscale")
    output = []
    if var_tailscale:
        command = ("/usr/bin/tailscale up")
        line = getoutput(command)
        output.append(i18n.t('msg.info_tailscale_up'))
    else:
        output.append(i18n.t('msg.info_tailscale_notinstalled'))
    return "\n".join(output)
    
@with_confirmation    
def tailscale_install():
    hay_tailscale = int(getoutput("opkg list-installed | grep tailscale | wc -l"))
    output = []
    if hay_tailscale == 0:
        command = "opkg install tailscale"
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_tailscale_installed'))
    return "\n".join(output)
    
@with_confirmation    
def tailscale_uninstall():
    hay_tailscale = int(getoutput("opkg list-installed | grep tailscale | wc -l"))
    output = []
    if hay_tailscale > 0:
        command = "opkg remove tailscale"
        line = getoutput(command)
        output.append(line)
    else:
        output.append(i18n.t('msg.info_tailscale_notinstalled'))
    return "\n".join(output)
    
def tailscale_down():
    var_tailscale = getoutput("which /usr/bin/tailscale")
    output = []
    if var_tailscale:
        command = ("/usr/bin/tailscale down")
        line = getoutput(command)
        output.append(i18n.t('msg.info_tailscale_down'))
    else:
        output.append(i18n.t('msg.info_tailscale_notinstalled'))
    return "\n".join(output)
    
def tailscale_ip():
    var_tailscale = getoutput("which /usr/bin/tailscale")
    output = []
    if var_tailscale:
        output.append(i18n.t('msg.info_ip_tailscale'))
        line = getoutput("/usr/bin/tailscale ip")
        output.append(line.splitlines()[0])
    else:
        output.append('msg.info_tailscale_notinstalled')
    return "\n".join(output)

def tailscale_status():
    var_tailscale = getoutput("which /usr/bin/tailscale")
    output = []
    if var_tailscale:
        output.append(i18n.t('msg.info_status_tailscale'))
        line = getoutput("/usr/bin/tailscale status")
        output.append(line)
    else:
        output.append(i18n.t('msg.info_tailscale_notinstalled'))
    return "\n".join(output)

# MAS INFO

def plugin_instalados():
    output = []
    output.append(i18n.t('msg.info_plugin_installed'))
    line = getoutput("/usr/bin/opkg list-installed")
    output.append(line)
    return "\n".join(output)
      
def crontab_tareas():
    cron = CronTab(user='root')
    jobs = []
    output = []
    output.append(i18n.t('msg.info_crontab_tareas'))
    for job in cron:
        output.append(str(job))
    return "\n".join(output)
    
def get_ram_disponible():
    output = []
    available_memory = psutil.virtual_memory().available
    available_memory_mb = round(available_memory / (1024**2), 2)
    output.append(str(available_memory_mb) + " MB")
    return "\n".join(output)
    
def get_cpu_uso():
    output = []
    cpu_uso = psutil.cpu_percent()
    output.append(f"{cpu_uso}%")
    return "\n".join(output)

def get_disco_interno_disponible():
    output = []
    disco_interno = psutil.disk_usage('/')
    espacio_libre_mb = round(disco_interno.free / (1024**2), 2)
    output.append(f"{espacio_libre_mb} MB")
    return "\n".join(output)
    
def get_puntos_de_montaje():
    output = []
    for partition in psutil.disk_partitions():
        output.append(f"{partition.device}: {partition.mountpoint}")
    return "\n".join(output)
    
def get_bytes_red():
    output = []
    bytes_enviados = psutil.net_io_counters().bytes_sent
    bytes_recibidos = psutil.net_io_counters().bytes_recv
    output.append(f"Enviados: {bytes_enviados} bytes")
    output.append(f"Recibidos: {bytes_recibidos} bytes")
    return "\n".join(output)

def get_conexiones_de_red():
    output = []
    for connection in psutil.net_connections(kind='inet'):
        if connection.status == 'ESTABLISHED':
            output.append(f"{connection.laddr.ip}:{connection.laddr.port} -> {connection.raddr.ip}:{connection.raddr.port}")
    return "\n".join(output)
    
def get_proceso_con_mas_consumo():
    output = []
    max_cpu_percent = -1
    max_mem_percent = -1
    max_process = None
    for process in psutil.process_iter():
        try:
            cpu_percent = process.cpu_percent()
            mem_percent = process.memory_percent()
            if cpu_percent > max_cpu_percent:
                max_cpu_percent = cpu_percent
                max_process = process
            if mem_percent > max_mem_percent:
                max_mem_percent = mem_percent
                max_process = process
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    if max_process is not None:
        output.append(f"PID: {max_process.pid}, \nNombre: {max_process.name()}, \nConsumo CPU: {max_cpu_percent}%, \nConsumo Memoria: {max_mem_percent}%")
    return "\n".join(output)

def get_interfaces_de_red_activas():
    output = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                output.append(f"{interface}: {addr.address} ({addr.netmask})")
    return "\n".join(output)
    
def get_dmesg():
    output = []
    with open('/var/log/dmesg', 'r') as f:
        output.append(f.read())
    return "\n".join(output)
    
@with_confirmation   
def repo_jungle_install():
    url = 'http://tropical.jungle-team.online/script/jungle-feed.conf'
    local_path = '/etc/opkg/jungle-feed.conf'
    output = []
    if os.path.exists(local_path):
        output.append(f'Archivo {local_path} ya existe, no se instala')
    else:
        response = requests.get(url)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            output.append(f'Instalando {url} to {local_path}')
        else:
            output.append(f'Descarga fallida {url}: {response.status_code} {response.reason}')
    return "\n".join(output)
    
@with_confirmation    
def repo_oeAlliance():
    output = []
    url = "http://updates.mynonpublic.com/oea/feed"
    process = subprocess.Popen(["bash", "-c", f"curl -s {url} | bash"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        output.append(f"Error executing command: {stderr.decode()}")
    else:
        output.append(stdout.decode())
    
    return "\n".join(output)

@with_confirmation  
def install_junglescripttool():
    command = "opkg update"
    execute_os_commands(command)
    hay_junglescripttool = int(getoutput("opkg list-installed | grep enigma2-plugin-extensions-junglescripttool | wc -l"))
    if hay_junglescripttool > 0:
        commands = "opkg upgrade enigma2-plugin-extensions-junglescripttool"
        message = "Junglescripttool esta instalado. Upgrading si procede..."
    else:
        commands = """
                    opkg remove enigma2-plugin-extensions-junglescripttool
                    opkg install enigma2-plugin-extensions-junglescripttool
                    """
        message = "Instalando Junglescripttool..."
    output = getoutput(commands)
    return f"{message}\n{output}"


@with_confirmation
def junglescripttool_uninstall():
    commands = "opkg remove enigma2-plugin-extensions-junglescripttool"
    return getoutput(commands)
    
@with_confirmation  
def install_epgimport():
    command = "opkg update"
    execute_os_commands(command)
    hay_epgimport = int(getoutput("opkg list-installed | grep enigma2-plugin-extensions-epgimport | wc -l"))
    if hay_epgimport > 0:
        commands = "opkg upgrade enigma2-plugin-extensions-epgimport"
        message = "epgimport esta instalado. Upgrading si procede..."
    else:
        commands = """
                    opkg remove enigma2-plugin-extensions-epgimport
                    opkg install enigma2-plugin-extensions-epgimport
                    """
        message = "Instalando epgimport..."
    output = getoutput(commands)
    return f"{message}\n{output}"


@with_confirmation
def epgimport_uninstall():
    commands = "opkg remove enigma2-plugin-extensions-epgimport"
    return getoutput(commands)
    
@with_confirmation  
def install_tdtchannels():
    command = "opkg update"
    execute_os_commands(command)
    hay_tdtchannels = int(getoutput("opkg list-installed | grep enigma2-plugin-extensions-tdtchannels | wc -l"))
    if hay_tdtchannels > 0:
        commands = "opkg upgrade enigma2-plugin-extensions-tdtchannels"
        message = "tdtchannels esta instalado. Upgrading si procede..."
    else:
        commands = """
                    opkg remove enigma2-plugin-extensions-tdtchannels
                    opkg install enigma2-plugin-extensions-tdtchannels
                    """
        message = "Instalando tdtchannels..."
    output = getoutput(commands)
    return f"{message}\n{output}"


@with_confirmation
def tdtchannels_uninstall():
    commands = "opkg remove enigma2-plugin-extensions-epgimport"
    return getoutput(commands)
    
@with_confirmation  
def install_emuoscamconclave():
    command = "opkg update"
    execute_os_commands(command)
    hay_oscamconclave = int(getoutput("opkg list-installed | grep enigma2-plugin-softcams-oscam-conclave | wc -l"))
    if hay_oscamconclave > 0:
        commands = "opkg upgrade enigma2-plugin-softcams-oscam-conclave"
        message = "oscamconclave esta instalado. Upgrading si procede..."
    else:
        commands = """
                    opkg remove enigma2-plugin-softcams-oscam-conclave
                    opkg install enigma2-plugin-softcams-oscam-conclave
                    """
        message = "Instalando oscamconclave..."
    output = getoutput(commands)
    return f"{message}\n{output}"


@with_confirmation
def emuoscamconclave_uninstall():
    commands = "opkg remove enigma2-plugin-softcams-oscam-conclave"
    return getoutput(commands)
    
@with_confirmation  
def install_skinkoala():
    distro = enigma_distro()
    if distro == openatv:
        command = "opkg update"
        execute_os_commands(command)
        hay_skinkoala = int(getoutput("opkg list-installed | grep enigma2-plugin-skins-op-artkoala | wc -l"))
        if hay_skinkoala > 0:
            commands = "opkg upgrade enigma2-plugin-skins-op-artkoala"
            message = "op-artkoala esta instalado. Upgrading si procede..."
        else:
            commands = """
                        opkg remove enigma2-plugin-skins-op-artkoala
                        opkg install enigma2-plugin-skins-op-artkoala
                        """
            message = "Instalando op-artkoala..."
    else:
        message = "No se instala, solo es compatible con imagen OpenATV"        
    output = getoutput(commands)
    return f"{message}\n{output}"


@with_confirmation
def skinkoala_uninstall():
    commands = "opkg remove enigma2-plugin-skins-op-artkoala"
    return getoutput(commands)
    

@with_confirmation  
def install_jedimaker():
    command = "opkg update"
    execute_os_commands(command)
    hay_jedimaker = int(getoutput("opkg list-installed | grep enigma2-plugin-extensions-jedimakerxtream | wc -l"))
    if hay_jedimaker > 0:
        commands = "opkg upgrade enigma2-plugin-extensions-jedimakerxtream"
        message = "jedimakerxtream esta instalado. Upgrading si procede..."
    else:
        commands = """
                    opkg remove enigma2-plugin-extensions-jedimakerxtream
                    opkg install enigma2-plugin-extensions-jedimakerxtream
                    """
        message = "Instalando jedimakerxtream..."
    output = getoutput(commands)
    return f"{message}\n{output}"


@with_confirmation
def jedimaker_uninstall():
    commands = "opkg remove enigma2-plugin-extensions-jedimakerxtream"
    return getoutput(commands)
    
@with_confirmation  
def install_openvpn():
    command = "opkg update"
    execute_os_commands(command)
    hay_openvpn = int(getoutput("opkg list-installed | grep openvpn | wc -l"))
    if hay_openvpn > 0:
        commands = "opkg upgrade openvpn"
        message = "openvpn esta instalado. Upgrading si procede..."
    else:
        commands = """
                    opkg remove openvpn
                    opkg install openvpn
                    """
        message = "Instalando openvpn..."
    output = getoutput(commands)
    return f"{message}\n{output}"


@with_confirmation
def openvpn_uninstall():
    commands = "opkg remove openvpn"
    return getoutput(commands)
    
def change_password(change):
    commands = "echo 'root:{}' | chpasswd".format(change)
    execute_os_commands(commands)
    return i18n.t('msg.change_password_ok')
    
def programar_tarea_cron(comando, tiempo):
    output = []
    cron = CronTab(user='root')
    args = shlex.split("/" + comando)
    command = " ".join([shlex.quote(arg) for arg in args])
    job = cron.new(command=command)
    job.setall(tiempo)
    cron.write()
    output.append("Tarea cron programada exitosamente")
    return "\n".join(output)
    
@with_confirmation    
def install_jediepgxtream():
    command = "opkg update"
    execute_os_commands(command)
    hay_jediepgxtream = int(getoutput("opkg list-installed | grep enigma2-plugin-extensions-jediepgxtream | wc -l"))
    if hay_jediepgxtream > 0:
        commands = "opkg upgrade enigma2-plugin-extensions-jediepgxtream"
        message = "jediepgxtream esta instalado. Upgrading si procede..."
    else:
        repo_jediepgxtream = int(getoutput("opkg list | grep enigma2-plugin-extensions-jedimakerxtream | wc -l"))
        if repo_jediepgxtream > 0:
            commands = """
                        opkg remove enigma2-plugin-extensions-jediepgxtream
                        opkg install enigma2-plugin-extensions-jediepgxtream
                        """
            message = "Instalando jediepgxtream..."
        else:
            message = "El paquete jediepgxtream no se encuentra en los repositorios."
            commands = ""
    output = getoutput(commands)
    return f"{message}\n{output}"
    
@with_confirmation
def jediepgxtream_uninstall():
    commands = "opkg remove enigma2-plugin-extensions-jediepgxtream"
    return getoutput(commands)
    
@with_confirmation    
def install_footonsat():
    command = "opkg update"
    execute_os_commands(command)
    hay_footonsat = int(getoutput("opkg list-installed | grep enigma2-plugin-extensions-footonsat | wc -l"))
    if hay_footonsat > 0:
        message = "footonsat ya esta instalado"
        output = ""
    else:
        command = 'wget -q --no-check-certificate https://raw.githubusercontent.com/ziko-ZR1/FootOnsat/main/Download/install.sh -O - | /bin/sh'
        subprocess.run(command, shell=True, check=True)
        message = "Instalando footonsat..."
        output = getoutput(command)
    return f"{message}\n{output}"

    
@with_confirmation
def footonsat_uninstall():
    commands = "opkg remove enigma2-plugin-extensions-footonsat"
    return getoutput(commands)

def list_bouquets():
    output = []
    index_rec = 0
    j = webif_api("getservices")
    services = j['services']
    for s in services:	
        output.append(str(index_rec) + " - " + s['servicename'])
        index_rec = index_rec + 1
    return "\n".join(output)

def descarga_m3u(index_bouquet):
    j = webif_api("getservices")
    if j['services']:
        tamano = len(j['services'])
        indice = int(index_bouquet)
        salida = "Bouquet no existe"
        if indice <= tamano:
            if j['services'][indice]:
                bouquet_ref = j['services'][indice]['servicereference']
                bouquet_name = j['services'][indice]['servicename']
                url = "http://{}/web/services.m3u?bRef={}&bName={}".format(obtener_ip_deco(), bouquet_ref, bouquet_name)
            response = requests.get(url)
            if response.status_code == 200:
                archivo_m3u = "/tmp/{}.m3u".format(bouquet_name)
                with open(archivo_m3u, "wb") as f:
                    f.write(response.content)
                if os.path.exists(archivo_m3u):
                    bot.send_document(G_CONFIG['chat_id'], open(archivo_m3u, 'rb'))
                    getoutput("rm -f '{}'".format(archivo_m3u))
                else:
                    bot.send_message(G_CONFIG['chat_id'], i18n('msg.command_not_found'))

# MAIN
menu_info = MenuOption(name = 'info', description = i18n.t('menu.info.title'))
menu_info.add_option(MenuOption(name = "channel", description = i18n.t('menu.info.channel'), command = info_channel))
menu_info.add_option(MenuOption(name = "sistema", description = i18n.t('menu.info.system'), command = system_info))
menu_info.add_option(MenuOption(name = "machineid", description = i18n.t('menu.info.machineid'), command = info_machineid))
menu_info.add_option(MenuOption(name = "top", description = i18n.t('menu.info.top'), command = info_top))
menu_info.add_option(MenuOption(name = "estado_receptor", description = i18n.t('menu.info.estado_receptor'), command = remotecontrol_status))
menu_info.add_option(MenuOption(name = "plugin_instalados", description = i18n.t('menu.info.plugin_installed'), command = plugin_instalados))
menu_info.add_option(MenuOption(name = "tareas_crontab", description = i18n.t('menu.info.crontab_info'), command = crontab_tareas))
menu_info.add_option(MenuOption(name = "get_ram", description = i18n.t('menu.info.ram_info'), command = get_ram_disponible))
menu_info.add_option(MenuOption(name = "get_cpu", description = i18n.t('menu.info.cpu_uso'), command = get_cpu_uso))
menu_info.add_option(MenuOption(name = "get_emmc", description = i18n.t('menu.info.emmc_uso'), command = get_disco_interno_disponible))
menu_info.add_option(MenuOption(name = "get_montajes", description = i18n.t('menu.info.puntos_montaje'), command = get_puntos_de_montaje))
menu_info.add_option(MenuOption(name = "get_bytes", description = i18n.t('menu.info.bytes'), command = get_bytes_red))
menu_info.add_option(MenuOption(name = "get_conexiones", description = i18n.t('menu.info.conexiones'), command = get_conexiones_de_red))
menu_info.add_option(MenuOption(name = "get_maxprocesos", description = i18n.t('menu.info.maxproceso'), command = get_proceso_con_mas_consumo))
menu_info.add_option(MenuOption(name = "get_interfacered", description = i18n.t('menu.info.interfazred'), command = get_interfaces_de_red_activas))
menu_info.add_option(MenuOption(name = "get_dmesg", description = i18n.t('menu.info.dmesg'), command = get_dmesg))

menu_jungle = MenuOption(name = 'jungle', description = i18n.t('menu.jungle.title'))
menu_ghostreamy = MenuOption(name = 'ghostreamy', description = i18n.t('menu.ghostreamy.title'))
menu_ghostreamy.add_option(MenuOption(name = "status", description = i18n.t('menu.ghostreamy.status'), command = ghostreamy_status))
menu_ghostreamy.add_option(MenuOption(name = "stop", description = i18n.t('menu.ghostreamy.stop'), command = ghostreamy_stop))
menu_ghostreamy.add_option(MenuOption(name = "start", description = i18n.t('menu.ghostreamy.start'), command = ghostreamy_start))
menu_ghostreamy.add_option(MenuOption(name = "restart", description = i18n.t('menu.ghostreamy.restart'), command = ghostreamy_restart))
menu_ghostreamy.add_option(MenuOption(name = "config", description = i18n.t('menu.ghostreamy.config'), command = lambda : config("/etc/enigma2/ghostreamy.env")))
menu_ghostreamy.add_option(MenuOption(name = "set_config", description = i18n.t('menu.ghostreamy.set_config'), command = lambda x,y: set_value("/etc/enigma2/ghostreamy.env", x,y), params=['clave', 'valor']))
menu_ghostreamy.add_option(MenuOption(name = "ver_log", description = i18n.t('menu.ghostreamy.log'), command = ghostreamy_log))
menu_ghostreamy.add_option(MenuOption(name = "ver_version", description = i18n.t('menu.ghostreamy.version'), command = ghostreamy_version))
menu_junglebot = MenuOption(name = 'junglebot', description = i18n.t('menu.junglebot.title'), info = 'https://jungle-team.com/junglebotv2-telegram-enigma2/')
menu_junglebot.add_option(MenuOption(name = "config", description = i18n.t('menu.junglebot.config'), command = lambda : config("/usr/bin/junglebot/parametros.py")))
menu_junglebot.add_option(MenuOption(name = "set_config_parameters", description = i18n.t('menu.junglebot.set_config'), command = set_value_parameters, params =['clave', 'valor']))
menu_junglebot.add_option(MenuOption(name = "update", description = i18n.t('menu.junglebot.update'), command = junglebot_update, params=params_confirmation))
menu_junglebot.add_option(MenuOption(name = "reboot", description = i18n.t('menu.junglebot.reboot'), command = junglebot_restart, params=params_confirmation))
menu_junglebot.add_option(MenuOption(name = "log", description = i18n.t('menu.junglebot.log'), command = junglebot_log))
menu_junglebot.add_option(MenuOption(name = "purgelog", description = i18n.t('menu.junglebot.purge_log'), command = junglebot_purge_log))
menu_junglebot.add_option(MenuOption(name = "changelog", description = i18n.t('menu.junglebot.changelog'), command = junglebot_changelog))
menu_junglescript = MenuOption(name = 'junglescript', description = i18n.t('menu.junglescript.title'), info  ='https://jungle-team.com/junglescript-lista-canales-y-picon-enigma2-movistar/')
menu_junglescript.add_option(MenuOption(name = "config", description = i18n.t('menu.junglescript.config'), command = lambda : config("/usr/bin/enigma2_pre_start.conf")))
menu_junglescript.add_option(MenuOption(name = "set_config", description = i18n.t('menu.junglescript.set_config'), command = lambda x, y: set_value("/usr/bin/enigma2_pre_start.conf", x,y), params =['clave', 'valor']))
menu_junglescript.add_option(MenuOption(name = "show_version", description = i18n.t('menu.junglescript.version'), command = junglescript_version))
menu_junglescript.add_option(MenuOption(name = "run", description = i18n.t('menu.junglescript.run'), command = junglescript_run, params=params_confirmation))
menu_junglescript.add_option(MenuOption(name = "force_channels", description = i18n.t('menu.junglescript.force_channels'), command = junglescript_channels, params=params_confirmation))
menu_junglescript.add_option(MenuOption(name = "force_picons", description = i18n.t('menu.junglescript.force_picons'), command = junglescript_picons, params=params_confirmation))
menu_junglescript.add_option(MenuOption(name = "log", description = i18n.t('menu.junglescript.log'), command = junglescript_log))
menu_junglescript.add_option(MenuOption(name = "ver_fecha_lista", description = i18n.t('menu.junglescript.channel_list'), command = junglescript_fecha_listacanales))
menu_junglescript.add_option(MenuOption(name = "ver_fecha_picons", description = i18n.t('menu.junglescript.picon_list'), command = junglescript_fecha_picons))
menu_junglescript.add_option(MenuOption(name = "addbouquetfav", description = i18n.t('menu.junglescript.add_bouquet'), command = junglescript_addfavbouquet, params=['bouquet']))
menu_junglescript.add_option(MenuOption(name = "delbouquetfav", description = i18n.t('menu.junglescript.del_bouquet'), command = junglescript_delfavbouquet, params=[[JB_BUTTONS, lambda: zip(junglescript_fav_bouquets(), junglescript_fav_bouquets())]]))
menu_junglescript.add_option(MenuOption(name = "addbouquetsave", description = i18n.t('menu.junglescript.add_save_bouquet'), command = junglescript_addsavebouquet, params=['bouquet']))
menu_junglescript.add_option(MenuOption(name = "delbouquetsave", description = i18n.t('menu.junglescript.del_save_bouquet'), command = junglescript_delsavebouquet, params=[[JB_BUTTONS, lambda: zip(junglescript_save_bouquets(), junglescript_save_bouquets())]]))
menu_jungle.add_option(MenuOption(name = "backupjungleconfigs", description = i18n.t('menu.command.backup_jungle_configs'), command = backup_jungle_configs))
menu_speedy = MenuOption(name = 'speedy', description = i18n.t('menu.speedy.title'))
menu_speedy.add_option(MenuOption(name = "install_feed_jungle", description = i18n.t('menu.speedy.feedjungle'), command = repo_jungle_install, params=params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_feed_Oe", description = i18n.t('menu.speedy.feedoe'), command = repo_oeAlliance, params=params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_junglescript", description = i18n.t('menu.speedy.install_junglescript'), command = junglescript_install, params=params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_junglescript", description = i18n.t('menu.speedy.uninstall_junglescript'), command = junglescript_uninstall, params=params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_ghostreamy", description = i18n.t('menu.speedy.install_ghostreamy'), command = ghostreamy_install, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_ghostreamy", description = i18n.t('menu.speedy.uninstall_ghostreamy'), command = ghostreamy_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_jungletools", description = i18n.t('menu.speedy.install_jungletools'), command = install_junglescripttool, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_jungletools", description = i18n.t('menu.speedy.uninstall_jungletools'), command = junglescripttool_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_epgimport", description = i18n.t('menu.speedy.install_epgimport'), command = install_epgimport, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_epgimport", description = i18n.t('menu.speedy.uninstall_epgimport'), command = epgimport_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_tdtchannels", description = i18n.t('menu.speedy.install_tdtchannels'), command = install_tdtchannels, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_tdtchannels", description = i18n.t('menu.speedy.uninstall_tdtchannels'), command = tdtchannels_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_oscamconclave", description = i18n.t('menu.speedy.install_oscamconclave'), command = install_emuoscamconclave, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_oscamconclave", description = i18n.t('menu.speedy.uninstall_oscamconclave'), command = emuoscamconclave_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_skinkoala", description = i18n.t('menu.speedy.install_skinkoala'), command = install_skinkoala, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_skinkoala", description = i18n.t('menu.speedy.uninstall_skinkoala'), command = skinkoala_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_jedimaker", description = i18n.t('menu.speedy.install_jedimaker'), command = install_jedimaker, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_jedimaker", description = i18n.t('menu.speedy.uninstall_jedimaker'), command = jedimaker_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_openvpn", description = i18n.t('menu.speedy.install_openvpn'), command = install_openvpn, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_openvpn", description = i18n.t('menu.speedy.uninstall_openvpn'), command = openvpn_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "zerotier_install", description = i18n.t('menu.speedy.install_zerotier'), command = zerotier_install, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "zerotier_uninstall", description = i18n.t('menu.speedy.uninstall_zerotier'), command = zerotier_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "tailscale_install", description = i18n.t('menu.speedy.install_tailscale'), command = tailscale_install, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "tailscale_uninstall", description = i18n.t('menu.speedy.uninstall_tailscale'), command = tailscale_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_jediepgxtream", description = i18n.t('menu.speedy.install_jediepgxtream'), command = install_jediepgxtream, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_jediepgxtream", description = i18n.t('menu.speedy.uninstall_jediepgxtream'), command = jediepgxtream_uninstall, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "install_footonsat", description = i18n.t('menu.speedy.install_footonsat'), command = install_footonsat, params = params_confirmation))
menu_speedy.add_option(MenuOption(name = "uninstall_footonsat", description = i18n.t('menu.speedy.uninstall_footonsat'), command = footonsat_uninstall, params = params_confirmation))
menu_jungle.add_option(menu_ghostreamy)
menu_jungle.add_option(menu_junglebot)
menu_jungle.add_option(menu_junglescript)
menu_jungle.add_option(menu_speedy )


menu_redes = MenuOption(name = 'redes', description = i18n.t('menu.redes.title'))
menu_network = MenuOption(name='network', description=i18n.t('menu.network.title'))
menu_network.add_option(MenuOption(name='status', description=i18n.t('menu.network.status'), command=network_status))
menu_network.add_option(MenuOption(name='connections', description=i18n.t('menu.network.connections'), command=info_conexiones))
menu_network.add_option(MenuOption(name='speedtest', description=i18n.t('menu.network.speedtest'), command=info_speedtest, params=[[JB_BUTTONS, lambda: info_speedtest_options()]]))
menu_network.add_option(MenuOption(name='check_duckdns_ip', description=i18n.t('menu.network.check_duckdns_ip'), command=info_check_duckdns_ip, params=['host']))
menu_network.add_option(MenuOption(name='check_open_port', description=i18n.t('menu.network.check_open_port'), command=info_check_open_port, params=['host', 'port']))
menu_network.add_option(MenuOption(name='geolocate_ip', description=i18n.t('menu.network.geolocate'), command=geolocalizar_ip, params=['geolocalizar']))
menu_network.add_option(MenuOption(name='block_ip', description=i18n.t('menu.network.block_ip'), command=bloquear_ip, params=['bloquear']))
menu_network.add_option(MenuOption(name='unblock_ip', description=i18n.t('menu.network.unblock_ip'), command=desbloquear_ip, params=[[JB_BUTTONS, lambda: zip(rejected_ips(), rejected_ips())]]))
menu_network.add_option(MenuOption(name='show_blocked_ips', description=i18n.t('menu.network.show_blocked_ips'), command=mostrar_ip))
menu_stream = MenuOption(name = 'stream', description = i18n.t('menu.stream.title'))
menu_stream.add_option(MenuOption(name = "ver", description = i18n.t('menu.stream.show'), command = cotillearamigos))
menu_stream.add_option(MenuOption(name = "amigos", description = i18n.t('menu.stream.friends'), command = amigos))
menu_stream.add_option(MenuOption(name = "addamigo", description = i18n.t('menu.stream.add_friend'), command = stream_addamigo, params=['ip / ghostreamy:usuario']))
menu_stream.add_option(MenuOption(name = "delamigo", description = i18n.t('menu.stream.delete_friend'), command = stream_delamigo, params=[[JB_BUTTONS, lambda: zip(stream_amigos(), stream_amigos())]]))
menu_stream.add_option(MenuOption(name = "autocheck", description = i18n.t('menu.stream.autocheck'), command = stream_autocheck, params=params_confirmation))
menu_stream.add_option(MenuOption(name = "stopstream", description = i18n.t('menu.stream.stop_streamproxy'), command = command_stopstream))
menu_stream.add_option(MenuOption(name = "listar_instrusos", description = i18n.t('menu.stream.intruders_list'), command = intrusos))
menu_stream.add_option(MenuOption(name = "delinstruso", description = i18n.t('menu.stream.delete_intruder'), command = stream_delintruso, params=[[JB_BUTTONS, lambda: zip(stream_intrusos(), stream_intrusos())]]))
menu_conexiones = MenuOption(name = 'conexiones', description = i18n.t('menu.connections.title'))
menu_conexiones.add_option(MenuOption(name = "ssh", description = i18n.t('menu.connections.ssh'), command = controlssh))
menu_conexiones.add_option(MenuOption(name = "ftp", description = i18n.t('menu.connections.ftp'), command = controlftp))
menu_conexiones.add_option(MenuOption(name = "autossh", description = i18n.t('menu.connections.autossh'), command = conn_autossh, params=params_confirmation))
menu_conexiones.add_option(MenuOption(name = "autoftp", description = i18n.t('menu.connections.autoftp'), command = conn_autoftp, params=params_confirmation))
menu_vpn = MenuOption(name = 'vpn', description = i18n.t('menu.vpn.title'))
menu_zerotier = MenuOption(name = 'zerotier', description = i18n.t('menu.zerotier.title'))
menu_zerotier.add_option(MenuOption(name = "zerotier_status", description = i18n.t('menu.zerotier.status'), command = zerotier_status))
menu_zerotier.add_option(MenuOption(name = "zerotier_start", description = i18n.t('menu.zerotier.start'), command = zerotier_start))
menu_zerotier.add_option(MenuOption(name = "zerotier_stop", description = i18n.t('menu.zerotier.stop'), command = zerotier_stop))
menu_zerotier.add_option(MenuOption(name = "zerotier_force_reload", description = i18n.t('menu.zerotier.force_reload'), command = zerotier_force_reload))
menu_zerotier.add_option(MenuOption(name = "zerotier_join", description = i18n.t('menu.zerotier.join'), command = zerotier_join_network, params=['network id']))
menu_zerotier.add_option(MenuOption(name = "zerotier_leave", description = i18n.t('menu.zerotier.leave'), command = zerotier_leave_network, params=['network id']))
menu_tailscale = MenuOption(name = 'tailscale', description = i18n.t('menu.tailscale.title'))
menu_tailscale.add_option(MenuOption(name = "tailscale_up", description = i18n.t('menu.tailscale.up'), command = tailscale_up))
menu_tailscale.add_option(MenuOption(name = "tailscale_down", description = i18n.t('menu.tailscale.down'), command = tailscale_down))
menu_tailscale.add_option(MenuOption(name = "tailscale_ip", description = i18n.t('menu.tailscale.ip'), command = tailscale_ip))
menu_tailscale.add_option(MenuOption(name = "tailscale_status", description = i18n.t('menu.tailscale.status'), command = tailscale_status))
menu_vpn.add_option(menu_zerotier)
menu_vpn.add_option(menu_tailscale)
menu_redes.add_option(menu_network)
menu_redes.add_option(menu_stream)
menu_redes.add_option(menu_conexiones)
menu_redes.add_option(menu_vpn)

menu_gestion = MenuOption(name = 'gestion', description = i18n.t('menu.gestion.title'))
menu_gestion.add_option(MenuOption(name = "runcommand", description = i18n.t('menu.command.exec_command'), command = command_runcommand, params=['comando']))
menu_command = MenuOption(name = 'command', description = i18n.t('menu.command.title'))
menu_command.add_option(MenuOption(name = "freeram", description = i18n.t('menu.command.freeram'), command = command_freeram))
menu_command.add_option(MenuOption(name = "update", description = i18n.t('menu.command.update'), command = command_update))
menu_command.add_option(MenuOption(name = "upgrade", description = i18n.t('menu.command.upgrade'), command = command_upgrade, params=params_confirmation))
menu_command.add_option(MenuOption(name = "restaurar", description = i18n.t('menu.command.factory_reset'), command = command_restaurar, params=params_confirmation))
menu_command.add_option(MenuOption(name = "resetpass", description = i18n.t('menu.command.resetpass'), command = command_resetpass, params=params_confirmation))
menu_command.add_option(MenuOption(name = "getfile", description = i18n.t('menu.command.get_file'), command = file_download, params=['path del fichero sin la primera barra de la ruta, ej: tmp/oscam.log']))
menu_command.add_option(MenuOption(name='change_password', description=i18n.t('menu.command.change_password'), command=change_password, params=['change']))
menu_command.add_option(MenuOption(name = "cron_tarea_programada", description = i18n.t('menu.command.cron_tarea_programada'), command = programar_tarea_cron, params =['comando a programar sin usar primera /, ejem: usr/bin/python /etc/miscript.py', 'de cuando quieres que se ejecute, ejm: 30']))
menu_command.add_option(MenuOption(name = "list_bouquets", description = i18n.t('menu.command.list_bouquets'), command = list_bouquets))
menu_command.add_option(MenuOption(name = "descarga_m3u", description = i18n.t('menu.command.descarga_m3u'), command = descarga_m3u, params =['Numero de la lista de bouquets']))
menu_grabaciones = MenuOption(name = 'grabaciones', description = i18n.t('menu.records.title'))
menu_grabaciones.add_option(MenuOption(name = "listado_timers", description = i18n.t('menu.records.list'), command = list_recording_timers))
menu_grabaciones.add_option(MenuOption(name = "borrar_timer", description = i18n.t('menu.records.delete'), command = delete_timer, params=params_confirmation))
menu_grabaciones.add_option(MenuOption(name = "limpiar_timers", description = i18n.t('menu.records.clean'), command = clean_expired_timers, params=params_confirmation))
menu_grabaciones.add_option(MenuOption(name = "grabar_ahora", description = i18n.t('menu.records.save'), command = record_now))
menu_grabaciones.add_option(MenuOption(name = "listado_ficher_grabacion", description = i18n.t('menu.records.file_list'), command = list_recordings))
menu_grabaciones.add_option(MenuOption(name = "borrado_ficher_grabacion", description = i18n.t('menu.records.delete_file'), command = delete_recordings, params =["indice"]))
menu_grabaciones.add_option(MenuOption(name = "borrado_completo_grabaciones", description = i18n.t('menu.records.delete_all'), command = delete_all_recordings, params=params_confirmation))
menu_grabaciones.add_option(MenuOption(name = "show_path_grabaciones", description = i18n.t('menu.records.path'), command = show_path_recordings))
menu_epg = MenuOption(name = 'epg', description = i18n.t('menu.epg.title'))
menu_epg.add_option(MenuOption(name = "listar_ruta_epg", description = i18n.t('menu.epg.path_epg'), command = find_epg_dat))
menu_epg.add_option(MenuOption(name = "listar_fecha_epg", description = i18n.t('menu.epg.date_epg'), command = find_date_epg_dat))
menu_epg.add_option(MenuOption(name = "update_epg", description = i18n.t('menu.epg.update_epg'), command = update_epg, params =["dias (3, 7, 15 o 30)"]))
menu_epg.add_option(MenuOption(name = "borrar_epg", description = i18n.t('menu.epg.del_epg'), command = delete_epg_dat, params=params_confirmation))
menu_epg.add_option(MenuOption(name = "reiniciar_interfaz", description = i18n.t('menu.epg.restart_gui'), command = remotecontrol_restartgui, params=params_confirmation))
menu_epg.add_option(MenuOption(name = "desinstalar_epgimport", description = i18n.t('menu.epg.uninstall_epgimport'), command = remove_epgimport, params=params_confirmation))
menu_epg.add_option(MenuOption(name = "desinstalar_crossepg", description = i18n.t('menu.epg.uninstall_crossepg'), command = remove_crossepg, params=params_confirmation))
menu_gestion.add_option(menu_command)
menu_gestion.add_option(menu_grabaciones)
menu_gestion.add_option(menu_epg)

menu_emu = MenuOption(name='emu', description= i18n.t('menu.emu.title'), info = 'https://jungle-team.com/conclave-oscam-autoupdate/')
menu_emu.add_option(MenuOption(name = "status", description = i18n.t('menu.emu.status'), command = emucam_status))
menu_emu.add_option(MenuOption(name = "list_emus", description = i18n.t('menu.emu.show_installed_emus'), command = list_installed_emus))
menu_emu.add_option(MenuOption(name="addlineacccam", description=i18n.t('menu.emu.addlinecccam'), command=addlinea_cccam, params=['clinea (C: servidor puerto usuario password)']))
menu_emu.add_option(MenuOption(name = "dellineacccam", description = i18n.t('menu.emu.dellinecccam'), command = dellinea_cccam, params=[[JB_BUTTONS, lambda: zip(list_lines_cccam(), list_lines_cccam())]]))
menu_emu.add_option(MenuOption(name = "addlineoscam", description = i18n.t('menu.emu.addlineoscam'), command = addlinea_oscam, params=['protocolo', 'label', 'clinea (C: servidor puerto usuario password)']))
menu_emu.add_option(MenuOption(name = "dellineoscam", description = i18n.t('menu.emu.dellineoscam'), command = deletelineaoscam, params=[[JB_BUTTONS, lambda: zip(list_readers_oscam(), list_readers_oscam())]]))
menu_emu.add_option(MenuOption(name = "activatelineoscam", description = i18n.t('menu.emu.enablelineoscam'), command = enable_reader_oscam, params=[[JB_BUTTONS, lambda: zip(list_disabled_readers_oscam(), list_disabled_readers_oscam())]]))
menu_emu.add_option(MenuOption(name = "deactivatelineoscam", description = i18n.t('menu.emu.disablelineoscam'), command = disable_reader_oscam, params=[[JB_BUTTONS, lambda: zip(list_enabled_readers_oscam(), list_enabled_readers_oscam())]]))
menu_emu.add_option(MenuOption(name = "start", description = i18n.t('menu.emu.start'), command = oscam_start))
menu_emu.add_option(MenuOption(name = "stop", description = i18n.t('menu.emu.stop'), command = oscam_stop))
menu_emu.add_option(MenuOption(name = "restart", description = i18n.t('menu.emu.restart'), command = oscam_restart))
menu_emu.add_option(MenuOption(name = "install_oscam_conclave", description = i18n.t('menu.emu.install_conclave'), command = install_oscam_conclave, params=params_confirmation))
menu_emu.add_option(MenuOption(name = "update_autooscam", description = i18n.t('menu.emu.update_autooscam'), command = update_autooscam, params=params_confirmation))
menu_emu.add_option(MenuOption(name = "run_autooscam", description = i18n.t('menu.emu.run_autooscam'), command = run_autooscam, params=params_confirmation))
menu_emu.add_option(MenuOption(name = "force_autooscam", description = i18n.t('menu.emu.force_autooscam'), command = force_autooscam, params=params_confirmation))
menu_emu.add_option(MenuOption(name = "change_active_emu", description = i18n.t('menu.emu.activate_emu'), command = set_active_emu, params=[[JB_BUTTONS, lambda: zip(emu_list(), emu_list())]]))

menu_remotecontrol = MenuOption(name = 'remotecontrol', description = i18n.t('menu.remotecontrol.title'))
menu_remotecontrol.add_option(MenuOption(name = "standby_wakeup", description = i18n.t('menu.remotecontrol.standby_wakeup'), command = remotecontrol_standby_wakeup))
menu_remotecontrol.add_option(MenuOption(name = "status", description = i18n.t('menu.remotecontrol.status'), command = remotecontrol_status))
menu_remotecontrol.add_option(MenuOption(name = "reboot", description = i18n.t('menu.remotecontrol.reboot'), command = remotecontrol_reboot, params=params_confirmation))
menu_remotecontrol.add_option(MenuOption(name = "reboot_enigma2", description = i18n.t('menu.remotecontrol.restartgui'), command = remotecontrol_restartgui, params=params_confirmation))
menu_remotecontrol.add_option(MenuOption(name = "screenshot", description = i18n.t('menu.remotecontrol.screenshot'), command = remotecontrol_screenshot))
menu_remotecontrol.add_option(MenuOption(name = "send_message", description = i18n.t('menu.remotecontrol.send_message'), command = remotecontrol_send_message, params=['mensaje']))
menu_remotecontrol.add_option(MenuOption(name = "send_menu", description = i18n.t('menu.remotecontrol.menu'), command = remotecontrol_send_menu))
menu_remotecontrol.add_option(MenuOption(name = "send_exit", description = i18n.t('menu.remotecontrol.exit'), command = remotecontrol_send_exit))
menu_remotecontrol.add_option(MenuOption(name = "send_up", description = i18n.t('menu.remotecontrol.up'), command = remotecontrol_send_up))
menu_remotecontrol.add_option(MenuOption(name = "send_down", description = i18n.t('menu.remotecontrol.down'), command = remotecontrol_send_down))
menu_remotecontrol.add_option(MenuOption(name = "send_left", description = i18n.t('menu.remotecontrol.left'), command = remotecontrol_send_left))
menu_remotecontrol.add_option(MenuOption(name = "send_right", description = i18n.t('menu.remotecontrol.right'), command = remotecontrol_send_right))
menu_remotecontrol.add_option(MenuOption(name = "send_ok", description = i18n.t('menu.remotecontrol.ok'), command = remotecontrol_send_ok))
menu_remotecontrol.add_option(MenuOption(name = "send_digit", description = i18n.t('menu.remotecontrol.digit'), command = remotecontrol_send_digit, params=['digito']))
menu_remotecontrol.add_option(MenuOption(name = "send_red", description = i18n.t('menu.remotecontrol.red'), command = remotecontrol_send_red))
menu_remotecontrol.add_option(MenuOption(name = "send_green", description = i18n.t('menu.remotecontrol.green'), command = remotecontrol_send_green))
menu_remotecontrol.add_option(MenuOption(name = "send_yellow", description = i18n.t('menu.remotecontrol.yellow'), command = remotecontrol_send_yellow))
menu_remotecontrol.add_option(MenuOption(name = "send_blue", description = i18n.t('menu.remotecontrol.blue'), command = remotecontrol_send_blue))
menu_remotecontrol.add_option(MenuOption(name = "change_channel", description = i18n.t('menu.remotecontrol.change_channel'), command = remotecontrol_change_channel, params=['canal']))
menu_remotecontrol.add_option(MenuOption(name = "send_mute", description = i18n.t('menu.remotecontrol.mute'), command = remotecontrol_send_mute))
menu_remotecontrol.add_option(MenuOption(name = "send_vol_up", description = i18n.t('menu.remotecontrol.volume_up'), command = remotecontrol_send_vol_up))
menu_remotecontrol.add_option(MenuOption(name = "send_vol_down", description = i18n.t('menu.remotecontrol.volume_down'), command = remotecontrol_send_vol_down))

menu_ayuda = MenuOption(name = 'ayuda', description = i18n.t('menu.help.title'))

g_menu = [menu_ayuda, menu_info, menu_gestion, menu_emu, menu_remotecontrol, menu_redes, menu_jungle]   
g_current_menu_option = None

if __name__ == "__main__":
    try:
        logger.info('junglebot esta funcionando...' + VERSION)
        send_large_message(G_CONFIG['chat_id'], i18n.t('msg.boot_info') + VERSION)
        check_version()
        inicializar_intrusos()
        cargar_ips_bloquedas()
        start_autostream()
        start_autossh()
        start_autoftp()
        start_autoram()
        start_autotemp()
        start_autoflash()
        fill_command_list()
    except Exception as e:
        logger.exception(e)
    bot.infinity_polling()

