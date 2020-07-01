# --------------------------------------------------------------------------- #
# Name:        Manage foot inscription & teams
#
# Author:      Pasha Shadkami
#
# Created:     27/10/2019
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
import boto3

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

public_cmds = OrderedDict([('add',"S'inscrire dans le prochain match"),
                           ('del',"Annuler l'inscription"),
                           ('prog',"Afficher le prochain programme du jeu"),
                           ('players',"Afficher les joueurs du prochain jeu"),
                           ('arrange',"Arranger les équipes")])
admin_cmds = OrderedDict([('add',"S'inscrire dans le prochain match"),
                          ('del',"Annuler l'inscription"),
                          ('add_susp',"Susprendre un joueur"),
                          ('del_susp',"Annuler la suspension d'un joueur"),
                          ('set_prog',"Mettre le prochain jeu"),
                          ('all',"Afficher tous les noms"),
                          ('next', 'Afficher le jour dans 45 jours')])
                          
class Msg():
    wrong_page_add_del = "Pour s'inscrire ou annuler l'inscription, allez d'abord sur la page du groupe."
    wrong_place_timkeshi = "Pour arranger les équipes, créez d'abord un groupe, invitez ensuite l'autre capitaine."
    you_are_forbidden = "Oops! Tu es suspendu pour le prochain jeu!"
    too_late_del = "L'inscription ne peut pas être annulée dans les dernières 48h! Tu contactes les admins stp."
    restart_timkeshi = "Je ne parlais pas à toi, je parlais au deuxième capitaine"
    missing_permission = "Tu n'es pas autorisé à utiliser cette commande! Désolé!"
    select_player = "c'est à toi de choisir (le score est de 1 à 5 dans cet ordre: goal, défense, attaque, course)"
    teamkeshi_welcome = "je te remercie d'avoir commancé l'arrangement des équipes. Le deuxième capitaine, es-tu aussi prêt?"
    validation_finish = "Parfait! Tout est nickel, les équipes seront envoyées aux admins."
    validation_finish2 = "Voici les équipes faites par {} et {}:"
    team_rates = "Goal: {}, Défense: {}, Attaque: {}, Course: {}"
    ask_validation = "Tu confirmes ton équipe?"
    select_forbidden_player = "Tu peux choisir maintenant le joueur suspendu du prochain match:"
    select_unforbidden_player = "Tu peux enlever maintenant le joueur suspendu du prochain match:"
    no_forbidden_player = "Il n'y a aucun joueur suspendu"
    forbidden_player = "Joueurs supendus:"
    operation_cancelled = "L'operation a été annulée."
    try_to_del = "a voulu annulé mais je l'ai empêché! Tu veux l'appeler peut-être?"
    next_week_prog = "Le prochain jeu:"
    reserve = "Les réserves"
    timkeshi_is_running = "L'arrangement des équipes est en train! Pour recommancer, il faut d'abord annuler celui d'en cours."
    bad_set_prog_msg = "Le format doit être 'date heure, centre',\npar exemple: 01/01/2019 20:30, 0"
    bad_set_prog_succeed = "Le changement suivant a effectué avec du succès:"
    sign_up_not_started = "La date du prochain jeu n'est pas encore définie."
    next_potential_date = '45 days later will be {}'
    
# The description to set in bot father
"""
add - s'inscrire dans le prochain jeu
del - annuler l'inscription
prog - afficher la date du prochain jeu
players - afficher les joueurs du prochain jeu
arrange - faire des équipe
help - aide
help_admins - aide admins
"""

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
    keyboard.append([InlineKeyboardButton(MotFr.cancel, callback_data=MotFr.cancel)])
    return keyboard

def create_validation_keyboard():
    keyboard = [[InlineKeyboardButton(MotFr.yes, callback_data=MotFr.yes),
                 InlineKeyboardButton(MotFr.no, callback_data=MotFr.no)]]
    return keyboard


