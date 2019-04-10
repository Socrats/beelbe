from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import generic

from experiments.constants import Constants
from experiments.models import Player


class LoginRequiredMixinExperiments(generic.View):
    login_url = reverse_lazy('experiments:index')
    redirect_field_name = 'next'

    def dispatch(self, request, *args, **kwargs):
        # I only need to check if user logged in -> user id on session plus session token?
        if ('user_id' not in request.session) or (not Player.objects.filter(id=request.session['user_id']).exists()):
            return HttpResponseRedirect(self.login_url)

        return super(LoginRequiredMixinExperiments, self).dispatch(request, *args, **kwargs)


def login_required_experiments(function=None, redirect_field_name=REDIRECT_FIELD_NAME,
                               login_url=reverse_lazy('experiments:login')):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            if ('user_id' not in request.session) or (
                    not Player.objects.filter(id=request.session['user_id']).exists()):
                return HttpResponseRedirect(login_url)
            else:
                return view_func(request, *args, **kwargs)

        return _wrapper_view

    return decorator


def check_game_finished():
    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            player = get_object_or_404(Player, pk=request.user.id)
            if player.session.finished or player.profile.finished:
                return HttpResponseRedirect(reverse_lazy('experiments:logout'))
            return view_func(request, *args, **kwargs)

        return _wrapper_view

    return decorator


def check_experiment_state(sender=None):
    """
    Should check the experiment state and from where the student has
    come, so that if the fsm schema is not being followed, the view
    should not be called and instead the participant should be
    redirected to the correct state. Also, if the experiment_state is
    Constants.STATE_FINISH, the participant should be logged out
    :return: decorator
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            player = get_object_or_404(Player, pk=request.user.id)
            if (player.profile.experiment_state not in sender) or (
                        player.profile.experiment_state == Constants.STATE_FINISH):
                # Check if player in a transition:
                if player.profile.transition_state == Constants.STATE_TRANSITION_S2:
                    # transition to state S2 is finish_results_view
                    return HttpResponseRedirect(
                        reverse_lazy('experiments:results_round', kwargs={'session_id': player.session.id}))
                elif player.profile.transition_state == Constants.STATE_TRANSITION_S3:
                    # transition to state S3 is finish_round_view
                    return HttpResponseRedirect(
                        reverse_lazy('experiments:game_round', kwargs={'session_id': player.session.id}))
                elif player.profile.transition_state == Constants.STATE_TRANSITION_S4:
                    # transition to state S4 is transition_risk
                    return HttpResponseRedirect(
                        reverse_lazy('experiments:results_risk_wait', kwargs={'session_id': player.session.id}))

                if player.profile.experiment_state == Constants.STATE_TEST:
                    return HttpResponseRedirect(
                        reverse_lazy('experiments:test', kwargs={'session_id': player.session.id}))
                elif player.profile.experiment_state == Constants.STATE_GAME_S2:
                    return HttpResponseRedirect(
                        reverse_lazy('experiments:game', kwargs={'session_id': player.session.id}))
                elif player.profile.experiment_state == Constants.STATE_GAME_S3:
                    return HttpResponseRedirect(
                        reverse_lazy('experiments:results', kwargs={'session_id': player.session.id}))
                elif player.profile.experiment_state == Constants.STATE_GAME_S4:
                    return HttpResponseRedirect(
                        reverse_lazy('experiments:results_risk', kwargs={'session_id': player.session.id}))
                elif player.profile.experiment_state == Constants.STATE_QUIZ:
                    return HttpResponseRedirect(
                        reverse_lazy('experiments:userinfo', kwargs={'session_id': player.session.id}))
                else:
                    return HttpResponseRedirect(reverse_lazy('experiments:logout'))
            return view_func(request, *args, **kwargs)

        return _wrapper_view

    return decorator


def check_transition(sender=None, target=None):
    """
    Should enforce a finite state machine by checking that the transition between states is correct. Only the
    states described on sender can transit to the current view, and the current view must transition only to one
    of the possible states described at target.
    
    :param sender: previous state
    :param target: next state
    :return: 
    """
    pass


def test_concurrently(times):
    import threading
    """
    Add this decorator to small pieces of code that you want to test
    concurrently to make sure they don't raise exceptions when run at the
    same time.  E.g., some Django views that do a SELECT and then a subsequent
    INSERT might fail when the INSERT assumes that the data has not changed
    since the SELECT.
    """

    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []

            def call_test_func():
                try:
                    test_func(*args, **kwargs)
                except Exception as e:
                    exceptions.append(e)
                    raise

            threads = []
            for i in range(times):
                threads.append(threading.Thread(target=call_test_func))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                raise Exception('test_concurrently intercepted %s exceptions: %s' % (len(exceptions), exceptions))

        return wrapper

    return test_concurrently_decorator


def test_concurrently_users(times):
    import threading
    """
    Add this decorator to small pieces of code that you want to test
    concurrently to make sure they don't raise exceptions when run at the
    same time.  E.g., some Django views that do a SELECT and then a subsequent
    INSERT might fail when the INSERT assumes that the data has not changed
    since the SELECT.
    """

    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []

            def call_test_func(user_number=None):
                try:
                    test_func(user_number)
                except Exception as e:
                    exceptions.append(e)
                    raise

            threads = []
            for i in range(times):
                threads.append(threading.Thread(target=call_test_func, kwargs={'user_number': i}))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                raise Exception('test_concurrently intercepted %s exceptions: %s' % (len(exceptions), exceptions))

        return wrapper

    return test_concurrently_decorator
