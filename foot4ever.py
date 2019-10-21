# --------------------------------------------------------------------------- #
# Name:        Manage foot inscription & teams
#
# Author:      Pasha Shadkami
#
# Created:     12/12/2017
# Copyright:   Pasha Shadkami
#-------------------------------------------------------------------------------

import os
import sys
import json
from collections import OrderedDict
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.bot import Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import datetime
import pandas as pd

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

public_cmds = OrderedDict([('add','ثبت نام در بازی هفته بعد از ساعت ۶ روز جمعه')
                          ,('del','کنسل کردن ثبت نام')
                          ,('prog','دریافت روز و ساعت برنامه بازی آینده')
                          ,('timkeshi','اجرای برنامه تیم کشی')])
admin_cmds = OrderedDict([('add','اضافه کردن بازیکن در لیست ثبت نام')
                          ,('del','پاک کردن بازیکن از لیست ثبت نام')
                          ,('add_mahroom','اضافه کردن بازیکن در لیست محرومین از ثبت نام')
                          ,('del_mahroom','پاک کردن بازیکن از لیست محرومین از ثبت نام')
                          ,('set_prog','تغییر برنامه هفته آینده')
                          ,('all','دریافت اسم تمامی بازیکنان')])


class Msg():
    wrong_page_add_del = 'به منظور ثبت نام و یا پاک نمودن ثبت نام، لطفا ابتدا به صفحه اصلی گروه رفته سپس دستور را تایپ نمایید'
    wrong_place_timkeshi = 'به منظور تیم کشی، ابتدا یک گروه ساخته، کاپیتان دوم و من را به گروه دعوت ، سپس مجددا دستور را انتخاب کنید'
    you_are_forbidden = 'شرمنده، شما این هفته از ثبت نام محروم هستی'
    too_late_add = 'می دونم فوتبال دوست داری، اما باید تا جمعه ساعت شش برای ثبت نام مجدد صبر کنی'
    too_late_del = 'کنسل کردن ثبت نام دیر بوده و دیگر میسر نمی باشد. لطفا با ادمین ها تماس حاصل کنید'
    restart_timkeshi = 'جان با شما نبودم! با کاپیتان دوم بودم!!!'
    missing_permission = 'شما مجاز به استفاده از این دستور نمی باشید'
    select_player = 'لطفا یک بازیکن انتخاب کن (امتیازات از ۱ تا ۵: دروازه، دفاع، حمله، دوندگی)'
    teamkeshi_welcome = 'کاپیتان اول، از اینکه تیم کشی را آغاز کردی ازت ممنونم! ای کاپیتان دوم، تو هم حاضر و آماده هستی؟'
    validation_finish = 'مرسی! تیم کشی با موفقیت انجام شد. تیم ها به ادمین ها ارسال خواهند شد'
    validation_finish2 = 'تیم کشی با موفقیت توسط {} و {} انجام شد و به شرح زیر می باشد'
    team_rates = 'دروازه: {}، دفاع: {}، حمله: {}، دوندگی: {}'
    ask_validation = 'تیمتو تایید می کنی؟ اوکی؟'
    select_forbidden_player = 'بازیکنی که باید محروم شود را انتخاب کن'
    select_unforbidden_player = 'بازیکن محرومی که باید پاک شود را انتخاب کن'
    no_forbidden_player = 'در حال حاطر بازیکن محروم نداریم'
    operation_cancelled = 'درخواست شما کنسل شد'
    try_to_del = 'خواست کنسل کنه، من نگذاشتم! بدی نیست یک تماسی باهاش بگیرین'
    next_week_prog ='برنامه هفته بعد:'
    reserve = 'بازیکنان ذخیره'
    timkeshi_is_running = 'تیم کشی در حال انجام می باشد. برای آغاز مجدد، لطفا ابتدا آن را کنسل کنید'
    bad_set_prog_msg = 'فرمت تغییر برنامه می بایست به شکل زیر باشد: تاریخ ساعت ، مرکز'
    bad_set_prog_format = '25/05/2018 19:30, 1'
    bad_set_prog_succeed = 'تغییر برنامه با موفقییت انجام و به شرح ذیل می باشد'

def create_player_keyboard(players):
    keyboard = []
    row = []
    nb_btn_in_row = 1
    for idx, player in enumerate(players):
        row.append(InlineKeyboardButton(player, callback_data=player))
        if (idx+1) % nb_btn_in_row == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(PerWord.cancel, callback_data=PerWord.cancel)])
    return keyboard

