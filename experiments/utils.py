import csv
import json

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse

from .constants import Constants
from .models import (RunNow, Player, GameData, Experiment, Session, RequestMonitor,
                     Profile, Game, Treatment, CollectiveRiskGame, Group)


class RunLoader(object):
    """
    Class that allow to create another run with the specifications from a python dictionary
    """

    def __init__(self, run_content_path):
        with open(run_content_path) as json_data:
            self.run = json.load(json_data)

    def load(self):
        experiment = Experiment.objects.get(experiment_name=self.run['experiment_name'])
        treatment = Treatment.objects.get(experiment=experiment,
                                          treatment_name=self.run['treatment_name'])
        session = Session.objects.get(experiment=experiment, treatment=treatment,
                                      session_number=self.run['session_number'])
        new_run = RunNow(experiment_id=experiment.id,
                         session_id=session.id,
                         treatment_id=treatment.id,
                         experiment_on=self.run['experiment_on'])
        new_run.save()


class GamesLoader(object):
    """
    Helper class to load games into DB from json files
    """

    def __init__(self, game_content_path):
        with open(game_content_path) as json_data:
            self.games = json.load(json_data)

    def load(self):
        from importlib import import_module
        for game_name, game in self.games.items():
            new_game = getattr(import_module("experiments.models"), game['type'])(**game['params'])
            new_game.save()


class ExperimentsLoader(object):
    """
    Helper class to load experiments into DB from json files
    """

    def __init__(self, experiments_content_path):
        with open(experiments_content_path) as json_data:
            self.experiments = json.load(json_data)

    def load(self):
        for key1, experiment in self.experiments.items():
            # add experiment to DB
            new_experiment = Experiment(experiment_name=experiment['experiment_name'],
                                        experiment_metadata=experiment['experiment_metadata'])
            new_experiment.save()
            # Create treatments
            for key2, treatment in experiment['treatments'].items():
                # Get index to experiment's game
                game = Game.objects.get(game_uid=treatment['game_uid'])
                # Create treatment
                new_treatment = Treatment(experiment=new_experiment, game=game,
                                          treatment_name=treatment['treatment_name'],
                                          treatment_metadata=treatment['treatment_metadata'])
                new_treatment.save()
                # Create sessions
                for key3, session in treatment['sessions'].items():
                    new_session = Session(experiment=new_experiment, treatment=new_treatment,
                                          session_number=session['session_number'],
                                          session_metadata=session['session_metadata'],
                                          scheduled_date=session['scheduled_date'],
                                          group_size=session['group_size'])
                    new_session.save()


# class ParticipantsLoader(object):
#     """
#     Class that provides methods to load participants from json files into the database
#     """
#
#     def __init__(self, participants_content_path):
#         with open(participants_content_path) as json_data:
#             self.participants = json.load(json_data)
#
#     def load(self):
#         for index in self.participants:
#             experiment = Experiment.objects.get(experiment_name=self.participants[index]['experiment_name'])
#             treatment = Treatment.objects.get(experiment=experiment,
#                                               treatment_name=self.participants[index]['treatment_name'])
#             session = Session.objects.get(experiment=experiment, treatment=treatment,
#                                           session_number=self.participants[index]['session_number'])
#             new_participant = RegisteredParticipant(experiment=experiment,
#                                                     session=session,
#                                                     first_name=self.participants[index]['first_name'],
#                                                     family_name=self.participants[index]['family_name'],
#                                                     id_num=self.participants[index]['id_num'],
#                                                     password=self.participants[index]['password']
#                                                     )
#             new_participant.save()


def erase_game_data():
    Player.objects.all().delete()
    GameData.objects.all().delete()


def init_monitor():
    RequestMonitor.objects.all().update(var=0, condition=False)
    RequestMonitor.queue.through.objects.all().delete()


def create_monitor(name, group):
    monitor = RequestMonitor(name="".join([name, "g", group]), var=0, condition=False, group=group)
    monitor.save()


