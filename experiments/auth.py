from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language

from experiments.constants import Constants
from .models import Session, Player, RunNow, Experiment


def authenticate(request, session_id, username="", password=""):
    # Check if experiment on
    run_now = RunNow.objects.all()[:1].get()
    if not run_now.experiment_on:
        raise Http404

    # Check if the experiments session is correct
    exp_session = get_object_or_404(Session, pk=session_id)

    return exp_session


def login(request, user):
    # Check if session exists
    if not request.session.exists(request.session.session_key):
        request.session.create()

    # Check if participant with session key
    try:
        player = Player.objects.get(sess_key=request.session.session_key)
    except (KeyError, Player.DoesNotExist):
        # Create new entry in Participant table
        player = Player(experiment=user.experiment, session=user.session,
                        sess_key=request.session.session_key)
        player.save()

    # Create a session entry for the participant
    request.session['user_id'] = player.id
    request.session['reg_user_id'] = player.id
    request.session['experiment_state'] = 'login'
    # Indicate that registered user participated


def logout(request, user):
    pass


class ExperimentsBackend(ModelBackend):
    """
    Checks that User is authorized on the experiment, treatment and session.
    Checks that the experiment is active.
    Checks that the User has not already finished the experiment (users can
    only participate on the experiment once)
    Checks the state of the participant on the experiment and sets the variable
    next to that state.
    """

    def authenticate(self, request=None, username=None, password=None, dummy=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):

                # If admin or staff, check with custom ModelBackend
                if user.is_superuser or user.is_staff:
                    return None

                # second get run_now object
                run_now = RunNow.objects.all()[:1].get()

                experiment = Experiment.objects.get(pk=run_now.experiment_id)
                exp_session = Session.objects.get(pk=run_now.session_id)
                # Check if user is registered for the current experiment and session
                if (user.player.experiment != experiment) or (user.player.session != exp_session) \
                        or (user.player.session.treatment != exp_session.treatment) \
                        or (not run_now.experiment_on):
                    raise PermissionDenied

                # Check if user has a player associated
                try:
                    player = Player.objects.get(user=user, experiment=experiment, session=exp_session)
                    if player.profile.finished or (player.profile.experiment_state == Constants.STATE_FINISH) or (
                                player.group is None):
                        raise PermissionDenied
                except (KeyError, Player.DoesNotExist):
                    # Create new entry in Participant table
                    player = Player(user=user, experiment=experiment, session=exp_session)
                    player.save()

                # Setup experiment state if participant is new to the experiment
                if not player.profile.participated:
                    player.profile.experiment_state = Constants.STATE_LOGIN
                    player.profile.language = get_language()
                    player.profile.save()
                    # Create a session entry for the participant
                    request.session['experiment_state'] = Constants.STATE_LOGIN
                    request.session.save()

                return user
