#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import time
import os
from os import path
import commands
from commands import *
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
from StringIO import StringIO
import re
from netaddr import *
import logging
import urllib
import i18n

VERSION="2.5.8"   
CONFIG_FILE = '/usr/bin/junglebot/parametros.py' 
GA_ACCOUNT_ID = 'UA-178274579-1'
VTI="VTi"
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
@bot.message_handler(commands=['inicio'])
def command_inicio(m):
    if allowed(m):
        identificacion = m.chat.id
        alias_permitidos[identificacion] = 0
        time.sleep(1)
        bot.send_photo(identificacion, photo=open('/usr/bin/junglebot/images/logojungle.jpeg', 'rb'))
        bot.send_message(identificacion, i18n.t('msg.init') + "\n")

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
        bot.send_message(identificacion, i18n.t('msg.text_help', version=VERSION, brand=brand, telegram_url=telegram_url) + help, parse_mode='html')
    
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
                ga('command', command)
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
    commands = """
            curl https://raw.githubusercontent.com/jungla-team/junglebot/master/bot.py > /tmp/bot.py
            """
    execute_os_commands(commands)
    version_github = getoutput("grep -i VERSION= /tmp/bot.py | cut -d'=' -f2 | head -n 1").strip()
    version_github = version_github.replace('"','').strip()
    n_VERSION = VERSION.replace(".","")
    n_version_github = version_github.replace(".","")
    if n_version_github > n_VERSION:
        new_version = True
        logger.info('Existe nueva versión de Junglebot {}'.format(version_github))
        bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.new_version', version=version_github))
    execute_os_commands("rm -f /tmp/bot.py")
    
def ga(action, label):
    try:
        if not G_CONFIG['ga']:
            return
        tracking_id = GA_ACCOUNT_ID
        client_id = int(machine_id()[-6:], 16)
        data = { 'v': 1, 'aip': 1, 'ua': "Mozilla/5.0",
                'tid': tracking_id, 'cid': client_id, 
                't': 'event', 'ec': 'bot', 'ea': action, 'el': label }
        requests.post( url="https://www.google-analytics.com/collect", params=data)
    except Exception as e:
        logger.warning("GA: " + str(e))


def machine_id():
    return getoutput("cat /etc/machine-id")

# COMMANDS

# PYSTREAMY
def pystreamy_stop():
    return execute_os_commands("/etc/init.d/pystreamy stop", i18n.t('msg.pystreamy_stop'))

def pystreamy_start():
    return execute_os_commands("/etc/init.d/pystreamy start", i18n.t('msg.pystreamy_start'))

def pystreamy_restart():
    return execute_os_commands("/etc/init.d/pystreamy restart", i18n.t('msg.pystreamy_restart'))

@with_confirmation
def pystreamy_install():
    commands = """
                curl https://gitlab.com/amoyse/pystreamy/-/raw/master/pystreamy_all.ipk?inline=false >  /tmp/pystreamy_all.ipk
                opkg install --force-reinstall --force-overwrite /tmp/pystreamy_all.ipk
                """
    return execute_os_commands(commands)

def pystreamy_status(quiet = False):
    # HACK ps comamnd arguments
    command = "ps -l"
    output = execute_os_commands(command)
    command = "ps -ef"
    output = output + execute_os_commands(command)
    running = False
    for line in output.split('\n'):
        if line.find("/usr/sbin/pystreamy.py") >= 0:
            running = True
            break
    if quiet:
        return running
    if running:
        return i18n.t('msg.pystreamy_started')
    else:
        return i18n.t('msg.pystreamy_stopped')

@with_confirmation
def pystreamy_uninstall():
    commands = """
            opkg remove --force-remove pystreamy
            echo 'Deleted file /etc/enigma2/pystreamy.conf'
            rm /etc/enigma2/pystreamy.conf
            """ 
    return execute_os_commands(commands)
    
def pystreamy_check_config(file_path):
    config = read_config_file(file_path)
    params = { key: value for (key, value) in config }
    output = []
    deco_ip = params.get('deco_ip')
    real_deco_ip = obtener_ip_deco()
    output.append(i18n.t('msg.check_ip_deco'))
    if deco_ip != real_deco_ip:
        output.append(i18n.t('msg.check_ip_deco_error', deco_ip=deco_ip, real_ip=real_deco_ip))
    else:
        output.append(i18n.t('msg.ok'))
    scheme = params.get('ext_scheme')
    if scheme and scheme.strip():
        host = params.get('ext_host')
        port = params.get('ext_port')
        certfile = params.get('certfile')
        output.append(i18n.t('msg.check_certs'))
        output.append(letsencrypt_status(certfile))
        output.append(i18n.t('msg.check_external_ip'))
        output.append(info_check_duckdns_ip(host))
        output.append(i18n.t('msg.check_external_port'))
        output.append(info_check_open_port(host, port))
        user = params.get('user')
        password = params.get('password')
        if user:
            if not password:
                output.append(i18n.t('msg.wrong_password'))
    else:
        output.append(i18n.t('msg.wrong_external_access'))

    return "\n".join(output)

def pystreamy_log():
    get_file("/var/log/pystreamy.log")
    
def config(file_path):
    return execute_os_commands("cat {}".format(file_path))

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
        bot.send_message(G_CONFIG['chat_id'], i18n.t("msg.file_notfound", file=filepath))
    return ''

# LETSENCRYPT
def letsencrypt_status(cert_file):
    return "Checking certificate {}\n{}".format(cert_file, execute_os_commands("openssl x509 -in {} -startdate -enddate -subject -noout".format(cert_file)))