def delete_monitors(group):
    RequestMonitor.objects.all().filter(group=group).delete()


def delete_monitor(group, name):
    RequestMonitor.objects.all().filter(group=group, name=name).delete()


def init_experiment():
    # get experiment from run now
    run_now = RunNow.objects.all()[:1].get()

    # now retrieve experiment, treatment and session
    experiment = Experiment.objects.get(pk=run_now.experiment_id)
    treatment = Treatment.objects.get(pk=run_now.treatment_id)
    session = Session.objects.get(pk=run_now.session_id)
    game = CollectiveRiskGame.objects.get(id=treatment.game.id)

    # If session finished don't ever modify it
    if session.finished:
        return False

    # initialize players
    Player.objects.filter(experiment=experiment, session=session).update(group=None)

    Profile.objects.filter(player__experiment=experiment,
                           player__session=session, player__user__is_active=True).update(
        private_account=game.endowment,
        last_round=0,
        finished=False,
        participated=False,
        experiment_state=Constants.STATE_INACTIVE,
        transition_state=Constants.STATE_NO_TRANSITION,
        threshold_state=None,
        group_number=None,
        time_start_experiment=None,
    )

    # assign groups to players
    assign_groups2players(experiment_id=experiment.id, session_id=session.id)

    # initialize monitors
    RequestMonitor.objects.filter(group__session=session).update(var=0, condition=False)
    monitors = RequestMonitor.objects.filter(group__session=session)
    for monitor in monitors:
        monitor.queue.clear()

        # initialize groups
        Group.objects.filter(session=session).update(finishing_round=0,
                                                     game_finished=False,
                                                     public_account=0,
                                                     current_round=0,
                                                     random_value=0,
                                                     random_value_generated=False,
                                                     dice_results="0.0",
                                                     finishing_round_selected=False)

    # Finally activate session through runnow
    run_now.experiment_on = True
    run_now.save()


def init_experiment_without_setting_group():
    # get experiment from run now
    run_now = RunNow.objects.all()[:1].get()

    # now retrieve experiment, treatment and session
    experiment = Experiment.objects.get(pk=run_now.experiment_id)
    treatment = Treatment.objects.get(pk=run_now.treatment_id)
    session = Session.objects.get(pk=run_now.session_id)
    game = CollectiveRiskGame.objects.get(id=treatment.game.id)

    # If session finished don't ever modify it
    if session.finished:
        return False

    # initialize players
    Profile.objects.filter(player__experiment=experiment, player__session=session, player__user__is_active=True).update(
        private_account=game.endowment, last_round=0, finished=False,
        participated=False, experiment_state=Constants.STATE_INACTIVE, transition_state=Constants.STATE_NO_TRANSITION)

    # initialize monitors
    RequestMonitor.objects.filter(group__session=session).update(var=0, condition=False)
    monitors = RequestMonitor.objects.filter(group__session=session)
    for monitor in monitors:
        monitor.queue.clear()

    # initialize groups
    Group.objects.filter(session=session).update(finishing_round=0,
                                                 game_finished=False,
                                                 public_account=0,
                                                 current_round=0,
                                                 random_value=0,
                                                 random_value_generated=False,
                                                 dice_results="0.0",
                                                 finishing_round_selected=False)

    # Finally activate session through runnow
    run_now.experiment_on = True
    run_now.save()


def init_session(session=None):
    if session is not None:
        pass
    else:
        run_now = RunNow.objects.all()[:1].get()
        session_id = run_now.session_id

    # now retrieve experiment, treatment and session
    Session.objects.filter(pk=session_id).update(finished=False, structure_assigned=False)
    session = Session.objects.get(pk=session_id)
    Group.objects.filter(session=session).update(finishing_round=0, game_finished=False, public_account=0,
                                                 current_round=0, random_value=0, random_value_generated=False)


def erase_game_data_session(session=None):
    if session is not None:
        pass
    else:
        run_now = RunNow.objects.all()[:1].get()
        session_id = run_now.session_id

    # If session finished, don't ever modify it!
    if Session.objects.get(pk=session_id).finished:
        return False

    # now retrieve experiment, treatment and session
    GameData.objects.filter(session=session_id).delete()