def create_validation_keyboard():
    keyboard = [[InlineKeyboardButton(PerWord.yes, callback_data=PerWord.yes),
                 InlineKeyboardButton(PerWord.no, callback_data=PerWord.no)]]
    return keyboard


"""
add - ثبت نام در بازی آینده
del - کنسل کردن ثبت نام
prog - دریافت روز و ساعت برنامه بازی آینده
timkeshi - اجرای برنامه تیم کشی
help - راهنما
help_admins - راهنمای ادمین
"""

class PerWord():
    hamed_no = 'حامد'
    pasha = 'پاشا'
    ali_ju = 'علیرضا ژول'
    ali_sh = 'علیرضا شی'
    cyrus = 'سیروس'
    hamid = 'حمید'
    ali_cre = 'علی کخ'
    sia = 'سیاوش'
    soroosh = 'سروش'
    mohammad = 'محمد'
    saman = 'سامان'
    amin = 'امین'
    amin_mo = 'امین مو'
    essy = 'اسفندیار'
    armin = 'آرمین'
    mori = 'مرتضی'
    babak = 'بابک'
    mehrdad = 'مهرداد'
    navid = 'نوید'
    mehdi_k = 'مهدی'
    reza = 'رضا'
    changiz = 'چنگیز'
    milad = 'میلاد'
    saleh = 'صالح'
    mehdi_v = 'مهدی وح'
    parham = 'پرهام'

    zero = '۰'
    one = '۱'
    two = '۲'
    three = '۳'
    four = '۴'
    five = '۵'
    six = '۶'
    seven = '۷'
    eight = '۸'
    nine = '۹'
    ten = '۱۰'

    monday = 'دوشنبه'
    tuesday = 'سه شنبه'
    wednesday = 'چهارشنبه'
    thursday = 'پنجشنبه'
    friday = 'جمعه'
    saturday = 'شنبه'
    sunday = 'یکشنبه'

    cancel = 'کنسل'
    yes = 'بلی'
    no = 'خیر'
    jan = 'جان، '
    team = 'تیم'
    white = 'سفید'
    red = 'قرمز'


class UserIds():
    hamed_no = 76017323
    pasha = 122707272
    ali_ju = 132438059
    ali_sh = 104542063
    cyrus = 114173106
    hamid = 501194040 #Sobhan: 127776929
    ali_cre = 240732760
    sia = 200115880
    soroosh = 107547421
    saman = 118674419
    essy = 264694076
    babak = 472586769
    armin = 315665388
    amin_mo = 117948828
    amin = 102490025
    mehdi_k = 95201504
    mehdi_v = 296955045
    navid = 161869718
    mehrdad = 359343302
    reza = 94006043
    mori = 161625455
    mohammad = 86055925
    changiz = 118876980
    parham = 45177826
    saleh = 316966952
    milad = 110228454                    

# Contains user Id as key. Persian name, goal keepering, defensing, attacking and running rates
players_info =  { UserIds.ali_cre   :   (PerWord.ali_cre,   (2.86,3.13,3.00,2.50))
                , UserIds.ali_ju    :   (PerWord.ali_ju,    (2.89,3.00,4.28,3.17))
                , UserIds.ali_sh    :   (PerWord.ali_sh,    (2.57,3.00,4.53,3.82))
                , UserIds.amin      :   (PerWord.amin,      (2.41,2.95,3.20,2.70))
                , UserIds.armin     :   (PerWord.armin,     (2.32,2.89,3.25,3.53))
                , UserIds.changiz   :   (PerWord.changiz,   (5.00,1.00,1.00,1.00))
                , UserIds.cyrus     :   (PerWord.cyrus,     (4.71,4.03,4.32,3.82))
                , UserIds.essy      :   (PerWord.essy,      (2.89,3.67,3.82,3.50))
                , UserIds.hamid     :   (PerWord.hamid,     (4.00,2.75,2.53,4.71))
                , UserIds.hamed_no  :   (PerWord.hamed_no,  (2.96,4.00,2.82,3.03))
                , UserIds.mohammad  :   (PerWord.mohammad,  (2.65,2.81,3.25,2.56))
                , UserIds.mori      :   (PerWord.mori,      (3.28,4.71,3.28,4.21))
                , UserIds.navid     :   (PerWord.navid,     (3.00,4.00,5.00,4.75))
                , UserIds.pasha     :   (PerWord.pasha,     (2.35,3.53,3.00,3.39))
                , UserIds.saman     :   (PerWord.saman,     (2.78,3.57,4.00,4.92))
                , UserIds.soroosh   :   (PerWord.soroosh,   (4.85,3.21,3.35,2.42))
                , UserIds.sia       :   (PerWord.sia,       (3.11,3.53,4.53,4.00))
                , UserIds.parham    :   (PerWord.parham,    (2.00,3.00,4.00,4.50))
                , UserIds.mehdi_v   :   (PerWord.mehdi_v,   (5.00,3.50,3.50,4.00))
                , UserIds.saleh     :   (PerWord.saleh,     (3.50,3.00,3.50,4.00))
                , UserIds.milad     :   (PerWord.milad,     (3.00,3.00,4.50,4.00))
                
                , UserIds.mehrdad   :   (PerWord.mehrdad,   (5,5,5,5))
                , UserIds.amin_mo   :   (PerWord.amin_mo,   (5,5,5,5))
                , UserIds.babak     :   (PerWord.babak,     (3.5,3.5,3.5,3.5))
                , UserIds.mehdi_k   :   (PerWord.mehdi_k,   (5,5,5,5))
                , UserIds.reza      :   (PerWord.reza,      (5,5,5,5))}