def letsencrypt_create(host, token):
    commands = """
        cd /tmp
        curl -O https://raw.githubusercontent.com/jungla-team/utilidades/master/cert_duckdns.sh
        mv cert_duckdns.sh /usr/sbin
        chmod 777 /usr/sbin/cert_duckdns.sh
        /usr/sbin/cert_duckdns.sh -host {host} -token {token}
        """.format(host = host, token = token)
    return execute_os_commands(commands)  

def controlacceso_backgroundvti(identificacion):
    while True:
        ip_autorizadas = ips_autorizadas()
        output = []
        j = webif_api("statusinfo?") 
        ip_deco = obtener_ip_deco()
        lista_streamings = j['Streaming_list']
        if lista_streamings.strip():
            lista_streamings = lista_streamings.strip()
            streamings = lista_streamings.split("\n")
            for stream in streamings:
                if stream.strip():            
                    ip_cliente = stream.split(":")[0].strip()
                    if ip_deco != ip_cliente and ip_cliente != "::1":
                        if ip_cliente and not ip_cliente in ip_autorizadas:
                            output.append(i18n.t('msg.control_access') + stream.strip())
        ### Sacar streams pystreamy
        hay_pystreamy = pystreamy_status(True)
        if os.path.exists("/tmp/pystreamy.status") and hay_pystreamy:
            for linea in open('/tmp/pystreamy.status'):
                user_stream = linea.split("##")[0]
                ip_stream = linea.split("##")[1]
                trans_stream = linea.split("##")[2]
                canal_stream = linea.split("##")[3]
                if len(trans_stream) > 0:
                    trans_stream = ": transcoding"
                if ip_stream and not ip_stream in ip_autorizadas:
                    output.append(i18n.t('msg.control_access') + ip_stream + ": " + canal_stream + ": " + user_stream + trans_stream)
        if output:
            logger.info(output)
            bot.send_message(identificacion, "\n".join(output))
        time.sleep(G_CONFIG['timerbot'])

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
    
def controlacceso_background(identificacion):
    while True:
        ip_autorizadas = ips_autorizadas()
        output = []
        ### Sacar streams
        j = webif_api("about?")
        lineas = j['info']['streams']  
        ip_deco = obtener_ip_deco()
        for linea in lineas:	
            ip = linea['ip'].replace("::ffff:","")
            if ip_deco != ip and ip != "::1":
                if ip and not ip in ip_autorizadas:
                    output.append(i18n.t('msg.control_access') + linea['ip'].replace("::ffff:","") + ": " + linea['name'])
        ### Sacar streams pystreamy
        hay_pystreamy = pystreamy_status(True)
        if os.path.exists("/tmp/pystreamy.status") and hay_pystreamy:
            for linea in open('/tmp/pystreamy.status'):
                user_stream = linea.split("##")[0]
                ip_stream = linea.split("##")[1]
                trans_stream = linea.split("##")[2]
                canal_stream = linea.split("##")[3]
                if len(trans_stream) > 0:
                    trans_stream = ": transcoding"
                if ip_stream and not ip_stream in ip_autorizadas:
                    output.append(i18n.t('msg.control_access') + ip_stream + ": " + canal_stream + ": " + user_stream + trans_stream)
        if output:
            logger.info(output)
            bot.send_message(identificacion, "\n".join(output))
        time.sleep(G_CONFIG['timerbot'])

def controlssh_background():
    while True:
        ip_autorizadas = ips_autorizadas()
        conexiones = commands.getoutput("netstat -tan | grep \:'22 ' | grep ESTAB | awk '{print $5}' |sed -e 's/::ffff://'| cut -d: -f1 | sort")      
        conexiones = conexiones.split('\n')
        output = []
        for linea in conexiones:
            if linea and not linea in ip_autorizadas:
                output.append(i18n.t('msg.control_ssh_unauthorized') + " = " + linea)
        if output:
            logger.info(output)
            bot.send_message(G_CONFIG['chat_id'], "\n".join(output))
        time.sleep(G_CONFIG['timerbot'])
        
def controlftp_background():
    while True:
        ip_autorizadas = ips_autorizadas()
        conexiones = commands.getoutput("netstat -tan | grep \:'21 ' | grep ESTAB | awk '{print $5}' |sed -e 's/::ffff://'| cut -d: -f1 | sort") 
        conexiones = conexiones.split('\n')
        output = []
        for linea in conexiones:
            if linea and not linea in ip_autorizadas:
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

def estado_receptor():
    response = webif_get("powerstate")
    if  re.split('[\n\t]', response)[4] == 'true':
        resultado = i18n.t('msg.satbox_standby')
    else:
        resultado = i18n.t('msg.satbox_started')
    return resultado

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
    return requests.get('https://ifconfig.me/').text

def info_tarjetared():
    line = getoutput("ethtool eth0").split("Speed: ")[1]
    return i18n.t('msg.info_networkcard') + ":\n" + line
    
def list_speedtest():
    distro = enigma_distro()
    if (distro == "VTi"):
        lista = getoutput("/opt/bin/speedtest-cli --list")
    else:
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
    distro = enigma_distro()
    try:
        if (distro == "VTi"):
            velocidad = getoutput("/opt/bin/speedtest-cli --share --simple " + " --server "+ hostspeed +  " | awk 'NR==4' | awk '{print $3}'")
        else:
            velocidad = getoutput("/usr/bin/speedtest-cli --share --simple " + " --server "+ hostspeed +  " | awk 'NR==4' | awk '{print $3}'")
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
		mark = str('\xc2\xb0')
		temperatura = tempinfo.replace('\n', '').replace(' ','') + mark + "C\n"

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
		except:
			tempinfo = ""
    if tempinfo and int(tempinfo.replace('\n', '')) > 0:
		mark = str('\xc2\xb0')
		temperatura = tempinfo.replace('\n', '').replace(' ','') + mark + "C\n"
    if temperatura:
        temperatura = int(filter(str.isdigit, temperatura))
    return temperatura                       