class MotFr():
    monday = 'Lundi'
    tuesday = 'Mardi'
    wednesday = 'Mercredi'
    thursday = 'Jeudi'
    friday = 'Vendredi'
    saturday = 'Samedi'
    sunday = 'Dimanche'

    cancel = 'Anuler'
    yes = 'Oui'
    no = 'Non'
    jan = 'cher, '
    team = 'Equipe'
    white = 'blanche'
    red = 'rouge'


day_names = {0:MotFr.monday, 1:MotFr.tuesday, 2:MotFr.wednesday, 3:MotFr.thursday, 4:MotFr.friday, 5:MotFr.saturday, 6:MotFr.sunday}


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

    def format_number(self, number):
        return '{0:.1f}'.format(number) if int(number) != number else str(int(number))

    def create_player_keyboard(self):
        cur_players = [player.user_name for captain, players in self.teams.items() for player in players]
        players = []
        for player in self.players:
            if player.user_name in cur_players:
                continue
            if player.foot_rates is not None:
                players.append('{}: {}'.format(player.user_name, '|'.join([self.format_number(rate) for rate in player.foot_rates.tolist()])))
            else:
                players.append(player.user_name)
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
            txt += 3*'\u26aa' if is_white else 3*'\U0001f534' # Blue = \U0001f535
            txt += ' {} {} '.format(MotFr.team, MotFr.white if is_white else MotFr.red)
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
                rate_goa = self.format_number(rates[0])
                rate_def = self.format_number(rates[1])
                rate_att = self.format_number(rates[2])
                rate_run = self.format_number(rates[3])
                txt += '{}\n'.format(Msg.team_rates.format(rate_goa, rate_def, rate_att, rate_run))
            for idx, player in enumerate(players):
                txt += '{}. {}\n'.format(idx+1, player.user_name)
            txt += '\n'
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
        user_name = self.whose_turn().user_name
        return '{}, {}\n\n{}'.format(user_name, Msg.ask_validation if is_finish else Msg.select_player, self.print_teams(False, True))


class FootUser():
    def __init__(self, user_id, first_name, last_name, players_info, foreign_players_rates):
        self.id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.user_name = self.make_camel_case(first_name, last_name)
        self.foot_rates = self.get_rates(players_info, foreign_players_rates)

        # They will be set later
        self.is_forbidden = False
        self.order_id = -1 # if order id is bigger-equal than 0, it means user plays in the next match
        self.is_admin = False

    def get_rates(self, players_info, foreign_players_rates):
        if str(self.id) in list(players_info.keys()):
            return pd.Series(players_info[str(self.id)][1])
        if self.user_name.lower() in foreign_players_rates:
            return pd.Series(foreign_players_rates[self.user_name.lower()])
        return None

    @staticmethod
    def make_camel_case(first_name, last_name):
        try:
            return '{}{} {}{}'.format(first_name[0].upper(), first_name[1:].lower(), last_name[0].upper(), last_name[1].lower())
        except:
            return '{}{}'.format(first_name[0].upper(), first_name[1:].lower())

    @staticmethod
    def get_foot_user(all_players, user_id=None, user_name=None):
        """
        Returns FootUser by the given user_id
        """
        for user in all_players:
            if user_id and user.id == user_id:
                return user
            if user_name and user.user_name.lower() == user_name.lower():
                return user


