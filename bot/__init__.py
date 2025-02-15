import logging
import os
import threading
import time
import random
import string
import aria2p
import telegram.ext as tg
from dotenv import load_dotenv
from pyrogram import Client
import psycopg2
from psycopg2 import Error
from telegraph import Telegraph

import socket

socket.setdefaulttimeout(600)

botStartTime = time.time()
if os.path.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
                    level=logging.INFO)

load_dotenv('config.env')

LOGGER = logging.getLogger(__name__)

Interval = []

emoticons = [
            "https://telegra.ph/file/73158ecf12829ddf7c474.jpg",
            "https://telegra.ph/file/1ee75c6862ec5a326369e.jpg",
            "https://telegra.ph/file/22004288d1a66e5595b88.jpg",
            "https://telegra.ph/file/642d6e1cb8a0a39b90224.jpg",
            "https://telegra.ph/file/de1611deef4ce40b76516.jpg",
            "https://telegra.ph/file/f9518dd934bd14133e47f.jpg",
        ]

IMG = random.choice(emoticons)

def getConfig(name: str):
    return os.environ[name]

def mktable():
    try:
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor()
        sql = "CREATE TABLE users (uid bigint, sudo boolean DEFAULT FALSE);"
        cur.execute(sql)
        conn.commit()
        LOGGER.info("Table Created!")
    except Error as e:
        LOGGER.error(e)
        exit(1)


try:
    if bool(getConfig('_____REMOVE_THIS_LINE_____')):
        logging.error('The README.md file there to be read! Exiting now!')
        exit()
except KeyError:
    pass

aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret="",
    )
)

DOWNLOAD_DIR = None
BOT_TOKEN = None