def estado_zerotier():
    var_zerotier = getoutput("which /usr/sbin/zerotier-cli")
    output = []
    if var_zerotier:
        output.append(i18n.t('msg.info_zerotier'))
        # estado zerotier
        line = getoutput("/usr/sbin/zerotier-cli info")
        bot.send_message(G_CONFIG['chat_id'], line)
        # per zerotier
        line = getoutput('/usr/sbin/zerotier-cli listpeers')
        output.append("  [i] " + line)
        # network zerotier
        line = getoutput('/usr/sbin/zerotier-cli listnetworks')
        output.append("  [i] " + line)
    else:
        output.append(i18n.t('msg.info_zerotier_notinstalled'))
    return "\n".join(output)

def info_check_duckdns_ip(host):
    public_ip = info_ip()
    data = { 'host': host, 'go': 'GO' }
    response = requests.post(url = 'https://ping.eu/action.php?atype=3', data = data)
    lines = response.text.split('\n')
    host_ip = ''
    for line in lines:
        matchObj = re.match('(.*) has address \<span class\=t2\>(.*)\<', line, re.M|re.I)
        if matchObj:
            host_ip = matchObj.group(2).split('<')[0]
            break
    if public_ip == host_ip:
        return i18n.t('msg.info_duckdns_ok', host=host, public_ip=public_ip)
    else:
        return i18n.t('msg.info_duckdns_ko', public_ip=public_ip, host=host, host_ip=host_ip)
    

def info_check_open_port(host, port):
    response = requests.post(url = 'https://www.portforwarding.org/', data = { 'server': host, 'port': port})
    if response.text.find('<span class="label label-success">Open</span>') > 0:
        return i18n.t('msg.info_port_open', host=host, port=port)
    else:
        return i18n.t('msg.info_port_closed', host=host, port=port)
        
# COMMAND   
@with_confirmation
def command_reboot():
    line = execute_os_commands("reboot")
    return i18n.t('msg.command_reboot') + "\n" + line

@with_confirmation
def command_restartgui():
    line = execute_os_commands("killall -9 enigma2")
    return i18n.t('msg.command_restartgui') + "\n" + line

def command_update():
    line = execute_os_commands("opkg update")
    return i18n.t('msg.command_update') + "\n\n" + line

def command_stopstream():
    line = execute_os_commands("killall -9 streamproxy")
    return i18n.t('msg.command_stopstream') + " \n" + line

@with_confirmation
def command_upgrade():
    line = execute_os_commands("opkg update && opkg upgrade && reboot")
    return i18n.t('msg.command_upgrade') + "\n\n" + line

@with_confirmation
def command_restaurar():
    line = execute_os_commands("rm -r /etc/enigma2 && reboot")
    return i18n.t('msg.command_restore') + "\n\n" + line
    
@with_confirmation
def command_resetpass():
    line = execute_os_commands('/usr/bin/passwd -d root')
    return i18n.t('msg.command_resetpass') + "\n" + line

def command_freeram():
    line = execute_os_commands("sync; echo 3 > /proc/sys/vm/drop_caches ")
    return i18n.t('msg.command_freeram') + "\n" + line

def command_screenshot():
    captura = execute_os_commands('wget 127.0.0.1/grab -O /tmp/capturacanal.png && sleep 10')
    bot.send_message(G_CONFIG['chat_id'], i18n.t('msg.command_screenshot') + '\n' + captura)
    bot.send_photo(G_CONFIG['chat_id'], photo=open('/tmp/capturacanal.png', 'rb'))
    return ''
    
def command_reposo():
    line = webif_get("powerstate?newstate=0")
    return i18n.t('msg.command_sleep') + "\n" + line
    
def command_despertar():
    line = webif_get("remotecontrol?command=116")
    return i18n.t('msg.command_wakeup') + "\n" + line

def command_runcommand(command):
    salida = execute_os_commands(command)
    if not salida.isspace():
        return salida
    else:
        return i18n.t('msg.command_execute_success')

# STREAM
def cotillearamigos():
    count_streams = 0
    output = []
    distro = enigma_distro()
    ### Sacar streams todas las imagenes menos VTI
    if distro != VTI:
        j = webif_api("about?")
        ip_deco = obtener_ip_deco()
        if j['info']['streams']:
            for s in j['info']['streams']:
                count_streams = count_streams + 1
                ip_cliente = s['ip'].replace("::ffff:","")
                if ip_deco != ip_cliente and "127.0." not in ip_cliente and ip_cliente != "::1":
                    output.append(ip_cliente + ": " + s['name'])
    ### Sacar streams para VTI
    if distro == VTI:
        j = webif_api("statusinfo?")
        ip_deco = obtener_ip_deco()
        if "Streaming_list" in j:
            lista_streamings = j['Streaming_list']
            if lista_streamings.strip():
                streamings = lista_streamings.split("\n")
                for stream in streamings:  
                    count_streams = count_streams + 1
                    ip_cliente = stream.split(":")[0].strip()
                    if ip_deco != ip_cliente and "127.0." not in ip_cliente and ip_cliente != "::1" and stream.strip():
                         output.append(stream.strip())                    
    ### Sacar streams pystreamy
    hay_pystreamy = pystreamy_status(True)
    if os.path.exists("/tmp/pystreamy.status") and hay_pystreamy:
        for linea in open('/tmp/pystreamy.status'):
            count_streams = count_streams + 1
            user_stream = linea.split("##")[0]
            ip_stream = linea.split("##")[1]
            trans_stream = linea.split("##")[2]
            canal_stream = linea.split("##")[3]
            if len(trans_stream) > 0:
                trans_stream = ": transcoding"
            output.append(ip_stream + ": " + canal_stream + ": " + user_stream + trans_stream)
    if count_streams == 0:
        output.append(i18n.t('msg.streams_notexist'))
    return "\n".join(output)