foreign_players_rates =   {'mouad'  : (2.50,3.50,4.00,5.00)
                          ,'mathieu': (2.00,3.00,3.50,4.00)
                          ,'yvon'   : (2.00,3.00,3.00,3.00)
                          ,'florin' : (2.50,3.00,4.00,5.00)
                          ,'francisco' : (2.00,2.50,2.50,4.00)
                          ,'daniel' : (2.50,3.50,3.50,4.00)}

per_digits = {0:PerWord.zero, 1:PerWord.one, 2:PerWord.two, 3:PerWord.three, 4:PerWord.four, 5:PerWord.five,
              6:PerWord.six, 7:PerWord.seven, 8:PerWord.eight, 9:PerWord.nine, 10:PerWord.ten}

per_day_names = {0:PerWord.monday, 1:PerWord.tuesday, 2:PerWord.wednesday, 3:PerWord.thursday, 4:PerWord.friday, 5:PerWord.saturday, 6:PerWord.sunday}

##
default_next_players = [UserIds.pasha, UserIds.saman]
#default_next_players = list(players_info.keys())

def WithLogError(method):
    """
    Decorator which executes the method with busy cursor
    """
    def method_wrapper(*args, **kwargs):
        try:
            return_value = method(*args, **kwargs)
        except Exception as e:
            update = args[1]
            context = args[2]
            context.bot.send_message(chat_id=update.message.chat_id, text=str(e))
            raise e
        return return_value
    return method_wrapper