@transaction.atomic
def assign_groups2players(experiment_id, session_id, game_type=Constants.COLLECTIVE_RISK):
    """Randomly assign groups of group_size to players"""

    # First check how many players are assigned to the session
    experiment = Experiment.objects.get(id=experiment_id)
    session = Session.objects.get(id=session_id)

    # If session finished, don't ever modify it!
    if session.finished:
        return False

    if session.structure_assigned:
        return None

    players = Player.objects.filter(experiment=experiment, session=session, user__is_active=True).order_by('?')

    # Now get the game
    if game_type is Constants.COLLECTIVE_RISK:
        game = CollectiveRiskGame.objects.get(id=session.treatment.game.id)
    else:
        game = Game.objects.get(id=session.treatment.game.id)

    num_rounds = game.rounds
    if game.is_round_variable:
        num_rounds = game.min_round + 30

    nb_players = players.count()
    group_size = session.group_size if session.group_size > 0 else game.group_size
    # Perhaps request permission of the admin in case the numbers are not divisible
    nb_groups = nb_players // group_size
    print(nb_groups, group_size, nb_players)

    # Create groups
    groups = []
    for i in range(nb_groups):
        group = Group.objects.get_or_create(group_number=i, session=session)[0]
        groups.append(group)
        # Create monitors
        for r in range(num_rounds + 1):
            RequestMonitor.objects.get_or_create(name="monitorS2r{}".format(r), group=group)
            RequestMonitor.objects.get_or_create(name="monitorS3r{}".format(r), group=group)
        RequestMonitor.objects.get_or_create(name="monitorS4", group=group)

    # Now randomly assign players to groups
    for i, player in enumerate(players):
        group = groups[i // group_size]
        player.profile.group_number = group.group_number
        player.group = group
        player.save()

    session.structure_assigned = True
    session.save()

    return nb_groups, nb_players


def remove_from_group(player, group):
    # If session finished, don't ever modify it!
    if player.session.finished:
        return False

    player.group = None
    player.save()


def move_player_to_group(player, group):
    # If session finished, don't ever modify it!
    if player.session.finished:
        return False

    player.group = group
    player.save()


def setup_experiment():
    # Create an experiment

    # Create treatments

    # Create sessions

    # Create CRD Game

    # Set group size

    # Create RunNow entry

    # Create RegisteredParticipants

    # Up to here, load all this configuration from a json file/files

    # Login participants

    # Assign groups

    pass


def set_run_now(experiment, session, treatment, experiment_on=True):
    RunNow.objects.get_or_create(experiment_id=experiment,
                                 session_id=session,
                                 treatment_id=treatment,
                                 experiment_on=experiment_on)


def correct_group_monitors_if_player_fails(player_id):
    player = Player.objects.get(pk=player_id)
    # check which state of the game are they stuck in
    try:
        monitor = player.monitors.all()[0]
    except IndexError:
        raise IndexError("[ERROR] Player is not in a queue!")
    else:
        if player.monitors.all().count() > 1:
            raise Exception("[WARNING] Player is in more than one queue!")

            # Check the conditions of the monitor


def add_users(users, experiment, session, treatment):
    from django.contrib.auth.models import User

    # If session finished, don't ever modify it!
    if session.finished:
        return False

    game = CollectiveRiskGame.objects.get(id=treatment.game.id)

    for key, user in users.items():
        user = User.objects.create_user(username=user['username'], password=user['password'])
        user.player.experiment = experiment
        user.player.session = session
        user.player.profile.private_account = game.endowment
        user.is_active = True
        user.save()
        user.player.save()


def make_player_inactive(username):
    from django.contrib.auth.models import User
    user = User.objects.get(username=username)
    user.is_active = False
    user.save()


def make_player_active(username):
    from django.contrib.auth.models import User
    user = User.objects.get(username=username)
    user.is_active = True
    user.save()


def change_player_group(username, group):
    from django.contrib.auth.models import User
    user = User.objects.get(username=username)

    # If session finished, don't ever modify it!
    if user.player.session.finished:
        return False

    Player.objects.filter(user=user).update(group=group)


def export_as_csv(description="Download selected rows as CSV file", header=True):
    """
    This function returns an export csv action
    This function ONLY downloads the columns shown in the list_display of the admin
    'header' is whether or not to output the column names as the first row
    """

    def export_as_csv(modeladmin, request, queryset):
        """
        Generic csv export admin action.
        based on http://djangosnippets.org/snippets/1697/ and /2020/
        """
        if not request.user.is_staff:
            raise PermissionDenied
        opts = queryset.model._meta

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % str(opts).replace('.', '_')

        writer = csv.writer(response)
        field_names = [field.name for field in opts.fields]
        # Write a first row with header information
        if header:
            writer.writerow(field_names)
        # Write data rows
        for obj in queryset:
            writer.writerow([getattr(obj, field, None) for field in field_names])
        return response

    export_as_csv.short_description = description
    return export_as_csv


def gen_participant_json(passwords, expression, randomize=True):
    """
    Function to create new users and store them in a json file
    
    :param passwords: list with passwords
    :param expression: string that contain the fixed part of the username
    :param randomize: indicates whether the passwords should be assigned randomly
    :return: 
    """
    from random import shuffle
    # First create a dict
    users = {}
    if randomize:
        shuffle(passwords)
    for i, pss in enumerate(passwords, 1):
        users["{}".format(i)] = {"username": "{0}{1}".format(expression, i), "password": pss}
    return users


def user_dict2txt(user_dict, file):
    for i in range(1, len(user_dict) + 1):
        file.write("username: {}\n".format(user_dict["{}".format(i)]["username"]))
        file.write("password: {}\n".format(user_dict["{}".format(i)]["password"]))
        file.write("\n")


def add_users2session(password_path: str, save_path: str, session: Session, expression: str, randomize: bool = True):
    """
    Adds users to the :session with the passwords from :password_path (as many users as passwords).
    Stores the users information in a .txt and .json files on :save_path.
    :param password_path: path to a .txt file containing the passwords to be used (one per line)
    :param save_path: path where the users info should be saved
    :param session: session where the users are added to
    :param expression: common pattern for the users names
    :param randomize: indicates if the password assignment should be randomized
    :return: None or Exception
    """

    # If session finished, don't ever modify it!
    if session.finished:
        return False

    try:
        with open(password_path) as pss_file:
            pss = pss_file.read().splitlines()
    except TypeError as te:
        return te
    except Exception as e:
        return e
    else:
        # generate users as a dict
        users = gen_participant_json(pss, expression, randomize)

    save_file = "{save_path}exp{experiment_id}t{treatment_id}sess{session_name}_{session_date}".format(
        save_path=save_path,
        experiment_id=session.experiment.id,
        treatment_id=session.treatment.id,
        session_name=session.session_number,
        session_date=session.scheduled_date.strftime(
            "%d%m%y"))
    # generate txt file
    try:
        with open("{}.txt".format(save_file), "w") as txt_file:
            user_dict2txt(users, txt_file)
    except TypeError as te:
        return te
    except Exception as e:
        return e

    # generate json file

    try:
        with open("{}.json".format(save_file), "w") as json_file:
            json.dump(users, json_file)
    except TypeError as te:
        return te
    except Exception as e:
        return e

    # add users to session
    experiment = session.experiment
    treatment = session.treatment
    add_users(users, experiment, session, treatment)


def calculate_final_round(p, min_round, dice_faces=6):
    import numpy as np
    dice_results = np.random.rand(100)
    check_condition = dice_results <= p
    rounds_add = np.where(check_condition == 1)[0][0]
    final_round = min_round + rounds_add
    return final_round, np.array(np.ceil(dice_results[:rounds_add + 1] * dice_faces), dtype=np.int32)