def stream_amigos():
    fichero = "/usr/bin/junglebot/amigos.cfg"
    if os.path.isfile(fichero):
        return execute_os_commands("cat " + fichero).split('\n')
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
	
def start_autostream():
    global g_autostream_thread
    if G_CONFIG['autostream'] == '1' and not g_autostream_thread:
        junglebot_restart()
        distro = enigma_distro()
        if distro == VTI:
            g_autostream_thread = threading.Thread(target=controlacceso_backgroundvti, args=(G_CONFIG['chat_id'],))
            g_autostream_thread.start()
            logger.info("Autostream iniciado")
        else:
            g_autostream_thread = threading.Thread(target=controlacceso_background, args=(G_CONFIG['chat_id'],))
            g_autostream_thread.start()
            logger.info("Autostream iniciado")

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
        f.write(data)
    return cccam_cfg + "\n" + data

def addlinea_oscam(protocol, cline):
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
                "label                         = " + params[1] + "_" + params[3] + "\n"
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
    vti_script = "/etc/init.d/current_cam.sh"
    openspa_script = getoutput("ls -t /usr/script/Oscam* | head -1")
    all_script = "/etc/init.d/softcam"
    if os.path.exists(vti_script) and distro == VTI:
        return vti_script
    elif os.path.exists(openspa_script) and distro == "openspa":
        return openspa_script
    elif os.path.exists(all_script) and (distro == "openatv" or distro == "openpli"):
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
        output = execute_os_commands("cat " + archivo)
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
            output.append(execute_os_commands("cat " + archivo))
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
            if line.find('<LI><B>OSCam:</B>') >= 0:
                parts = re.split('[<>]', line)
                version = "Version OSCam {}:{}\n".format(parts[6].strip(), parts[10].strip())
        output.insert(0, version)
        output.append(estado_clines_oscam())
        output.append(oscam_info())
        return "\n".join(output) 

def oscam_start():
    command = emu_init_command()
    if command:
        line = execute_os_commands("{} start".format(command)) or i18n.t("msg.starting")
        time.sleep(5)
        line += "\n" + emucam_status()
    else:
        line = i18n.t("msg.emu_not_active")
    return line

def oscam_stop():
    command = emu_init_command()
    if command:
        line = execute_os_commands("{} stop".format(command)) or i18n.t("msg.stoping")
        time.sleep(5)
        line += "\n" + emucam_status()
    else:
        line = i18n.t("msg.emu_not_active")
    return line

def oscam_restart():
    command = emu_init_command()
    if command:
        line = execute_os_commands("{} restart".format(command)) or i18n.t('msg.restarting')
        line += "\n" + emucam_status()
    else:
        line = i18n.t("msg.emu_not_active")
    return line

@with_confirmation
def install_oscam_conclave():
    file_autooscam = "/usr/bin/autooscam.sh"
    file_update_oscam = "/etc/oscam.update"
    if not os.path.exists(file_autooscam) and not os.path.exists(file_update_oscam):
        commands = """
            wget -O - -q http://tropical.jungle-team.online/oscam/conclave_install.sh | sh -h
            """
        return execute_os_commands(commands)
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
        return execute_os_commands(commands)
    else:
        return i18n.t("msg.file_notfound", file=file_autooscam)
        
@with_confirmation
def run_autooscam():
    file_autooscam = "/usr/bin/autooscam.sh"
    if os.path.exists(file_autooscam):
        commands = """
            /usr/bin/autooscam.sh
            """
        return execute_os_commands(commands)
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
        return execute_os_commands(commands)
    else:
        return i18n.t('msg.oscam_conclave_error')

def get_active_emu():
    active_emu = getoutput("readlink -f {}".format(emu_init_command())).split('/')[-1]
    return active_emu

def emu_list():
    distro = enigma_distro()
    if distro == VTI:
        command = "ls /usr/script/*.sh"
    elif distro == "openspa":
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
    elif (distro == VTI):
        new_emu = "/usr/script/" + emuladora
        script = "/etc/init.d/current_cam.sh"
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
  
# JUNGLESCRIPT
@with_confirmation
def junglescript_install():    
    commands = """
            curl https://raw.githubusercontent.com/jungla-team/enigma2_pre_start/master/enigma2_pre_start.sh > /usr/bin/enigma2_pre_start.sh
            chmod +x /usr/bin/enigma2_pre_start.sh
            """
    return execute_os_commands(commands)

@with_confirmation
def junglescript_run():
    return execute_os_commands("/usr/bin/enigma2_pre_start.sh")

@with_confirmation
def junglescript_uninstall():
    commands = """
            rm -f /usr/bin/enigma2_pre_start.sh
            rm -r /usr/bin/enigma2_pre_start.conf
            """
    return execute_os_commands(commands)
       
def junglescript_log():
    get_file("/tmp/enigma2_pre_start.log")

@with_confirmation
def junglescript_channels():
    commands = """
            rm -f /etc/enigma2/actualizacion
            /usr/bin/enigma2_pre_start.sh
            """
    return execute_os_commands(commands)

@with_confirmation
def junglescript_picons():
    picons_act = buscar_fich_act_picons()
    if os.path.exists(picons_act):
        commands = """
                rm -f {}
                /usr/bin/enigma2_pre_start.sh
                """.format(picons_act)
    return execute_os_commands(commands)
    
def junglescript_fecha_listacanales():
    listacanales_act = "/etc/enigma2/actualizacion"
    if os.path.exists(listacanales_act): 
       fecha_listacanales = getoutput("cat " + listacanales_act)
    return fecha_listacanales       

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
    picons_act = buscar_fich_act_picons()
    if os.path.exists(picons_act): 
       fecha_picons = getoutput("cat " + picons_act)
       return fecha_picons
    else:
       return picons_act