class Foot4Ever():
    """
    Manages everything about weekly foot sessions
    """
    def __init__(self):
        self.mode = os.getenv('MODE')
        self.token = os.getenv('TOKEN')
        updater = Updater(token=self.token, use_context=True)
        self.bot = Bot(self.token)

        self.init_dates()
        self.init_users_and_chats()
        self.reset_teams()

        open_inscription_date = self.get_open_inscription_date(self.next_date)

        # Define commands
        self.init_commands(updater.dispatcher)

        # log all errors
        updater.dispatcher.add_error_handler(self.error)

        self.run(updater)

    def run(self, updater):
        if self.mode == 'DEV':
            updater.start_polling()
            updater.idle()
        elif self.mode == 'PROD':
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
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.bad_set_prog_msg)
            return

        self.init_dates(date, center_index)
        self.reset_teams()
        for user in self.all_players:
            user.order_id = self.admins.index(user.id) if user.id in self.admins else -1
        context.bot.send_message(chat_id=cur_chat_id, text=Msg.bad_set_prog_succeed)
        self.get_prog(update, context)
        self.save_match_info()

    def init_dates(self, date = '20/06/2018 19:30', center_index = 2):
        """
        Information about next foot session
        """
        self.next_date = datetime.datetime.strptime(date, '%d/%m/%Y %H:%M')
        self.next_center_index = center_index
        self.centers = {'Aubervilliers':(48.907591, 2.375871), 'La Defense':(48.899902, 2.221698), "Porte d'Ivry":(48.820167, 2.393684)}

    def init_commands(self, dp):
        """
        Init available commands
        """
        dp.add_handler(CommandHandler('start', self.start))
        dp.add_handler(CommandHandler('add', self.add_player, pass_args=True, pass_user_data=True))
        dp.add_handler(CommandHandler('del', self.del_player, pass_args=True, pass_user_data=True))
        dp.add_handler(CommandHandler('prog', self.get_prog))
        dp.add_handler(CommandHandler('players', self.get_next_players))
        dp.add_handler(CommandHandler('help', self.help))
        dp.add_handler(CommandHandler('help_admins', self.help_admins))
        dp.add_handler(CommandHandler('all', self.get_all_players_username))
        dp.add_handler(CommandHandler('next', self.get_next_date))
        dp.add_handler(CommandHandler('add_susp', self.show_add_forbidden_player_keyboard, pass_user_data=True))
        dp.add_handler(CommandHandler('del_susp', self.show_del_forbidden_player_keyboard, pass_user_data=True))
        dp.add_handler(CommandHandler('arrange', self.show_timkeshi_buttons, pass_user_data=True))
        dp.add_handler(CommandHandler('set_prog', self.set_prog, pass_args=True, pass_user_data=True))
        dp.add_handler(CallbackQueryHandler(self.on_btn_callback))

    def init_users_and_chats(self):
        self.chat_info_path = os.path.join(os.path.split(__file__)[0], 'chat_info.txt')
        if os.path.exists(self.chat_info_path):
            with open(self.chat_info_path) as f:
                self.chat_ids = json.load(f)
        else:
            self.chat_ids = {}
        self.foot_chat_id = self.chat_ids['Urban Football']
    
        self.all_players = []
        self.cur_players = []
        self.init_s3()
        self.load_user_rates()
        self.load_match_info()
        #self.cur_players = [int(user_id) for user_id in self.players_info.keys()] ##
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
            user = FootUser(id, first_name, last_name, self.players_info, self.foreign_players_rates)
            if user.id in self.cur_players:
                user.order_id = self.cur_players.index(user.id)
                #print(f'{user.order_id},{user.user_name}')
            if user.first_name.lower() in ['pasha', 'saman']:
                self.admins.append(user.id)
                user.is_admin = True
            self.all_players.append(user)
        # Add foreign players as well
        for player in self.cur_players:
            if isinstance(player, str):
                #print(player)
                user = self.add_foreign_player(player, False)
                user.order_id = self.cur_players.index(player)
        #self.save_all_users_info()

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
        if self.next_date < datetime.datetime.now():
            context.bot.send_message(chat_id=update.message.chat_id, text=Msg.sign_up_not_started)
            return
        msg = '{}\n{}'.format(Msg.next_week_prog, self.get_next_program()) 
        context.bot.send_message(chat_id=update.message.chat_id, text=msg, parse_mode='HTML')
        lat, lon = list(self.centers.values())[self.next_center_index]
        context.bot.send_location(chat_id=update.message.chat_id, latitude=lat, longitude=lon) 

    def get_next_program(self):
        """
        Next session date & center
        """
        # another calendar icon: \U0001f4c6
        msg = '\U0001f4c5 <b>{}</b> - {} \n'.format(day_names[self.next_date.weekday()], self.next_date.strftime('%d/%m/%Y'))
        msg += '\u23f0 <b>{}</b> - {} \n'.format(self.next_date.strftime('%Hh%M'), (self.next_date+datetime.timedelta(minutes=90)).strftime('%Hh%M'))
        msg += '\U0001f4cd Urbansoccer <b>{}</b> \n'.format(list(self.centers.keys())[self.next_center_index])
        return msg

    @WithLogError
    def get_next_players(self, update, context):
        """
        Next session program & players
        """
        cur_chat_id = update.effective_message.chat_id
        context.bot.send_message(chat_id=cur_chat_id, text=self.get_program_and_players(), parse_mode='HTML')
        
    def get_program_and_players(self):
        """
        Next session program & players
        """
        msg = '{}\n'.format(self.get_next_program())
        next_players = sorted(self.all_players, key = lambda x:x.order_id)
        next_players = [player.user_name for player in next_players if player.order_id>=0]
        
        for index, player in enumerate(next_players):
            if index == 10:
                msg += '\n{}:\n'.format(Msg.reserve)
            msg += '{}. {}\n'.format(index+1 if index < 10 else index-9, player)
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
            user = FootUser(e_user.id, e_user.first_name, e_user.last_name, self.players_info, self.foreign_players_rates)
            user.is_admin = user.id in self.admins
            self.all_players.append(user)
            #self.save_all_users_info()
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
        if self.next_date < datetime.datetime.now():
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.sign_up_not_started)
            return
            
        if not is_pasha and cur_chat_id != self.foot_chat_id:
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.wrong_page_add_del)
            return
        
        if len(context.args)>0:
            return self.add_del_forced_player(context.bot, update, context.args, True)
        
        if user.is_forbidden:
            context.bot.send_message(chat_id=cur_chat_id, text='{}, {}'.format(user.user_name, Msg.you_are_forbidden))
            return

        if user.order_id < 0:
            user.order_id = self.get_next_order_id()
            context.bot.send_message(chat_id=cur_chat_id, text=self.get_program_and_players(), parse_mode='HTML')
            self.save_match_info()
    
    @WithLogError
    def del_player(self, update, context):
        cur_chat_id = update.effective_message.chat_id
        user = self.get_user_from_update(update)
        is_pasha = user.first_name.lower() == 'pasha'
        if self.next_date < datetime.datetime.now():
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.sign_up_not_started)
            return
            
        if cur_chat_id != self.foot_chat_id and user.first_name.lower() != 'pasha':
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.wrong_page_add_del)
            return

        if len(context.args)>0:
            return self.add_del_forced_player(context.bot, update, context.args, False)
        
        if not is_pasha and datetime.datetime.now() + datetime.timedelta(days=2) > self.next_date:
            context.bot.send_message(chat_id=cur_chat_id, text=Msg.too_late_del)
            context.bot.send_message(chat_id=self.chat_ids['Foot Admin'], text='{} {}'.format(user.user_name, Msg.try_to_del))
            return

        if user.order_id>=0:
            user.order_id = -1
            context.bot.send_message(chat_id=cur_chat_id, text=self.get_program_and_players(), parse_mode='HTML')
            self.save_match_info()
    
    def add_del_forced_player(self, bot, update, args, is_in_next_match):
        """
        ADMIN ONLY: Add forced player
        """
        if not self.is_admin(bot, update):
            return
    
        for player in ' '.join(args).split(','):
            self.add_foreign_player(player, is_in_next_match)
            
        bot.send_message(chat_id=update.effective_message.chat_id, text=self.get_program_and_players(), parse_mode='HTML')
        self.save_match_info()

    def add_foreign_player(self, player, is_in_next_match):
        """
        Add manually a player in the list of all players and for the next match
        """
        user = FootUser.get_foot_user(self.all_players, user_name=player)
        if not user:
            names = player.split(' ')
            user = FootUser(0, names[0], names[1] if len(names)>1 else '', self.players_info, self.foreign_players_rates)
            self.all_players.append(user)
        if is_in_next_match:
            user.order_id = self.get_next_order_id()
        else:
            user.order_id = -1
        return user
        
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

    def init_s3(self):
        if not self.mode == 'PROD':
            return
        self.access_key = os.getenv('CLOUDCUBE_ACCESS_KEY_ID')
        self.secret_key = os.getenv('CLOUDCUBE_SECRET_ACCESS_KEY')
        self.url = os.getenv('CLOUDCUBE_URL')
        self.cube_name = self.url.split('/')[-1]
        self.bucket_name = self.url.split('https://')[-1].split('.')[0]
        self.s3 = boto3.client('s3', aws_access_key_id=self.access_key, aws_secret_access_key=self.secret_key)

    def load_match_info(self):
        """
        loads match date and participants
        """
        self.match_info = os.path.join(os.path.split(__file__)[0], 'match_info.txt')

        if self.mode == 'PROD':
            self.match_info_s3 = os.path.join(self.cube_name, 'match_info.txt')
            try:
                self.s3.download_file(self.bucket_name, self.match_info_s3, self.match_info)
            except Exception as e:
                print(f'Failed to get the match info file: {str(e)}')
                return

        if self.match_info and os.path.exists(self.match_info):
            with open(self.match_info, 'r') as f:
                content = json.load(f)
            if content:
                self.init_dates(date = content['date'], center_index = content['center_index'])
                self.cur_players = content['cur_players'][:]

    def load_user_rates(self):
        """
        Load user rates if the file is available
        """
        self.user_rates = os.path.join(os.path.split(__file__)[0], 'user_rates.json')

        if self.mode == 'PROD':
            self.user_rates_s3 = os.path.join(self.cube_name, 'user_rates.json')
            try:
                self.s3.download_file(self.bucket_name, self.user_rates_s3, self.user_rates)
            except Exception as e:
                print(f'Failed to get the user rates file: {str(e)}')
                return

        with open(self.user_rates, 'r') as f:
            content = json.load(f)

        self.players_info = content['subscribed']
        self.foreign_players_rates = content['unsubscribed']

    def save_match_info(self):
        """
        saves match date and participants
        """
        content = {}
        content['date'] = datetime.datetime.strftime(self.next_date, '%d/%m/%Y %H:%M')
        content['center_index'] = self.next_center_index
        content['cur_players'] = []
        for user in sorted(self.all_players, key = lambda x:x.order_id):
            if user.order_id<0:
                continue
            content['cur_players'].append(user.id if user.id>0 else user.user_name)
            
        with open(self.match_info, 'w') as f:
            f.write(json.dumps(content))
             
        if not self.mode == 'PROD':
            return

        try:
            self.s3.upload_file(self.match_info, self.bucket_name, self.match_info_s3)
        except Exception as e:
            print(f'Failed to upload the match info file: {str(e)}')
            return

    @WithLogError
    def show_add_forbidden_player_keyboard(self, update, context):
        """
        ADMIN ONLY: Shows a keyboard to select forbidden player from the next session
        """
        if self.is_admin(context.bot, update):
            players = [user.user_name for user in self.all_players if not user.is_forbidden]
            reply_markup = InlineKeyboardMarkup(create_player_keyboard(players))
            update.message.reply_text(Msg.select_forbidden_player, reply_markup=reply_markup)

    @WithLogError
    def show_del_forbidden_player_keyboard(self, update, context):
        """
        ADMIN ONLY: Shows a keyboard to delete a forbidden player from the next session
        """
        if self.is_admin(context.bot, update):
            forbidden_players = [user.user_name for user in self.all_players if user.is_forbidden]
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
        if query.data == MotFr.cancel:
            bot.edit_message_text(text=Msg.operation_cancelled, message_id=query.message.message_id, chat_id=query.message.chat_id)
            return

        user = FootUser.get_foot_user(self.all_players, user_name=query.data)
        user.is_forbidden = True
        user.order_id = -1

        msg = '{}\n{}'.format(Msg.forbidden_player, ', '.join([user.user_name for user in self.all_players if user.is_forbidden]))
        bot.edit_message_text(text=msg, message_id=query.message.message_id, chat_id=query.message.chat_id)
        bot.send_message(chat_id=query.message.chat_id, text=self.get_program_and_players(), parse_mode='HTML')

    def on_btn_del_forbidden_player(self, bot, update):
        """
        Delete forbidden player from the next session
        """
        query = update.callback_query
        if query.data == MotFr.cancel:
            bot.edit_message_text(text=Msg.operation_cancelled, message_id=query.message.message_id, chat_id=query.message.chat_id)
            return
    
        user = FootUser.get_foot_user(self.all_players, user_name=query.data)
        user.is_forbidden = False
        
        forbidden_players = [user.user_name for user in self.all_players if user.is_forbidden]
        msg = '{}\n{}'.format(Msg.forbidden_player, ', '.join(forbidden_players)) if forbidden_players else Msg.no_forbidden_player
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
        update.message.reply_text('{}, {}'.format(cur_user.user_name, Msg.teamkeshi_welcome), reply_markup=reply_markup)

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
        if query.data in [MotFr.cancel, MotFr.no]:
            bot.edit_message_text(text=Msg.operation_cancelled, message_id=query.message.message_id, chat_id=query.message.chat_id)
            self.reset_teams()
            return

        cur_user = self.get_user_from_update(update)
        if query.data == MotFr.yes:
            if self.team_keshi.is_finish():
                self.team_keshi.set_validation(self.team_keshi.whose_turn())
                if self.team_keshi.is_both_validated():
                    self.bot.send_message(self.chat_ids['Teste team keshi'], self.team_keshi.print_teams(False, True))
                    final_teams = self.team_keshi.print_teams(True, False)
                    msg = '{}\n{}'.format(Msg.validation_finish, final_teams)
                    bot.edit_message_text(text=msg, chat_id=query.message.chat_id, message_id=query.message.message_id)
                    captain1, captain2 = list(self.team_keshi.teams.keys())[0].user_name, list(self.team_keshi.teams.keys())[1].user_name
                    self.bot.send_message(self.chat_ids['Foot Admin'], Msg.validation_finish2.format(captain1, captain2))##
                    #self.bot.send_message(self.chat_ids['Teste team keshi'], Msg.validation_finish2.format(captain1, captain2))##
                    msg = '{}{}'.format(self.get_next_program(), final_teams)
                    self.bot.send_message(self.chat_ids['Foot Admin'], msg, parse_mode='HTML')##
                    #self.bot.send_message(self.chat_ids['Teste team keshi'], msg, parse_mode='HTML')##
                    self.reset_teams()
                    return
            else:
                #cur_user = FootUser.get_foot_user(self.all_players, user_id=240732760) ##
                if cur_user.id == list(self.team_keshi.teams.keys())[0].id:
                    msg = '{} {}\n'.format(cur_user.user_name, Msg.restart_timkeshi)
                    msg += '{}, {}'.format(cur_user.user_name, Msg.teamkeshi_welcome)
                    update.effective_message.reply_text(msg)
                    return
                self.team_keshi.add_captain(cur_user) # Add 2nd captain
        else:
            #cur_user = self.team_keshi.whose_turn() ##
            if cur_user.id == self.team_keshi.whose_turn().id:
                self.team_keshi.add_player(cur_user, FootUser.get_foot_user(self.all_players, user_name=query.data.split(':')[0]))

        self.on_show_timkeshi_buttons(bot, update)
    
    def get_next_date(self, update, context):
        """
        Returns next date in 45 days if it is a football day (Monday, Tuesday, Wednesday)
        """
        if self.is_admin(context.bot, update):
            tz = pytz.timezone('Europe/Paris')
            today = datetime.now(tz)
            days = {0:'Monday', 1:'Tuesday', 2:'Wednesday', 3:'Thursday', 4:'Friday', 5:'Saturday', 6:'Sunday'}
            next_date = today + timedelta(days=45)
            weekday = next_date.weekday()
            #if weekday in (0, 1, 2): # Monday, Tuesday, Wednesday
            bot.edit_message_text(text=Msg.next_potential_date.format(days[weekday]), message_id=query.message.message_id, chat_id=query.message.chat_id)


def main():
    try:
        app = Foot4Ever()
    except Exception as e:
        str(e)
        raise e

if __name__ == '__main__':
    main()
