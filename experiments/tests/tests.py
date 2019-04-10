from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

import experiments.utils as utils
from experiments.models import RequestMonitor, Player, Experiment, Treatment, Session
from experiments.views import login_view, game_view, finish_round_view


# Create your tests here.
class RegisteredParticipantModel(TestCase):
    pass


class PlayerModelTests(TestCase):
    pass


class RequestMonitorModelTests(TestCase):
    def test_var_updates_correctly(self):
        pass

    def test_check_condition(self):
        pass

    def test_wait(self):
        pass

    def test_signal(self):
        pass


def add_session_to_request(request):
    """Annotate a request object with a session"""
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()


class LogInViewTests(TestCase):
    def test_login_participant(self):
        pass

    def test_not_participant_cant_login(self):
        pass

    def test_participant_cant_be_loggedin_twice(self):
        pass

    def test_restrict_participant_login_ip(self):
        pass

    def test_player_logged_in(self):
        pass

    def test_player_state(self):
        pass


class GameViewTests(TestCase):
    def setUp(self):
        # set up DB state
        game_loader = utils.GamesLoader(
            './experiments/db_data/games.json')
        game_loader.load()
        experiment_loader = utils.ExperimentsLoader(
            './experiments/db_data/experiments.json')
        experiment_loader.load()
        participants_loader = utils.ParticipantsLoader(
            './experiments/db_data/participants.json')
        participants_loader.load()
        run_now_loader = utils.RunLoader(
            './experiments/db_data/runnow.json')
        run_now_loader.load()

        # print(RegisteredParticipant.objects.all().values_list('password', flat=True))

        # Every test needs access to the request factory
        self.factory = RequestFactory()
        # We set the session id first
        self.experiment = Experiment.objects.get(experiment_name="Collective-Risk Experiment")
        self.treatment = Treatment.objects.get(experiment=self.experiment,
                                               treatment_name="Treatment 1")
        self.session = Session.objects.get(experiment=self.experiment, treatment=self.treatment,
                                           session_number=1)
        self.login_reverse = reverse('experiments:login', kwargs={'session_id': self.session.id})
        self.requests = {}

    def test_participants_sync(self):
        """
        Participants at game_view (state S2)
        Participants should be redirected to wait after their move, until all members of the group
        have finished. Then, they should be redirected to the results_view (S3).
        """
        # First we initialize the experiment
        utils.init_experiment()
        # Then we setup the participants
        passwords = ['testa', 'testb', 'testc', 'testd']

        for psswd in passwords:
            request = self.factory.post(self.login_reverse, {'password': psswd})
            add_session_to_request(request)
            login_view(request, session_id=self.session.id)
            self.requests[request.session['user_id']] = request

        # Now we assign groups
        num_groups = utils.assign_groups2players(self.experiment.id, self.session.id)
        # Let's get a pointer to the players on db
        players = Player.objects.all()
        # Create monitors for each group of players
        for i in range(num_groups):
            monitor1 = RequestMonitor(name="monitorS2g{}".format(i + 1), group=(i + 1))
            monitor2 = RequestMonitor(name="monitorS3g{}".format(i + 1), group=(i + 1))
            monitor1.save()
            monitor2.save()

        # Call game_view
        # # Create the request
        for player in players:
            request = self.factory.get(reverse('experiments:game', kwargs={'session_id': self.session.id}))
            add_session_to_request(request)
            request.session = self.requests[player.id].session
            # get to the game
            game_view(request, session_id=self.session.id)
            # make the action to be redirected to wait
            request = self.factory.post(reverse('experiments:game', kwargs={'session_id': self.session.id}),
                                        {'action': 2, 'time_round_start': timezone.now().isoformat(),
                                         'time_round_end': timezone.now().isoformat(),
                                         'time_elapsed': timezone.now().time().isoformat()
                                         })
            add_session_to_request(request)
            request.session = self.requests[player.id].session
            response = finish_round_view(request, session_id=self.session.id)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, text="<p>Wait until all members of the group have made their choice.</p>",
                                status_code=200)


class ResultsViewTests(TestCase):
    def setUp(self):
        # Every test needs access to the request factory
        self.factory = RequestFactory()
        # We set the session id first
        self.experiment_id = 1
        self.session_id = 1
        self.login_reverse = reverse('experiments:login', kwargs={'session_id': self.session_id})

        # generate participants
        passwords = ["testa", "testb", "testc"]

        for psswd in passwords:
            request = self.factory.post(self.login_reverse, {'password': psswd})
            add_session_to_request(request)
            login_view(request, session_id=self.session_id)

    def test_participants_sync(self):
        """
        Participants at results_view (state S3). If the game is finished (last round) they should be redirected to the
        survey when they press continue. Else, they should be redirected to WAIT until all members of the group
        have finished. Then, they should be redirected to the game_view (S2).
        """
        # First we initialize the experiment
        utils.init_experiment()
        # Then we setup the participants
        self.setUp()