def fav_bouquet():
    fichero = "/etc/enigma2/fav_bouquets"
    bouquets = junglescript_fav_bouquets()
    if len(bouquets) > 0:
        return '\n'.join(bouquets)
    else:
        return i18n.t('msg.file_notfound', file=fichero)
        
def junglescript_addbouquet(bouquet):
    with open ('/etc/enigma2/fav_bouquets','a') as f:
        f.write(bouquet + "\n")
    return fav_bouquet()

def junglescript_fav_bouquets():
    fichero = "/etc/enigma2/fav_bouquets"
    items = execute_os_commands("cat " + fichero).split('\n')
    if len(items) > 0:
        return items
    else:
        return []
        
def junglescript_delbouquet(bouquet):
    lines = None
    with open('/etc/enigma2/fav_bouquets', 'r') as file:
        lines = file.readlines()
    with open ('/etc/enigma2/fav_bouquets', 'w') as f:
        for line in lines:
            if line.strip("\n") != bouquet:
                f.write(line)
    return fav_bouquet()
    
#JUNGLEBOT
@with_confirmation 
def junglebot_update():
    check_version()
    if new_version == True:
        distro = enigma_distro()
        if distro == VTI:
            package = 'junglebot_vti.ipk'
        else:
            package = 'junglebot_all.ipk'
        commands = "curl -L https://github.com/jungla-team/junglebot/raw/master/ipk/{package} >  /tmp/{package}".format(package=package)
        bot.send_message(G_CONFIG['chat_id'], execute_os_commands(commands))
        command = "/usr/bin/opkg install --force-reinstall --force-overwrite /tmp/{package} &".format(package=package)
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
    commands = """
            curl https://raw.githubusercontent.com/jungla-team/junglebot/master/CHANGELOG.md > /tmp/CHANGELOG.md
            """
    execute_os_commands(commands)
    return getoutput("cat /tmp/CHANGELOG.md")

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
                return execute_os_commands(command)
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
            return execute_os_commands(command)
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
    commands = "route add -host {} reject".format(bloquear)
    execute_os_commands(commands)
    return i18n.t('msg.geo_block_ip')

def desbloquear_ip(desbloquear):
    commands = "route del {} reject".format(desbloquear)
    execute_os_commands(commands)
    return i18n.t('msg.geo_unblock_ip')
    
def rejected_ips():
    lines = getoutput("route -n")
    rejected_ips = []
    for line in lines.split('\n'):
        items = line.split()
        if len(items) > 6 and items[3].startswith('!'):
            rejected_ips.append(items[0])
    return rejected_ips

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
    conexiones = commands.getoutput("netstat -tan | grep \:'22 ' | grep ESTAB | awk '{print $5}' |sed -e 's/::ffff://'| cut -d: -f1 | sort") 
    conexiones = conexiones.split('\n')
    output = []
    for linea in conexiones:
        if linea:
            output.append(i18n.t('msg.ssh_con', info=linea))
    if output:
        return "\n".join(output)
    else:
        return i18n.t('msg.ssh_conn_notfound')
	
def controlftp():
    conexiones = commands.getoutput("netstat -tan | grep \:'21 ' | grep ESTAB | awk '{print $5}' |sed -e 's/::ffff://'| cut -d: -f1 | sort") 
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

# GUIAS RAPIDAS

@with_confirmation
def guiarapida_openatv():
    commands = "wget -O - -q http://tropical.jungle-team.online/script/jungle_team_openatv_utils | bash -h"
    return execute_os_commands(commands)

@with_confirmation    
def guiarapida_openpli():
    commands = "opkg update; opkg install bash; wget -O - -q http://tropical.jungle-team.online/script/jungle_team_openpli_utils | bash -h"
    return execute_os_commands(commands)

@with_confirmation    
def guiarapida_vti():
    commands = "wget -O - -q http://tropical.jungle-team.online/script/jungle_team_VTI_utils | bash -h"
    return execute_os_commands(commands)

@with_confirmation
def guiarapida_blackhole():
    commands = "wget -O - -q http://tropical.jungle-team.online/script/jungle_team_blackhole_utils | bash -h"
    return execute_os_commands(commands)
    
@with_confirmation    
def guiarapida_pure2():
    commands = "wget -O - -q http://tropical.jungle-team.online/script/jungle_team_Pure2_utils | bash -h"
    return execute_os_commands(commands)
    
def deco_send_message(message):
    resp = webif_api("message?type=1&text={}".format(bytearray(message, 'utf8')))
    if resp.get('result', False):
        return i18n.t('msg.send_msg_success')
    else:
        return i18n.t('msg.send_msg_error') 

def deco_send_remote(keys):
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

# MAIN
menu_info = MenuOption(name = 'info', description = i18n.t('menu.info.title'))
menu_info.add_option(MenuOption(name = "channel", description = i18n.t('menu.info.channel'), command = info_channel))
menu_info.add_option(MenuOption(name = "sistema", description = i18n.t('menu.info.system'), command = system_info))
menu_info.add_option(MenuOption(name = "machineid", description = i18n.t('menu.info.machineid'), command = info_machineid))
menu_info.add_option(MenuOption(name = "top", description = i18n.t('menu.info.top'), command = info_top))