download_dict_lock = threading.Lock()
status_reply_dict_lock = threading.Lock()
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# Stores list of users and chats the bot is authorized to use in
AUTHORIZED_CHATS = set()
SUDO_USERS = set()
if os.path.exists('authorized_chats.txt'):
    with open('authorized_chats.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            AUTHORIZED_CHATS.add(int(line.split()[0]))
if os.path.exists('sudo_users.txt'):
    with open('sudo_users.txt', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            SUDO_USERS.add(int(line.split()[0]))
try:
    achats = getConfig('AUTHORIZED_CHATS')
    achats = achats.split(" ")
    for chats in achats:
        AUTHORIZED_CHATS.add(int(chats))
except:
    pass
try:
    schats = getConfig('SUDO_USERS')
    schats = schats.split(" ")
    for chats in schats:
        SUDO_USERS.add(int(chats))
except:
    pass
  
try:
    BOT_TOKEN = getConfig('BOT_TOKEN')
    DB_URI = getConfig('DATABASE_URL')
    parent_id = getConfig('GDRIVE_FOLDER_ID')
    DOWNLOAD_DIR = getConfig('DOWNLOAD_DIR')
    if not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR = DOWNLOAD_DIR + '/'
    DOWNLOAD_STATUS_UPDATE_INTERVAL = int(getConfig('DOWNLOAD_STATUS_UPDATE_INTERVAL'))
    OWNER_ID = int(getConfig('OWNER_ID'))
    SUDO_USER = tuple(filter(lambda x: x, map(int, os.environ.get("SUDO_USER", "").split())))
    AUTO_DELETE_MESSAGE_DURATION = int(getConfig('AUTO_DELETE_MESSAGE_DURATION'))
    TELEGRAM_API = getConfig('TELEGRAM_API')
    TELEGRAM_HASH = getConfig('TELEGRAM_HASH')
    UPSTREAM_REPO = getConfig('UPSTREAM_REPO')
    UPSTREAM_BRANCH = getConfig('UPSTREAM_BRANCH')
except KeyError as e:
    LOGGER.error("One or more env variables missing! Exiting now")
    exit(1)

try:
    conn = psycopg2.connect(DB_URI)
    cur = conn.cursor()
    sql = "SELECT * from users;"
    cur.execute(sql)
    rows = cur.fetchall()  #returns a list ==> (uid, sudo)
    for row in rows:
        AUTHORIZED_CHATS.add(row[0])
        if row[1]:
            SUDO_USERS.add(row[0])
except Error as e:
    if 'relation "users" does not exist' in str(e):
        mktable()
    else:
        LOGGER.error(e)
        exit(1)
finally:
    cur.close()
    conn.close()

LOGGER.info("Generating USER_SESSION_STRING")

app = Client(':memory:', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, bot_token=BOT_TOKEN)

#Generate Telegraph Token
sname = ''.join(random.SystemRandom().choices(string.ascii_letters, k=8))
LOGGER.info("Generating Telegraph Token using '" + sname + "' name")
telegraph = Telegraph()
telegraph.create_account(short_name=sname)
telegraph_token = telegraph.get_access_token()
LOGGER.info("Telegraph Token Generated: '" + telegraph_token + "'")

try:
    STATUS_LIMIT = getConfig('STATUS_LIMIT')
    if len(STATUS_LIMIT) == 0:
        raise KeyError
    else:
        STATUS_LIMIT = int(getConfig('STATUS_LIMIT'))
except KeyError:
    STATUS_LIMIT = 2
try:
    MEGA_API_KEY = getConfig('MEGA_API_KEY')
except KeyError:
    logging.warning('MEGA API KEY not provided!')
    MEGA_API_KEY = None
try:
    MEGA_EMAIL_ID = getConfig('MEGA_EMAIL_ID')
    MEGA_PASSWORD = getConfig('MEGA_PASSWORD')
    if len(MEGA_EMAIL_ID) == 0 or len(MEGA_PASSWORD) == 0:
        raise KeyError
except KeyError:
    logging.warning('MEGA Credentials not provided!')
    MEGA_EMAIL_ID = None
    MEGA_PASSWORD = None
try:
    HEROKU_API_KEY = getConfig('HEROKU_API_KEY')
except KeyError:
    logging.warning('HEROKU API KEY not provided!')
    HEROKU_API_KEY = None
try:
    HEROKU_APP_NAME = getConfig('HEROKU_APP_NAME')
except KeyError:
    logging.warning('HEROKU APP NAME not provided!')
    HEROKU_APP_NAME = None
try:
    TORRENT_DIRECT_LIMIT = getConfig('TORRENT_DIRECT_LIMIT')
    if len(TORRENT_DIRECT_LIMIT) == 0:
        TORRENT_DIRECT_LIMIT = None
except KeyError:
    TORRENT_DIRECT_LIMIT = None
try:
    UPTOBOX_TOKEN = getConfig('UPTOBOX_TOKEN')
except KeyError:
    logging.info('UPTOBOX_TOKEN not provided!')
    UPTOBOX_TOKEN = None
try:
    VIEW_LINK = getConfig('VIEW_LINK')
    if VIEW_LINK.lower() == 'true':
        VIEW_LINK = True
    else:
        VIEW_LINK = False
except KeyError:
    VIEW_LINK = False
try:
    STOP_DUPLICATE = getConfig('STOP_DUPLICATE')
    if STOP_DUPLICATE.lower() == 'true':
        STOP_DUPLICATE = True
    else:
        STOP_DUPLICATE = False
except KeyError:
    STOP_DUPLICATE = False
try:
    INDEX_URL = getConfig('INDEX_URL')
    if len(INDEX_URL) == 0:
        INDEX_URL = None
except KeyError:
    INDEX_URL = None
try:
    CLONE_LIMIT = getConfig('CLONE_LIMIT')
    if len(CLONE_LIMIT) == 0:
        CLONE_LIMIT = None
except KeyError:
    CLONE_LIMIT = None
try:
    MEGA_LIMIT = getConfig('MEGA_LIMIT')
    if len(MEGA_LIMIT) == 0:
        MEGA_LIMIT = None
except KeyError:
    MEGA_LIMIT = None
try:
    TAR_UNZIP_LIMIT = getConfig('TAR_UNZIP_LIMIT')
    if len(TAR_UNZIP_LIMIT) == 0:
        TAR_UNZIP_LIMIT = None
except KeyError:
    TAR_UNZIP_LIMIT = None    
try:
    BUTTON_FOUR_NAME = getConfig('BUTTON_FOUR_NAME')
    BUTTON_FOUR_URL = getConfig('BUTTON_FOUR_URL')
    if len(BUTTON_FOUR_NAME) == 0 or len(BUTTON_FOUR_URL) == 0:
        raise KeyError
except KeyError:
    BUTTON_FOUR_NAME = None
    BUTTON_FOUR_URL = None
try:
    BUTTON_FIVE_NAME = getConfig('BUTTON_FIVE_NAME')
    BUTTON_FIVE_URL = getConfig('BUTTON_FIVE_URL')
    if len(BUTTON_FIVE_NAME) == 0 or len(BUTTON_FIVE_URL) == 0:
        raise KeyError
except KeyError:
    BUTTON_FIVE_NAME = None
    BUTTON_FIVE_URL = None
try:
    BUTTON_SIX_NAME = getConfig('BUTTON_SIX_NAME')
    BUTTON_SIX_URL = getConfig('BUTTON_SIX_URL')
    if len(BUTTON_SIX_NAME) == 0 or len(BUTTON_SIX_URL) == 0:
        raise KeyError
except KeyError:
    BUTTON_SIX_NAME = None
    BUTTON_SIX_URL = None
try:
    IS_TEAM_DRIVE = getConfig('IS_TEAM_DRIVE')
    if IS_TEAM_DRIVE.lower() == 'true':
        IS_TEAM_DRIVE = True
    else:
        IS_TEAM_DRIVE = False
except KeyError:
    IS_TEAM_DRIVE = False
try:
    USE_SERVICE_ACCOUNTS = getConfig('USE_SERVICE_ACCOUNTS')
    if USE_SERVICE_ACCOUNTS.lower() == 'true':
        USE_SERVICE_ACCOUNTS = True
    else:
        USE_SERVICE_ACCOUNTS = False
except KeyError:
    USE_SERVICE_ACCOUNTS = False
try:
    BLOCK_MEGA_FOLDER = getConfig('BLOCK_MEGA_FOLDER')
    if BLOCK_MEGA_FOLDER.lower() == 'true':
        BLOCK_MEGA_FOLDER = True
    else:
        BLOCK_MEGA_FOLDER = False
except KeyError:
    BLOCK_MEGA_FOLDER = False
try:
    BLOCK_MEGA_LINKS = getConfig('BLOCK_MEGA_LINKS')
    if BLOCK_MEGA_LINKS.lower() == 'true':
        BLOCK_MEGA_LINKS = True
    else:
        BLOCK_MEGA_LINKS = False
except KeyError:
    BLOCK_MEGA_LINKS = False
try:
    SHORTENER = getConfig('SHORTENER')
    SHORTENER_API = getConfig('SHORTENER_API')
    if len(SHORTENER) == 0 or len(SHORTENER_API) == 0:
        raise KeyError
except KeyError:
    SHORTENER = None
    SHORTENER_API = None
IGNORE_PENDING_REQUESTS = False
try:
    if getConfig("IGNORE_PENDING_REQUESTS").lower() == "true":
        IGNORE_PENDING_REQUESTS = True
except KeyError:
    pass
try:
    TIMEZONE = getConfig('TIMEZONE')
    if len(TIMEZONE) == 0:
        TIMEZONE = 'Asia/Kolkata'
except KeyError:
    TIMEZONE = 'Asia/Kolkata'

updater = tg.Updater(token=BOT_TOKEN)
bot = updater.bot
dispatcher = updater.dispatcher
