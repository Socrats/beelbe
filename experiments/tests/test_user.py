import json

import numpy as np
import time
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import connections
from django.db.models import Count, Q
from django.test import Client
from django.test import TestCase, RequestFactory, TransactionTestCase
from django.urls import reverse_lazy
from django.utils import timezone

import experiments.utils as utils
from experiments.constants import Constants
from experiments.decorators import test_concurrently_users
from experiments.models import (Experiment, Treatment, Session, CollectiveRiskGame,
                                RunNow, Group, RequestMonitor)


# Create your tests here.

def close_db_connections(func, *args, **kwargs):
    """
    Decorator to close db connections during threaded execution

    Note this is necessary to work around:
    https://code.djangoproject.com/ticket/22420
    """

    def _inner(*args, **kwargs):
        func(*args, **kwargs)
        for conn in connections.all():
            conn.close()

    return _inner


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


class GameViewTests(TransactionTestCase):
    num_users = 36

    @classmethod
    def setUpClass(cls):
        super(GameViewTests, cls).setUpClass()
        # set up DB state
        game_loader = utils.GamesLoader(
            '/Users/eliasfernandez/PycharmProjects/BEELPlatform/experiments/db_data/games.json')
        game_loader.load()
        experiment_loader = utils.ExperimentsLoader(
            '/Users/eliasfernandez/PycharmProjects/BEELPlatform/experiments/db_data/experiments.json')
        experiment_loader.load()
        run_now_loader = utils.RunLoader(
            '/Users/eliasfernandez/PycharmProjects/BEELPlatform/experiments/db_data/runnow.json')
        run_now_loader.load()

        # Every test needs access to the request factory
        cls.factory = RequestFactory()
        run_now = RunNow.objects.all()[:1].get()
        run_now.experiment_on = True
        run_now.save()
        # We set the session id first
        cls.experiment = Experiment.objects.get(pk=run_now.experiment_id)
        cls.treatment = Treatment.objects.get(experiment=cls.experiment,
                                              pk=run_now.treatment_id)
        cls.session = Session.objects.get(experiment=cls.experiment, treatment=cls.treatment,
                                          pk=run_now.session_id)
        cls.game = CollectiveRiskGame.objects.get(id=cls.session.treatment.game.id)

        # Create Users and clients
        UserModel = get_user_model()

        for i in range(cls.num_users):
            user = UserModel.objects.create_user('user{}'.format(i), '', 'pass{}'.format(i))
            user.player.experiment = cls.experiment
            user.player.session = cls.session
            user.player.profile.private_account = cls.game.endowment
            user.is_active = True
            user.save()
            user.player.save()

        # Initialize experiment
        utils.init_experiment()

    def test_participants_sync(self):
        """
        Participants at game_view (state S2)
        Participants should be redirected to wait after their move, until all members of the group
        have finished. Then, they should be redirected to the results_view (S3).
        """
        login_url = '/en/experiments/login/'
        session_id = self.session.id

        @test_concurrently_users(self.num_users)
        @close_db_connections
        def toggle_registration(user_number=None):
            """ perform the code you want to test here; it must be thread-safe
               (e.g., each thread must have its own Django test client)
            """

            def test_ajax_wait(condition):
                while not condition:
                    time.sleep(10 * np.random.rand())
                    r = c.post(reverse_lazy('experiments:sync', kwargs={'session_id': session_id}))
                    json_str = r.content.decode('utf8').replace("'", '"')
                    json_data = json.loads(json_str)
                    condition = json_data['can_continue']
                return condition

            if user_number is None:
                return

            UserModel = get_user_model()
            user = UserModel.objects.get(username='user{}'.format(user_number))
            c = Client(user=user)

            # First we check the login
            response = c.post(login_url,
                              {'username': 'user{}'.format(user_number), 'password': 'pass{}'.format(user_number)})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse_lazy('experiments:instructions'))
            self.assertTrue('experiment_state' in c.session.keys())

            # Then we move through the windows until game
            response = c.get(reverse_lazy('experiments:test', kwargs={'session_id': session_id}))
            self.assertEqual(response.status_code, 200)
            user.player.profile.experiment_state = Constants.STATE_TEST
            user.player.save()

            # Syncronize players before game
            response = c.get(reverse_lazy('experiments:results_round', kwargs={'session_id': session_id}))
            # player must be waiting
            self.assertContains(response, 'Wait for the rest of the members of the group.',
                                status_code=200)
            # next = response.context[-1]['next']
            # self.assertEqual(next, reverse_lazy("experiments:game", kwargs={'session_id': session_id}))
            can_continue = response.context['can_continue']
            if not can_continue:
                can_continue = test_ajax_wait(can_continue)
            self.assertEqual(can_continue, True)

            # The while is needed to take into account redirections due to db errors
            finished_game = False
            while not finished_game:
                move_next = False
                while not move_next:
                    # game starts
                    response = c.get(reverse_lazy('experiments:game', kwargs={'session_id': session_id}))

                    self.assertEqual(response.status_code, 200)
                    time_now = timezone.now()
                    elapsed = time_now - time_now
                    response = c.post(reverse_lazy('experiments:game_round', kwargs={'session_id': session_id}),
                                      {'time_round_start': time_now, 'time_round_end': time_now,
                                       'time_elapsed': elapsed,
                                       'action': '4'})
                    if response.status_code == 200:
                        move_next = True

                # player must be waiting
                self.assertContains(response, 'Wait for the rest of the members of the group.',
                                    status_code=200)
                # check that the next parameter is correct
                # next = response.context[-1]['next']
                # self.assertEqual(next, reverse_lazy("experiments:results", kwargs={'session_id': session_id}))

                can_continue = response.context['can_continue']
                if not can_continue:
                    can_continue = test_ajax_wait(can_continue)
                self.assertEqual(can_continue, True)

                # The while is needed to take into account redirections due to db errors
                move_next = False
                while not move_next:
                    # Get results page
                    response = c.get(reverse_lazy('experiments:results', kwargs={'session_id': session_id}))

                    self.assertEqual(response.status_code, 200)
                    time_now = timezone.now()
                    elapsed = time_now - time_now
                    response = c.post(reverse_lazy('experiments:results_round', kwargs={'session_id': session_id}),
                                      {'time_round_start': time_now, 'time_round_end': time_now,
                                       'time_elapsed': elapsed,
                                       'prediction': '4'})
                    if response.status_code == 200:
                        move_next = True
                    elif response.status_code == 302:
                        if response.url == reverse_lazy("experiments:results_risk_wait",
                                                        kwargs={'session_id': session_id}):
                            move_next = True

                if response.status_code == 302:
                    self.assertRedirects(response, expected_url=reverse_lazy("experiments:results_risk_wait",
                                                                             kwargs={'session_id': session_id}))
                    break
                else:
                    # player must be waiting
                    self.assertContains(response, 'Wait for the rest of the members of the group.',
                                        status_code=200)
                    # next = response.context[-1]['next']
                    # self.assertEqual(next, reverse_lazy("experiments:game", kwargs={'session_id': session_id}))

                can_continue = response.context['can_continue']
                if not can_continue:
                    can_continue = test_ajax_wait(can_continue)
                self.assertEqual(can_continue, True)

            response = c.get(reverse_lazy("experiments:results_risk_wait", kwargs={'session_id': session_id}))
            self.assertContains(response, 'Wait for the rest of the members of the group.',
                                status_code=200)
            can_continue = response.context['can_continue']
            if not can_continue:
                can_continue = test_ajax_wait(can_continue)
            self.assertEqual(can_continue, True)

            # check that risk page works
            response = c.post(reverse_lazy('experiments:results_risk', kwargs={'session_id': session_id}))

            # check monitor
            monitor = RequestMonitor.objects.get(group=user.player.group, name=Constants.MONITOR_S4)
            print("monitor {}|{} var {}, condition {}".format(monitor.name, monitor.group, monitor.var,
                                                              monitor.condition))

            # player must be waiting
            self.assertContains(response, 'The amount remaining on your private account is', status_code=200)

        toggle_registration()

        # Now check the database to see if there are errors
        # Check monitors condition is false
        self.assertEqual(RequestMonitor.objects.filter(condition=True).count(), 0)
        # Check no participants are in monitor queue
        self.assertEqual((RequestMonitor.objects.annotate(size_queue=Count('queue'))).filter(size_queue__gt=0).count(),
                         0)
        # Check all monitor variables are set to 0
        self.assertEqual(RequestMonitor.objects.filter(~Q(var=0)).count(), 0)
        # Check group finished
        self.assertEqual(Group.objects.filter(game_finished=False).count(), 0)