menu_network = MenuOption(name = 'red', description = i18n.t('menu.network.title'))
menu_network.add_option(MenuOption(name = "status", description = i18n.t('menu.network.status'), command = network_status))
menu_network.add_option(MenuOption(name = "conexiones", description = i18n.t('menu.network.connections'), command = info_conexiones))
menu_network.add_option(MenuOption(name = "speedtest", description = i18n.t('menu.network.speedtest'), command = info_speedtest, params=[[JB_BUTTONS, lambda: info_speedtest_options()]]))
menu_network.add_option(MenuOption(name = "check_duckdns_ip", description = i18n.t('menu.network.check_duckdns_ip'), command = info_check_duckdns_ip, params =["host"]))
menu_network.add_option(MenuOption(name = "check_open_port", description = i18n.t('menu.network.check_open_port'), command = info_check_open_port, params =["host", "port"]))
menu_network.add_option(MenuOption(name = "zerotier", description = i18n.t('menu.network.zerotier'), command = estado_zerotier))
menu_network.add_option(MenuOption(name = "geolocalizar_ip", description = "Geolocalizar IP", command = geolocalizar_ip, params=['geolocalizar']))
menu_network.add_option(MenuOption(name = "bloquear_ip", description = "Bloquear IP", command = bloquear_ip, params=['bloquear']))
menu_network.add_option(MenuOption(name = "desbloquear_ip", description = "Desbloquear IP", command = desbloquear_ip, params=[[JB_BUTTONS, lambda: zip(rejected_ips(), rejected_ips())]]))
menu_network.add_option(MenuOption(name = "ver_ip_bloqueadas", description = "Mostrar ip Bloqueadas", command = mostrar_ip))


menu_command = MenuOption(name = 'command', description = i18n.t('menu.command.title'))
menu_command.add_option(MenuOption(name = "status", description = i18n.t('menu.command.status'), command = estado_receptor))
menu_command.add_option(MenuOption(name = "reboot", description = i18n.t('menu.command.reboot'), command = command_reboot, params=params_confirmation ))
menu_command.add_option(MenuOption(name = "reposo", description = i18n.t('menu.command.standby'), command = command_reposo))
menu_command.add_option(MenuOption(name = "despertar", description = i18n.t('menu.command.wakeup'), command = command_despertar))
menu_command.add_option(MenuOption(name = "restartgui", description = i18n.t('menu.command.restartgui'), command = command_restartgui, params=params_confirmation))
menu_command.add_option(MenuOption(name = "stopstream", description = i18n.t('menu.command.stopstream'), command = command_stopstream))
menu_command.add_option(MenuOption(name = "freeram", description = i18n.t('menu.command.freeram'), command = command_freeram))
menu_command.add_option(MenuOption(name = "screenshot", description = i18n.t('menu.command.screenshot'), command = command_screenshot))
menu_command.add_option(MenuOption(name = "update", description = i18n.t('menu.command.update'), command = command_update))
menu_command.add_option(MenuOption(name = "upgrade", description = i18n.t('menu.command.upgrade'), command = command_upgrade, params=params_confirmation))
menu_command.add_option(MenuOption(name = "restaurar", description = i18n.t('menu.command.factory_reset'), command = command_restaurar, params=params_confirmation))
menu_command.add_option(MenuOption(name = "resetpass", description = i18n.t('menu.command.resetpass'), command = command_resetpass, params=params_confirmation))
menu_command.add_option(MenuOption(name = "runcommand", description = i18n.t('menu.command.exec_command'), command = command_runcommand, params=['comando']))

menu_stream = MenuOption(name = 'stream', description = i18n.t('menu.stream.title'))
menu_stream.add_option(MenuOption(name = "ver", description = i18n.t('menu.stream.show'), command = cotillearamigos))
menu_stream.add_option(MenuOption(name = "amigos", description = i18n.t('menu.stream.friends'), command = amigos))
menu_stream.add_option(MenuOption(name = "addamigo", description = i18n.t('menu.stream.add_friend'), command = stream_addamigo, params=['ip amigo']))
menu_stream.add_option(MenuOption(name = "delamigo", description = i18n.t('menu.stream.delete_friend'), command = stream_delamigo, params=[[JB_BUTTONS, lambda: zip(stream_amigos(), stream_amigos())]]))
menu_stream.add_option(MenuOption(name = "autocheck", description = i18n.t('menu.stream.autocheck'), command = stream_autocheck, params=params_confirmation))
menu_stream.add_option(MenuOption(name = "stopstream", description = i18n.t('menu.stream.stop_streamproxy'), command = command_stopstream))

menu_conexiones = MenuOption(name = 'conexiones', description = i18n.t('menu.connections.title'))
menu_conexiones.add_option(MenuOption(name = "config", description = i18n.t('menu.connections.config'), command = lambda : config("/usr/bin/junglebot/parametros.py")))
menu_conexiones.add_option(MenuOption(name = "set_config_parameters", description = i18n.t('menu.connections.set_config'), command = set_value_parameters, params =['clave', 'valor']))
menu_conexiones.add_option(MenuOption(name = "addamigo", description = i18n.t('menu.connections.add_friend'), command = stream_addamigo, params=['ip amigo']))
menu_conexiones.add_option(MenuOption(name = "delamigo", description = i18n.t('menu.connections.del_friend'), command = stream_delamigo, params=[[JB_BUTTONS, lambda: zip(stream_amigos(), stream_amigos())]]))
menu_conexiones.add_option(MenuOption(name = "amigos", description = i18n.t('menu.connections.friends'), command = amigos))
menu_conexiones.add_option(MenuOption(name = "ssh", description = i18n.t('menu.connections.ssh'), command = controlssh))
menu_conexiones.add_option(MenuOption(name = "ftp", description = i18n.t('menu.connections.ftp'), command = controlftp))
menu_conexiones.add_option(MenuOption(name = "autossh", description = i18n.t('menu.connections.autossh'), command = conn_autossh, params=params_confirmation))
menu_conexiones.add_option(MenuOption(name = "autoftp", description = i18n.t('menu.connections.autoftp'), command = conn_autoftp, params=params_confirmation))