class TeamKeshi():
    def __init__(self, all_players):
        self.players = [player for player in all_players if player.order_id>=0]
        self.players = sorted(self.players, key = lambda x:x.order_id)[:10]
        self.teams = OrderedDict()
        self.who_validated = []

    def add_captain(self, captain_player):
        if captain_player not in self.teams:
            self.teams[captain_player] = []
            self.teams[captain_player].append(captain_player)

    def add_player(self, captain_player, player):
        self.teams[captain_player].append(player)

    def convert_to_persian_number(self, number):
        persian_num = ''
        number = '{0:.1f}'.format(number) if int(number) != number else str(int(number))
        for digit in number:
            try:
                persian_num += per_digits[int(digit)]
            except:
                persian_num += '.'
        return persian_num

    def create_player_keyboard(self):
        cur_players = [player.foot_name for captain, players in self.teams.items() for player in players]
        players = []
        for player in self.players:
            if player.foot_name in cur_players:
                continue
            if player.foot_rates is not None:
                players.append('{}: {}'.format(player.foot_name, '|'.join([self.convert_to_persian_number(rate) for rate in player.foot_rates.tolist()])))
            else:
                players.append(player.foot_name)
        return create_player_keyboard(players)

    def is_finish(self):
        """
        Returns True if both teams are completed
        """
        if len(self.teams) == 0:
            return False
        for captain, players in self.teams.items():
            if len(players) < 5:
                return False
        return True

    def is_both_validated(self):
        """
        Returns True if both teams are completed
        """
        return len(self.who_validated) == 2
    
    def print_teams(self, sort, show_rates):
        """
        Prints current state of teams
        """
        txt = ''
        for captain, players in self.teams.items():
            is_white = captain == list(self.teams.keys())[0]
            txt += '\n\u200f'
            txt += 3*'\u26aa' if is_white else 3*'\U0001f534' # Blue = \U0001f535
            txt += ' {} {} '.format(PerWord.team, PerWord.white if is_white else PerWord.red)
            txt += 3*'\u26aa' if is_white else 3*'\U0001f534' # Blue = \U0001f535
            txt += '\n'

            if sort:
                players = sorted(players, key = lambda x:x.first_name) # Sort players alphebatically

            if show_rates:
                rates = pd.Series((0,0,0,0))
                nb = 0
                for player in players:
                    if player.foot_rates is not None:
                        rates += player.foot_rates
                        nb += 1
                rates = rates/nb
                rate_goa = self.convert_to_persian_number(rates[0])
                rate_def = self.convert_to_persian_number(rates[1])
                rate_att = self.convert_to_persian_number(rates[2])
                rate_run = self.convert_to_persian_number(rates[3])
                txt += '{}\n'.format(Msg.team_rates.format(rate_goa, rate_def, rate_att, rate_run))
            for idx, player in enumerate(players):
                txt += '\u200f{}. {}\n'.format(per_digits[idx+1], player.foot_name)
            txt += '\u200f'

        return txt

    def whose_turn(self):
        """
        Indicates whose turn is when selecting players or validating
        """
        captain_1 = list(self.teams.keys())[0]
        captain_2 = list(self.teams.keys())[1]
        is_finish = self.is_finish()
        if is_finish:
            return captain_2 if captain_1 in self.who_validated else captain_1
        if len(self.teams[captain_1]) == len(self.teams[captain_2]):
            rate_1 = captain_1.foot_rates.mean()
            rate_2 = captain_2.foot_rates.mean()
            if rate_1 > 0 and rate_2 > 0:
                return captain_1 if rate_1 <= rate_2 else captain_2
        return captain_1 if len(self.teams[captain_1]) <= len(self.teams[captain_2]) else captain_2

    def set_validation(self, captain):
        """
        Keep the captain name who validates teams
        """
        self.who_validated.append(captain)

    def get_keyboard(self):
        """
        Returns appropriated keyboard depending on situation of team-keshi
        """
        is_finish = self.is_finish()
        if is_finish:
            keyboard = create_validation_keyboard()
        else:
            keyboard = self.create_player_keyboard()
        return keyboard
        
    def get_msg(self):
        """
        Returns appropriated message depending on situation of team-keshi
        """
        is_finish = self.is_finish()
        foot_name = self.whose_turn().foot_name
        return '\u200f{} {}\n{}'.format(foot_name, Msg.ask_validation if is_finish else Msg.select_player, self.print_teams(False, True))


class FootUser():
    def __init__(self, user_id, first_name, last_name):
        self.id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.user_name = self.make_camel_case(first_name, last_name)
        self.foot_name = self.get_foot_name()
        self.foot_rates = self.get_rates()

        # They will be set later
        self.is_forbidden = False
        self.order_id = -1 # if order id is bigger-equal than 0, it means user plays in the next match
        self.is_admin = False

    def get_rates(self):
        if self.id in list(players_info.keys()):
            return pd.Series(players_info[self.id][1])
        if self.user_name.lower() in list(foreign_players_rates.keys()):
            return pd.Series(foreign_players_rates[self.user_name.lower()])
        return None

    @staticmethod
    def make_camel_case(first_name, last_name):
        try:
            return '{}{} {}{}'.format(first_name[0].upper(), first_name[1:].lower(), last_name[0].upper(), last_name[1].lower())
        except:
            return '{}{}'.format(first_name[0].upper(), first_name[1:].lower())

    def get_foot_name(self):
        try:
            return players_info[self.id][0]
        except:
            return self.user_name

    @staticmethod
    def get_foot_user(all_players, user_id=None, user_name=None, foot_name=None):
        """
        Returns FootUser by the given user_id
        """
        for user in all_players:
            if user_id and user.id == user_id:
                return user
            if user_name and user.user_name.lower() == user_name.lower():
                return user
            if foot_name and user.foot_name == foot_name:
                return user



