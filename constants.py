import os
from collections import OrderedDict


ADMIN_CHAT_ID = int(os.environ['ADMIN_CHAT_ID'])
MAIN_CHAT_ID = int(os.environ['MAIN_CHAT_ID'])
URBAN_CITY = os.environ['URBAN_CITY']
PASHA_USER_ID = int(os.environ.get('PASHA_USER_ID'))
SAM_USER_ID = int(os.environ.get('SAM_USER_ID'))
MATCH_INFO_FILE = f'match_info_{URBAN_CITY}.txt'
USER_RATES_FILE = f'user_rates_{URBAN_CITY}.json'


public_cmds = OrderedDict([('add', "S'inscrire dans le prochain match"),
                           ('del', "Annuler l'inscription"),
                           ('prog', "Afficher le prochain programme du jeu"),
                           ('players', "Afficher les joueurs du prochain jeu"),
                           ('arrange', "Arranger les équipes")])
admin_cmds = OrderedDict([('add', "S'inscrire dans le prochain match"),
                          ('del', "Annuler l'inscription"),
                          ('add_susp', "Susprendre un joueur"),
                          ('del_susp', "Annuler la suspension d'un joueur"),
                          ('set_prog', "Mettre le prochain jeu"),
                          ('set_admins', 'Set group admins'),
                          ('all', "Afficher tous les noms"),
                          ('next', 'Afficher le jour dans 45 jours')])


class Msg():  # pylint:disable=too-few-public-methods
    """
    UI messages
    """
    wrong_page_add_del = "Pour s'inscrire ou annuler l'inscription, allez d'abord sur la page du groupe."
    wrong_place_timkeshi = "Pour arranger les équipes, créez d'abord un groupe, invitez ensuite l'autre capitaine."
    you_are_forbidden = "Oops! Tu es suspendu pour le prochain jeu!"
    too_late_del = "L'inscription ne peut pas être annulée dans les dernières 48h! Tu contactes les admins stp."
    restart_timkeshi = "Je ne parlais pas à toi, je parlais au deuxième capitaine"
    missing_permission = "Tu n'es pas autorisé à utiliser cette commande! Désolé!"
    add_hint = "Pour t'inscrire', tu écris juste /add (sans ton prénom)."
    select_player = "c'est à toi de choisir (le score est de 1 à 5 dans cet ordre: goal, défense, attaque, course)"
    teamkeshi_welcome = "je te remercie d'avoir commancé l'arrangement des équipes. Le deuxième capitaine, quelle couleur choisis-tu?"
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
    change_succeeded = "Le changement suivant a effectué avec du succès:"
    sign_up_not_started = "La date du prochain jeu n'est pas encore définie! Un peu de patience mon gars."
    next_potential_date = '45 days later will be {} {}'
    sign_up_not_authorized = "Stp mets d'abord un prénom et/ou nom sur ton profile Telegram puis réessaie."
    admins_added = 'Les admins suivant ont été settés: {}'
    reserve_will_play = '@{}: Tu vas remplacer {}, tu peux confirmer avoir lu ce message?'
    name_already_added = "Je sais que tu es chaud mais ton nom est déjà dans la liste!"


# The description to set in bot father
# pylint:disable=pointless-string-statement
"""
add - s'inscrire dans le prochain jeu
del - annuler l'inscription
prog - afficher la date du prochain jeu
players - afficher les joueurs du prochain jeu
arrange - faire des équipe
help - aide
help_admins - aide admins
"""


class MotFr():  # pylint:disable=too-few-public-methods,disallowed-name,invalid-name
    """
    Frech words
    """
    monday = 'Lundi'
    tuesday = 'Mardi'
    wednesday = 'Mercredi'
    thursday = 'Jeudi'
    friday = 'Vendredi'
    saturday = 'Samedi'
    sunday = 'Dimanche'

    cancel = 'Annuler'
    yes = 'Oui'
    no = 'Non'
    jan = 'cher, '
    team = 'Equipe'
    white = 'blanche'
    red = 'rouge'


day_names = {0: MotFr.monday, 1: MotFr.tuesday, 2: MotFr.wednesday, 3: MotFr.thursday, 4: MotFr.friday, 5: MotFr.saturday, 6: MotFr.sunday}