menu_emu = MenuOption(name='emu', description= i18n.t('menu.emu.title'), info = 'https://jungle-team.com/conclave-oscam-autoupdate/')
menu_emu.add_option(MenuOption(name = "status", description = i18n.t('menu.emu.status'), command = emucam_status))
menu_emu.add_option(MenuOption(name = "list_emus", description = "Ver emus instaladas", command = list_installed_emus))
menu_emu.add_option(MenuOption(name = "addlineacccam", description = i18n.t('menu.emu.addlinecccam'), command = addlinea_cccam, params=['clinea (C: servidor puerto usuario password)']))
menu_emu.add_option(MenuOption(name = "addlineoscam", description = i18n.t('menu.emu.addlineoscam'), command = addlinea_oscam, params=['protocolo', 'clinea (C: servidor puerto usuario password)']))
menu_emu.add_option(MenuOption(name = "start", description = i18n.t('menu.emu.start'), command = oscam_start))
menu_emu.add_option(MenuOption(name = "stop", description = i18n.t('menu.emu.stop'), command = oscam_stop))
menu_emu.add_option(MenuOption(name = "restart", description = i18n.t('menu.emu.restart'), command = oscam_restart))
menu_emu.add_option(MenuOption(name = "install_oscam_conclave", description = i18n.t('menu.emu.install_conclave'), command = install_oscam_conclave, params=params_confirmation))
menu_emu.add_option(MenuOption(name = "update_autooscam", description = i18n.t('menu.emu.update_autooscam'), command = update_autooscam, params=params_confirmation))
menu_emu.add_option(MenuOption(name = "run_autooscam", description = i18n.t('menu.emu.run_autooscam'), command = run_autooscam, params=params_confirmation))
menu_emu.add_option(MenuOption(name = "force_autooscam", description = i18n.t('menu.emu.force_autooscam'), command = force_autooscam, params=params_confirmation))
menu_emu.add_option(MenuOption(name = "change_active_emu", description = "Activar emu", command = set_active_emu, params=[[JB_BUTTONS, lambda: zip(emu_list(), emu_list())]]))

menu_pystreamy = MenuOption(name = 'pystreamy', description = i18n.t('menu.pystreamy.title'), info = 'https://gitlab.com/amoyse/pystreamy/')
menu_pystreamy.add_option(MenuOption(name = "status", description = i18n.t('menu.pystreamy.status'), command = pystreamy_status))
menu_pystreamy.add_option(MenuOption(name = "stop", description = i18n.t('menu.pystreamy.stop'), command = pystreamy_stop))
menu_pystreamy.add_option(MenuOption(name = "start", description = i18n.t('menu.pystreamy.start'), command = pystreamy_start))
menu_pystreamy.add_option(MenuOption(name = "restart", description = i18n.t('menu.pystreamy.restart'), command = pystreamy_restart))
menu_pystreamy.add_option(MenuOption(name = "config", description = i18n.t('menu.pystreamy.config'), command = lambda : config("/etc/enigma2/pystreamy.conf")))
menu_pystreamy.add_option(MenuOption(name = "set_config", description = i18n.t('menu.pystreamy.set_config'), command = lambda x,y: set_value("/etc/enigma2/pystreamy.conf", x,y), params=['clave', 'valor']))
menu_pystreamy.add_option(MenuOption(name = "check_config", description = i18n.t('menu.pystreamy.check_config'), command = lambda: pystreamy_check_config("/etc/enigma2/pystreamy.conf")))
menu_pystreamy.add_option(MenuOption(name = "install", description = i18n.t('menu.pystreamy.install'), command = pystreamy_install, params = params_confirmation))
menu_pystreamy.add_option(MenuOption(name = "uninstall", description = i18n.t('menu.pystreamy.uninstall'), command = pystreamy_uninstall, params = params_confirmation))
menu_pystreamy.add_option(MenuOption(name = "ver_log", description = i18n.t('menu.pystreamy.log'), command = pystreamy_log))

menu_letsencrypt = MenuOption(name = 'letsencrypt', description = i18n.t('menu.letsencrypt.title'), info = 'https://jungle-team.com/crear-certificados-duckdns-firmados-lets-encrypt/')
menu_letsencrypt.add_option(MenuOption(name = "crear", description = i18n.t('menu.letsencrypt.create'), command = letsencrypt_create, params =['host', 'token']))
menu_letsencrypt.add_option(MenuOption(name = "estado", description = i18n.t('menu.letsencrypt.status'), command = lambda: letsencrypt_status('/etc/enigma2/cert.pem')))
menu_letsencrypt.add_option(MenuOption(name = "check_duckdns_ip", description = i18n.t('menu.letsencrypt.check_ip'), command = info_check_duckdns_ip, params =["host"]))
menu_letsencrypt.add_option(MenuOption(name = "check_open_port", description = i18n.t('menu.letsencrypt.check_port'), command = info_check_open_port, params =["host", "port"]))

menu_settings = MenuOption(name = 'junglebot', description = i18n.t('menu.junglebot.title'), info = 'https://jungle-team.com/junglebotv2-telegram-enigma2/')
menu_settings.add_option(MenuOption(name = "send_message", description = i18n.t('menu.junglebot.send_message'), command = deco_send_message, params=['mensaje']))
menu_settings.add_option(MenuOption(name = "send_remote", description = i18n.t('menu.junglebot.send_remote'), command = deco_send_remote, params=['canal']))
menu_settings.add_option(MenuOption(name = "config", description = i18n.t('menu.junglebot.config'), command = lambda : config("/usr/bin/junglebot/parametros.py")))
menu_settings.add_option(MenuOption(name = "set_config_parameters", description = i18n.t('menu.junglebot.set_config'), command = set_value_parameters, params =['clave', 'valor']))
menu_settings.add_option(MenuOption(name = "update", description = i18n.t('menu.junglebot.update'), command = junglebot_update, params=params_confirmation))
menu_settings.add_option(MenuOption(name = "reboot", description = i18n.t('menu.junglebot.reboot'), command = junglebot_restart, params=params_confirmation))
menu_settings.add_option(MenuOption(name = "log", description = i18n.t('menu.junglebot.log'), command = junglebot_log))
menu_settings.add_option(MenuOption(name = "purgelog", description = i18n.t('menu.junglebot.purge_log'), command = junglebot_purge_log))
menu_settings.add_option(MenuOption(name = "changelog", description = i18n.t('menu.junglebot.changelog'), command = junglebot_changelog))