class Foot4Ever():
    """
    Manages everything about weekly foot sessions
    """
    def __init__(self):
        self.token = os.getenv('TOKEN')
        updater = Updater(token=self.token, use_context=True)
        self.bot = Bot(self.token)

        self.init_users_and_chats()
        self.init_dates()
        self.reset_teams()

        # Define a job to send weekly program with interval 7*24*60*60, 7 days, 24 hours, 60 minutes and 60 seconds
        open_inscription_date = self.get_open_inscription_date(self.next_date)
        if datetime.datetime.now() < open_inscription_date:
            updater.job_queue.run_repeating(self.send_weekly_prog, interval=7*24*60*60, first=open_inscription_date)

        # Define commands
        self.init_commands(updater.dispatcher)

        # log all errors
        updater.dispatcher.add_error_handler(self.error)

        self.run(updater)

    def run(self, updater):
        mode = os.getenv('MODE')
        if mode == 'DEV':
            updater.start_polling()
            updater.idle()
        elif mode == 'PROD':
            port = int(os.environ.get('PORT', '8443'))
            app_name = os.environ.get('APP_NAME')
            updater.start_webhook(listen='0.0.0.0', port=port, url_path=self.token)
            updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(app_name, self.token))
        else:
            logger.error('Invalid mode')
            sys.exit(1)

    @WithLogError
    def set_prog(self, update, context):
        """
        Command to set date, time and center of the next session
        """
        cur_chat_id = update.effective_message.chat_id
        try:
            parts = ' '.join(context.args).split(',')
            date = parts[0]
            center_index = int(parts[1])
        except:
            context.bot.send_message(chat_id=cur_chat_id, text='{}\n{}'.format(Msg.bad_set_prog_msg, Msg.bad_set_prog_format))
            return

        self.init_dates(date, center_index)
        self.reset_teams()
        for user in self.all_players:
            user.order_id = default_next_players.index(user.id) if user.id in default_next_players else -1
        context.bot.send_message(chat_id=cur_chat_id, text=Msg.bad_set_prog_succeed)
        self.get_prog(update, context)

    def init_dates(self, date = '20/06/2018 19:30', center_index = 2):
        """
        Information about next foot session
        """
        self.next_date = datetime.datetime.strptime(date, '%d/%m/%Y %H:%M') ##
        self.next_center_index = center_index
        self.centers = {'Aubervilliers':(48.907591, 2.375871), 'La Defense':(48.899902, 2.221698), "Porte d'Ivry":(48.820167, 2.393684)}

    def send_weekly_prog(self, bot, job):
        """
        Job to send weekly program
        """
        bot.send_message(chat_id=self.foot_chat_id, text=self.get_next_program(), parse_mode='HTML')
        lat, lon = list(self.centers.values())[self.next_center_index]
        bot.send_location(chat_id=self.foot_chat_id, latitude=lat, longitude=lon)

    def init_commands(self, dp):
        """
        Init available commands
        """
        dp.add_handler(CommandHandler('start', self.start))
        dp.add_handler(CommandHandler('add', self.add_player, pass_args=True, pass_user_data=True))
        dp.add_handler(CommandHandler('del', self.del_player, pass_args=True, pass_user_data=True))
        dp.add_handler(CommandHandler('prog', self.get_prog))
        dp.add_handler(CommandHandler('help', self.help))
        dp.add_handler(CommandHandler('help_admins', self.help_admins))
        dp.add_handler(CommandHandler('all', self.get_all_players_username))
        dp.add_handler(CommandHandler('add_mahroom', self.show_add_forbidden_player_keyboard, pass_user_data=True))
        dp.add_handler(CommandHandler('del_mahroom', self.show_del_forbidden_player_keyboard, pass_user_data=True))
        dp.add_handler(CommandHandler('timkeshi', self.show_timkeshi_buttons, pass_user_data=True))
        dp.add_handler(CommandHandler('set_prog', self.set_prog, pass_args=True, pass_user_data=True))
        dp.add_handler(CallbackQueryHandler(self.on_btn_callback))

    def init_users_and_chats(self):
        self.chat_info_path = os.path.join(os.path.split(__file__)[0], 'chat_info.txt')
        if os.path.exists(self.chat_info_path):
            with open(self.chat_info_path) as f:
                self.chat_ids = json.load(f) # contains all users Id:UserName
        else:
            self.chat_ids = {}
        self.foot_chat_id = self.chat_ids['Urban Football']
    
        self.all_players = []
        self.user_info_path = os.path.join(os.path.split(__file__)[0], 'user_info.txt')
        self.load_users()

    def load_users(self):
        """
        Load all users info via user info file which contains user Ids
        """
        self.admins = []
        self.bot.get_chat_administrators(self.foot_chat_id)
        for chat_member in self.bot.get_chat_administrators(self.foot_chat_id):
            user = chat_member.user
            id, first_name, last_name = user.id, user.first_name, user.last_name
            print('{}: {} {}'.format(id, first_name, last_name))
            user = FootUser(id, first_name, last_name)
            if user.id in default_next_players:
                user.order_id = default_next_players.index(user.id)
            if user.first_name.lower() in ['pasha', 'saman']:
                self.admins.append(user.id)
                user.is_admin = True
            self.all_players.append(user)
        self.save_all_users_info()

    def reset_teams(self):
        self.is_timkeshi_running = False
        self.team_keshi = TeamKeshi(self.all_players)
    
    @WithLogError
    def help(self, update, context):
        help_txt = ''
        for cmd, help in public_cmds.items():
            help_txt += '{}: /{}\n'.format(help, cmd)
        update.message.reply_text(help_txt)

    @WithLogError
    def help_admins(self, update, context):
        help_txt = ''
        for cmd, help in admin_cmds.items():
            help_txt += '{}: /{}\n'.format(help, cmd)
        update.message.reply_text(help_txt)
    
    def error(self, bot, update, err):
        """
        Log Errors caused by Updates.
        """
        logger.warning('Update "%s" caused error "%s"', update, err)

    @WithLogError
    def get_prog(self, update, context):
        msg = '{}\n{}'.format(Msg.next_week_prog, self.get_next_program()) 
        context.bot.send_message(chat_id=update.message.chat_id, text=msg, parse_mode='HTML')
        lat, lon = list(self.centers.values())[self.next_center_index]
        context.bot.send_location(chat_id=update.message.chat_id, latitude=lat, longitude=lon) 

    def get_next_program(self):
        """
        Next session date & center
        """
        # another calendar icon: \U0001f4c6
        msg = '\u200f \U0001f4c5 <b>{}</b> - {} \n'.format(per_day_names[self.next_date.weekday()], self.next_date.strftime('%d/%m/%Y'))
        msg += '\u200f \u23f0 <b>{}</b> - {} \n'.format(self.next_date.strftime('%Hh%M'), (self.next_date+datetime.timedelta(minutes=90)).strftime('%Hh%M'))
        msg += '\u200f \U0001f4cd Urbansoccer <b>{}</b> \n'.format(list(self.centers.keys())[self.next_center_index])
        return msg

    def get_program_and_players(self):
        """
        Next session program & players
        """
        msg = '{}\n'.format(self.get_next_program())
        next_players = sorted(self.all_players, key = lambda x:x.order_id)
        next_players = [player.foot_name for player in next_players if player.order_id>=0]
        
        for index, player in enumerate(next_players):
            if index == 10:
                msg += '\n{}:\n'.format(Msg.reserve)
            msg += '\u200f{}. {}\n'.format(per_digits[index+1] if index < 10 else per_digits[index-9], player)
        msg += '\u200f'
        return msg

    @WithLogError
    def start(self, update, context):
        return
        txt = 'به روبات گروه فوتبال خوش آمدید. دستورات زیر قابل استفاده می باشند'
        for cmd, help in public_cmds.items():
            help_txt += '\n{}: /{}'.format(help, cmd)
        context.bot.send_message(chat_id=update.message.chat_id, text=txt)

    def get_user_from_update(self, update):
        """
        Get current user name
        """
        e_user = update.effective_user
        user = FootUser.get_foot_user(self.all_players, user_id=e_user.id)
        if not user:
            user = FootUser(e_user.id, e_user.first_name, e_user.last_name)
            user.is_admin = user.id in self.admins
            self.all_players.append(user)
            self.save_all_users_info()
        return user

    def get_open_inscription_date(self, date):
        weekday_delta = {6:9, 5:8, 4:7, 3:6, 2:5, 1:4, 0:3}
        date -= datetime.timedelta(days=weekday_delta[date.weekday()])
        return date.replace(hour=18).replace(minute=0)

    def is_admin(self, bot, update):
        """
        Returns True if the user is admin, else returns False with an alert message
        """
        user = self.get_user_from_update(update)
        if not user.is_admin:
            bot.send_message(chat_id=update.effective_message.chat_id, text=Msg.missing_permission)
            return False
        return True

    def get_next_order_id(self):
        """
        Returns the next order Id for players who play in the next match
        """
        order_id = -1
        for player in self.all_players:
            if player.order_id > order_id:
                order_id = player.order_id
        return 0 if order_id==-1 else order_id+1
    
    @WithLogError
    def add_player(self, update, context):
        cur_chat_id = update.effective_message.chat_id
        user = self.get_user_from_update(update)
        is_pasha = user.first_name.lower() == 'pasha'
        if not is_pasha and cur_chat_id != self.foot_chat_id:
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.wrong_page_add_del)
            return
        
        if len(context.args)>0:
            return self.add_del_forced_player(context.bot, update, context.args, True)
        
        if user.is_forbidden:
            foot_name = PersianNames[user.first_name.lower()]
            context.bot.send_message(chat_id=cur_chat_id, text='{} {}{}'.format(foot_name, PerWord.jan, Msg.you_are_forbidden))
            return

        now = datetime.datetime.now()
        if not is_pasha and (now > self.next_date or now < self.get_open_inscription_date(self.next_date)):
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.too_late_add)
            return

        if user.order_id < 0:
            user.order_id = self.get_next_order_id()
            context.bot.send_message(chat_id=cur_chat_id, text=self.get_program_and_players(), parse_mode='HTML')
    
    @WithLogError
    def del_player(self, update, context):
        cur_chat_id = update.effective_message.chat_id
        user = self.get_user_from_update(update)
        if cur_chat_id != self.foot_chat_id and user.first_name.lower() != 'pasha':
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.wrong_page_add_del)
            return

        if len(context.args)>0:
            return self.add_del_forced_player(context.bot, update, context.args, False)
        
        is_pasha = user.first_name.lower() == 'pasha'
        if not is_pasha and datetime.datetime.now() + datetime.timedelta(days=2) > self.next_date:
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.too_late_del)
            context.bot.send_message(chat_id=self.chat_ids['Foot Admin'], text='{} {}'.format(user.foot_name, Msg.try_to_del))
            return

        if user.order_id>=0:
            user.order_id = -1
            context.bot.send_message(chat_id=cur_chat_id, text=self.get_program_and_players(), parse_mode='HTML')
    
    def add_del_forced_player(self, bot, update, args, is_in_next_match):
        """
        ADMIN ONLY: Add forced player
        """
        if not self.is_admin(bot, update):
            return
    
        for player in ' '.join(args).split(','):
            user = FootUser.get_foot_user(self.all_players, user_name=player)
            if not user:
                names = player.split(' ')
                user = FootUser(0, names[0], names[1] if len(names)>1 else '')
                self.all_players.append(user)
            if is_in_next_match:
                user.order_id = self.get_next_order_id()
            else:
                user.order_id = -1
            
        bot.send_message(chat_id=update.effective_message.chat_id, text=self.get_program_and_players(), parse_mode='HTML')

    def save_all_users_info(self):
        """
        Keep user names & Ids in a file
        """
        if len(self.all_players) > 0:
            with open(self.user_info_path, 'w') as f:
                f.write(json.dumps({user.id:user.user_name for user in self.all_players if user.user_name}))
        if len(self.chat_ids) > 0:
            with open(self.chat_info_path, 'w') as f:
                f.write(json.dumps(self.chat_ids))

    @WithLogError
    def show_add_forbidden_player_keyboard(self, update, context):
        """
        ADMIN ONLY: Shows a keyboard to select forbidden player from the next session
        """
        if self.is_admin(context.bot, update):
            players = [user.foot_name for user in self.all_players if not user.is_forbidden]
            reply_markup = InlineKeyboardMarkup(create_player_keyboard(players))
            update.message.reply_text(Msg.select_forbidden_player, reply_markup=reply_markup)

    @WithLogError
    def show_del_forbidden_player_keyboard(self, update, context):
        """
        ADMIN ONLY: Shows a keyboard to delete a forbidden player from the next session
        """
        if self.is_admin(context.bot, update):
            forbidden_players = [user.foot_name for user in self.all_players if user.is_forbidden]
            if not forbidden_players:
                context.bot.send_message(text=Msg.no_forbidden_player, chat_id=update.message.chat_id)
            else:
                reply_markup = InlineKeyboardMarkup(create_player_keyboard(forbidden_players))
                update.message.reply_text(Msg.select_unforbidden_player, reply_markup=reply_markup)

    def on_btn_add_forbidden_player(self, bot, update):
        """
        Add forbidden player from the next session
        """
        query = update.callback_query
        if query.data == PerWord.cancel:
            bot.edit_message_text(text=Msg.operation_cancelled, message_id=query.message.message_id, chat_id=query.message.chat_id)
            return

        user = FootUser.get_foot_user(self.all_players, foot_name=query.data)
        user.is_forbidden = True
        user.order_id = -1

        msg = '{}\n{}'.format('بازیکنان محروم:', ', '.join([user.foot_name for user in self.all_players if user.is_forbidden]))
        bot.edit_message_text(text=msg, message_id=query.message.message_id, chat_id=query.message.chat_id)
        bot.send_message(chat_id=query.message.chat_id, text=self.get_program_and_players(), parse_mode='HTML')

    def on_btn_del_forbidden_player(self, bot, update):
        """
        Delete forbidden player from the next session
        """
        query = update.callback_query
        if query.data == PerWord.cancel:
            bot.edit_message_text(text=Msg.operation_cancelled, message_id=query.message.message_id, chat_id=query.message.chat_id)
            return
    
        user = FootUser.get_foot_user(self.all_players, foot_name=query.data)
        user.is_forbidden = False
        
        forbidden_players = [user.foot_name for user in self.all_players if user.is_forbidden]
        msg = '{}\n{}'.format('بازیکنان محروم', ', '.join(forbidden_players)) if forbidden_players else Msg.no_forbidden_player
        bot.edit_message_text(text=msg, message_id=query.message.message_id, chat_id=query.message.chat_id)

    @WithLogError
    def get_all_players_username(self, update, context):
        """
        Returns all registered players
        """
        update.message.reply_text(text='\n'.join([user.user_name for user in self.all_players]))

    @WithLogError
    def show_timkeshi_buttons(self, update, context):
        """
        Creates inline keyboard for team keshi
        """
        if update.message.chat.title == 'Urban Football':
            context.bot.send_message(chat_id=update.message.chat_id, text=Msg.wrong_place_timkeshi)
            return
        if self.is_timkeshi_running:
            context.bot.send_message(chat_id=update.message.chat_id, text=Msg.timkeshi_is_running)
            return

        self.reset_teams()
        self.is_timkeshi_running = True
        cur_user = self.get_user_from_update(update)
        self.team_keshi.add_captain(cur_user) # Add first captain
        reply_markup = InlineKeyboardMarkup(create_validation_keyboard())
        update.message.reply_text('{} {}'.format(cur_user.foot_name, Msg.teamkeshi_welcome), reply_markup=reply_markup)

    def on_show_timkeshi_buttons(self, bot, update):
        """
        Creates inline keyboard for team keshi
        """
        reply_markup = InlineKeyboardMarkup(self.team_keshi.get_keyboard())
        message= update.effective_message
        bot.edit_message_text(text=self.team_keshi.get_msg(), message_id=message.message_id, chat_id=message.chat_id, reply_markup=reply_markup)

    @WithLogError
    def on_btn_callback(self, update, context):
        text = update.callback_query.message.text
        if text == Msg.select_forbidden_player:
            self.on_btn_add_forbidden_player(context.bot, update)
        elif text == Msg.select_unforbidden_player:
            self.on_btn_del_forbidden_player(context.bot, update)
        else:
            self.on_btn_teamkeshi(context.bot, update)
    
    def on_btn_teamkeshi(self, bot, update):
        """
        Performs the related action when user touch on of the team-keshi buttons
        """
        query = update.callback_query
        if query.data in [PerWord.cancel, PerWord.no]:
            bot.edit_message_text(text=Msg.operation_cancelled, message_id=query.message.message_id, chat_id=query.message.chat_id)
            self.reset_teams()
            return

        cur_user = self.get_user_from_update(update)
        if query.data == PerWord.yes:
            if self.team_keshi.is_finish():
                self.team_keshi.set_validation(self.team_keshi.whose_turn())
                if self.team_keshi.is_both_validated():
                    self.bot.send_message(self.chat_ids['Foot Admin'], self.team_keshi.print_teams(False, True))
                    final_teams = self.team_keshi.print_teams(True, False)
                    msg = '{}\n{}'.format(Msg.validation_finish, final_teams)
                    bot.edit_message_text(text=msg, chat_id=query.message.chat_id, message_id=query.message.message_id)
                    captain1, captain2 = list(self.team_keshi.teams.keys())[0].foot_name, list(self.team_keshi.teams.keys())[1].foot_name
                    self.bot.send_message(self.chat_ids['Foot Admin'], Msg.validation_finish2.format(captain1, captain2))##
                    msg = '{}{}'.format(self.get_next_program(), final_teams)
                    self.bot.send_message(self.chat_ids['Foot Admin'], msg, parse_mode='HTML')##
                    self.reset_teams()
                    return
            else:
                #cur_user = FootUser.get_foot_user(self.all_players, user_id=UserIds.ali_cre) ##
                if cur_user.id == list(self.team_keshi.teams.keys())[0].id:
                    msg = '{} {}\n'.format(cur_user.foot_name, Msg.restart_timkeshi)
                    msg += '{} {}'.format(cur_user.foot_name, Msg.teamkeshi_welcome)
                    update.effective_message.reply_text(msg)
                    return
                self.team_keshi.add_captain(cur_user) # Add 2nd captain
        else:
            #cur_user = self.team_keshi.whose_turn() ##
            if cur_user.id == self.team_keshi.whose_turn().id:
                self.team_keshi.add_player(cur_user, FootUser.get_foot_user(self.all_players, foot_name=query.data.split(':')[0]))

        self.on_show_timkeshi_buttons(bot, update)



def main():
    try:
        app = Foot4Ever()
    except Exception as e:
        str(e)
        raise e

if __name__ == '__main__':
    main()