menu_junglescript = MenuOption(name = 'junglescript', description = i18n.t('menu.junglescript.title'), info  ='https://jungle-team.com/junglescript-lista-canales-y-picon-enigma2-movistar/')
menu_junglescript.add_option(MenuOption(name = "config", description = i18n.t('menu.junglescript.config'), command = lambda : config("/usr/bin/enigma2_pre_start.conf")))
menu_junglescript.add_option(MenuOption(name = "set_config", description = i18n.t('menu.junglescript.set_config'), command = lambda x, y: set_value("/usr/bin/enigma2_pre_start.conf", x,y), params =['clave', 'valor']))
menu_junglescript.add_option(MenuOption(name = "install", description = i18n.t('menu.junglescript.install'), command = junglescript_install, params=params_confirmation))
menu_junglescript.add_option(MenuOption(name = "uninstall", description = i18n.t('menu.junglescript.uninstall'), command = junglescript_uninstall, params=params_confirmation))
menu_junglescript.add_option(MenuOption(name = "run", description = i18n.t('menu.junglescript.run'), command = junglescript_run, params=params_confirmation))
menu_junglescript.add_option(MenuOption(name = "force_channels", description = i18n.t('menu.junglescript.force_channels'), command = junglescript_channels, params=params_confirmation))
menu_junglescript.add_option(MenuOption(name = "force_picons", description = i18n.t('menu.junglescript.force_picons'), command = junglescript_picons, params=params_confirmation))
menu_junglescript.add_option(MenuOption(name = "log", description = i18n.t('menu.junglescript.log'), command = junglescript_log))
menu_junglescript.add_option(MenuOption(name = "ver_fecha_lista", description = i18n.t('menu.junglescript.channel_list'), command = junglescript_fecha_listacanales))
menu_junglescript.add_option(MenuOption(name = "ver_fecha_picons", description = i18n.t('menu.junglescript.picon_list'), command = junglescript_fecha_picons))
menu_junglescript.add_option(MenuOption(name = "addbouquet", description = i18n.t('menu.junglescript.add_bouquet'), command = junglescript_addbouquet, params=['bouquet']))
menu_junglescript.add_option(MenuOption(name = "delbouquet", description = i18n.t('menu.junglescript.del_bouquet'), command = junglescript_delbouquet, params=[[JB_BUTTONS, lambda: zip(junglescript_fav_bouquets(), junglescript_fav_bouquets())]]))

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
menu_epg.add_option(MenuOption(name = "reiniciar_interfaz", description = i18n.t('menu.epg.restart_gui'), command = command_restartgui, params=params_confirmation))
menu_epg.add_option(MenuOption(name = "desinstalar_epgimport", description = i18n.t('menu.epg.uninstall_epgimport'), command = remove_epgimport, params=params_confirmation))
menu_epg.add_option(MenuOption(name = "desinstalar_crossepg", description = i18n.t('menu.epg.uninstall_crossepg'), command = remove_crossepg, params=params_confirmation))

menu_guiasrapidas = MenuOption(name = 'guiasrapidas', description = i18n.t('menu.guides.title'))
menu_guiasrapidas.add_option(MenuOption(name = "guia_rapida_openatv", description = i18n.t('menu.guides.openatv'), command = guiarapida_openatv, params=params_confirmation))
menu_guiasrapidas.add_option(MenuOption(name = "guia_rapida_openpli", description = i18n.t('menu.guides.openpli'), command = guiarapida_openpli, params=params_confirmation))
menu_guiasrapidas.add_option(MenuOption(name = "guia_rapida_vti", description = i18n.t('menu.guides.vti'), command = guiarapida_vti, params=params_confirmation))
menu_guiasrapidas.add_option(MenuOption(name = "guia_rapida_blackhole", description = i18n.t('menu.guides.blackhole'), command = guiarapida_blackhole, params=params_confirmation))
menu_guiasrapidas.add_option(MenuOption(name = "guia_rapida_pure2", description = i18n.t('menu.guides.pure2'), command = guiarapida_pure2, params=params_confirmation))

menu_ayuda = MenuOption(name = 'ayuda', description = i18n.t('menu.help.title'))

g_menu = [menu_ayuda, menu_info, menu_network, menu_guiasrapidas, menu_settings, menu_stream, menu_conexiones, menu_grabaciones, menu_epg, menu_emu, menu_command, menu_junglescript, menu_letsencrypt, menu_pystreamy]   
g_current_menu_option = None

if __name__ == "__main__":
    try:
        logger.info('junglebot esta funcionando...' + VERSION)
        send_large_message(G_CONFIG['chat_id'], i18n.t('msg.boot_info') + VERSION)
        ga('system', enigma_distro())
        ga('version', VERSION)
        ga('locale', G_CONFIG['locale'])
        check_version()
        start_autostream()
        start_autossh()
        start_autoftp()
        start_autoram()
        start_autotemp()
        start_autoflash()
        fill_command_list()
    except Exception as e:
        logger.exception(e)
    bot.infinity_polling(none_stop=True)
