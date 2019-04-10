# coding=utf-8
# ==============================================================================
# beelbe
# Copyright © 2016 Elias F. Domingos. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import json
# import the logging library
import logging

from django.contrib.auth import (login as auth_login, )
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import (LoginView, )
# from django.template import Context, Template
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import (transaction, DatabaseError, )
from django.db.models import (Sum, IntegerField, Count, F, )
from django.http import (HttpResponse, HttpResponseRedirect, )
from django.shortcuts import (get_object_or_404, render, )
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import is_safe_url
from django.utils.translation import get_language
from django.views import generic
from numpy import random, floor

from .constants import Constants
from .decorators import (check_game_finished, check_experiment_state)
from .forms import UserInfoForm
import comp.comprehension as comp
from .models import (
    CollectiveRiskGame, Profile, Survey, Player, GameData, RequestMonitor, Instruction, Group,
)
from .utils import calculate_final_round

# Get an instance of a logger
logger = logging.getLogger(__name__)


class ExperimentsLogin(LoginView):
    """
        Display the login form and handle the login action.
    """
    user = None

    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = None

        if self.user is not None:
            redirect_to = check_user_state(self.user)

        if redirect_to is None:
            redirect_to = self.request.POST.get(
                self.redirect_field_name,
                self.request.GET.get(self.redirect_field_name, '')
            )
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ''

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        auth_login(self.request, form.get_user())
        self.user = form.get_user()
        return HttpResponseRedirect(self.get_success_url())


def check_user_state(user):
    """
    Checks if the user's state and returns a redirect url
    :param user: user object
    :return: redirect_to_state url
    """
    redirect_to = None
    # If player was already doing the experiment, redirect to previous state
    if user.player.profile.participated:
        # Check if player in a transition:
        if user.player.profile.transition_state == Constants.STATE_TRANSITION_S2:
            # transition to state S2 is finish_results_view
            redirect_to = reverse_lazy('experiments:results_round', kwargs={'session_id': user.player.session.id})
        elif user.player.profile.transition_state == Constants.STATE_TRANSITION_S3:
            # transition to state S3 is finish_round_view
            redirect_to = reverse_lazy('experiments:game_round', kwargs={'session_id': user.player.session.id})
        elif user.player.profile.transition_state == Constants.STATE_TRANSITION_S4:
            # transition to state S4 is transition_risk
            redirect_to = reverse_lazy('experiments:results_risk_wait', kwargs={'session_id': user.player.session.id})

        if user.player.profile.experiment_state == Constants.STATE_TEST:
            redirect_to = reverse_lazy('experiments:test', kwargs={'session_id': user.player.session.id})
        elif user.player.profile.experiment_state == Constants.STATE_GAME_S2:
            redirect_to = reverse_lazy('experiments:game', kwargs={'session_id': user.player.session.id})
        elif user.player.profile.experiment_state == Constants.STATE_GAME_S3:
            redirect_to = reverse_lazy('experiments:results', kwargs={'session_id': user.player.session.id})
        elif user.player.profile.experiment_state == Constants.STATE_GAME_S4:
            redirect_to = reverse_lazy('experiments:results_risk', kwargs={'session_id': user.player.session.id})
        elif user.player.profile.experiment_state == Constants.STATE_QUIZ:
            redirect_to = reverse_lazy('experiments:userinfo', kwargs={'session_id': user.player.session.id})
        elif user.player.profile.experiment_state == Constants.STATE_FINISH:
            redirect_to = reverse_lazy('experiments:logout')

    return redirect_to


class InstructionsView(LoginRequiredMixin, generic.ListView):
    template_name = 'experiments/instructions.html'
    context_object_name = 'player'
    login_url = reverse_lazy('experiments:login')

    def get_queryset(self):
        user = get_object_or_404(User, pk=self.request.user.id)
        if user.player.profile.experiment_state == Constants.STATE_LOGIN and not user.player.profile.participated:
            # Update personal endowment only the first time the player has played the game
            game = CollectiveRiskGame.objects.get(id=user.player.session.treatment.game.id)
            Profile.objects.filter(player=user.player).update(experiment_state=Constants.STATE_INSTRUCTIONS,
                                                              transition_state=Constants.STATE_NO_TRANSITION,
                                                              private_account=game.endowment,
                                                              participated=True,
                                                              time_start_experiment=timezone.now())
            self.request.session['experiment_state'] = Constants.STATE_INSTRUCTIONS

            # If deadline is variable, then calculate last round
            if game.is_round_variable:
                if not user.player.group.finishing_round_selected:
                    final_round, trials = calculate_final_round(p=game.termination_probability,
                                                                min_round=game.min_round,
                                                                dice_faces=game.dice_faces
                                                                )
                    Group.objects.filter(id=user.player.group.id).update(finishing_round=final_round,
                                                                         dice_results=','.join(map(str, trials)),
                                                                         finishing_round_selected=True)

        return user.player

    def get_context_data(self, **kwargs):
        # first get language
        lang = get_language()
        # Call the base implementation first to get a context
        instructions = Instruction.objects.get(treatment=self.request.user.player.session.treatment, lang=lang)
        context = super(InstructionsView, self).get_context_data(**kwargs)
        page = self.request.GET.get('page')
        instructions_pages = instructions.text.split("[PAGE]")

        paginator = Paginator(instructions_pages, 1)  # show one per page
        try:
            context['instructions'] = paginator.page(page)
            context['fraction'] = (float(page) / paginator.num_pages) * 100
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            context['instructions'] = paginator.page(1)
            context['fraction'] = (1 / paginator.num_pages) * 100
        except EmptyPage:
            # If page is put of range(e.e. 9999), deliver last page of results.
            context['instructions'] = paginator.page(paginator.num_pages)
            context['fraction'] = 100.0

        return context


class TestView(LoginRequiredMixin, generic.FormView):
    template_name = 'experiments/test.html'
    form_class = comp.TestForm
    login_url = reverse_lazy('experiments:login')

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        return HttpResponseRedirect(
            reverse_lazy('experiments:results_round', kwargs={'session_id': self.request.user.player.session_id}))

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        participant = get_object_or_404(Player, pk=self.request.user.id)
        context = super(TestView, self).get_context_data(**kwargs)
        Profile.objects.filter(player=participant).update(experiment_state=Constants.STATE_TEST,
                                                          transition_state=Constants.STATE_NO_TRANSITION)
        self.request.session['experiment_state'] = Constants.STATE_TEST
        self.request.session.save()

        return context


def get_monitor_name(monitors, g_round):
    try:
        monitors.all().get(name=Constants.MONITOR_S4)
    except RequestMonitor.DoesNotExist:
        try:
            return monitors.filter(name__iregex=r"\ymonitorS{0}r{1}\y".format('[2-3]', g_round)).order_by('-name')[
                0].name
        except IndexError:
            raise
    else:
        return Constants.MONITOR_S4


@login_required(login_url=reverse_lazy('experiments:login'))
def sync_view(request, *args, **kwargs):
    """Check monitor condition and set players on the correct queue"""
    player = get_object_or_404(Player, pk=request.user.id)
    # First check in which queue is the player
    try:
        monitor_name = player.monitors.all()[0].name
    except IndexError:
        logger.exception("[ERROR] Player {} is not in a queue!".format(player))
        raise IndexError
    else:
        # We check if the player is in more than one monitor, in which case we get the one for the correct round
        if player.monitors.all().count() > 1:
            logger.warning("[WARNING] Player {} is in more than one queue!".format(player))
            try:
                monitor_name = get_monitor_name(player.monitors, player.profile.last_round)
            except IndexError:
                logger.error("[ERROR] No monitors follow the pattern requested!")
                monitor_name = player.monitors.all()[0].name

    try:
        with transaction.atomic():

            can_continue = RequestMonitor.check_condition(player.group, monitor_name,
                                                          lambda x: Profile.objects.filter(
                                                              group_number=player.profile.group_number,
                                                              player__experiment=player.experiment,
                                                              player__session=player.session,
                                                              player__user__is_active=True).count() == x, True)

            if can_continue:
                # First signal the player
                RequestMonitor.signal(player, monitor_name=monitor_name)
                game = CollectiveRiskGame.objects.get(id=player.session.treatment.game.id)
                # then update the accounts info on GameData (public_account = total_group_end - sum(private_accounts))
                accounts_info = Profile.objects.filter(
                    player__group=player.group,
                    player__experiment=player.experiment,
                    player__session=player.session,
                    player__user__is_active=True).aggregate(
                    public_account=Count('player') * game.endowment - Sum('private_account',
                                                                          output_field=IntegerField()))
                # update game data
                GameData.objects.filter(player=player, session=player.session, round=player.profile.last_round,
                                        group=player.group).update(public_account=accounts_info['public_account'])
                # update group public_account
                Group.objects.filter(pk=player.group.pk).update(public_account=accounts_info['public_account'])
    except DatabaseError:
        can_continue = False
        logger.error("[Player {}] Database error on wait".format(player.pk))

    response_data = {
        'session_id': player.session.id,
        'can_continue': can_continue
    }
    return HttpResponse(
        json.dumps(response_data),
        content_type="application/json"
    )


@login_required(login_url=reverse_lazy('experiments:login'))
@check_game_finished()
@check_experiment_state(sender=[Constants.STATE_TEST, Constants.STATE_GAME_S3, Constants.STATE_GAME_S2])
def game_view(request, *args, **kwargs):
    """Defines the game view"""
    player = get_object_or_404(Player, pk=request.user.id)

    RequestMonitor.check_condition(group=player.group,
                                   monitor_name="{}r{}".format(Constants.MONITOR_S2, player.profile.last_round),
                                   condition=lambda x: x == 0, update_value=False)

    Profile.objects.filter(player=player).update(experiment_state=Constants.STATE_GAME_S2,
                                                 transition_state=Constants.STATE_NO_TRANSITION)
    request.session['experiment_state'] = Constants.STATE_GAME_S2
    request.session.save()

    game = CollectiveRiskGame.objects.get(id=player.session.treatment.game.id)
    if player.profile.last_round > 1:
        last_round_actions_others = player.get_last_round_actions_others()
        player_last_action = player.get_last_round_action()
    else:
        last_round_actions_others = False
        player_last_action = False
    currency_name = "EMUs" if game.is_using_emus else game.real_currency

    total_rounds = game.rounds
    percentage = (player.profile.last_round / total_rounds) * 100
    if game.is_round_variable:
        total_rounds = game.min_round
        percentage = (player.profile.last_round / total_rounds) * 100
        if game.min_round <= player.profile.last_round:
            percentage = 100

    return render(request, 'experiments/game.html', {
        'session_id': player.session.id,
        'player': player,
        'round': {
            'norm': player.profile.last_round,
            'percentage': percentage,
            'total_rounds': total_rounds,
        },
        'valid_actions': game.get_valid_actions_as_list(),
        'currency_name': currency_name,
        'last_round_actions_others': last_round_actions_others,
        'player_last_action': player_last_action,
        'is_round_variable': game.is_round_variable,
    })


@login_required(login_url=reverse_lazy('experiments:login'))
@check_game_finished()
@check_experiment_state(sender=[Constants.STATE_GAME_S2])
def finish_round_view(request, *args, **kwargs):
    """Defines the view that transitions between the game view (S2) and the results view (S3)"""
    player = get_object_or_404(Player, pk=request.user.id)
    if player.profile.transition_state != Constants.STATE_TRANSITION_S3:
        try:
            with transaction.atomic():
                game_data, created = GameData.objects.get_or_create(player=player, session=player.session,
                                                                    opponent=player,
                                                                    round=player.profile.last_round,
                                                                    group=player.group)
                if created:
                    # First update game data
                    game_data.action = request.POST['action']
                    game_data.private_account = player.profile.private_account - int(request.POST['action'])
                    game_data.time_round_start = request.POST['time_round_start']
                    game_data.time_round_ends = request.POST['time_round_end']
                    game_data.time_elapsed = request.POST['time_elapsed']
                    game_data.save()
                    # Then update player profile
                    Profile.objects.filter(player=player).update(
                        private_account=F('private_account') - int(request.POST['action']),
                        transition_state=Constants.STATE_TRANSITION_S3)

        except DatabaseError:
            # if there is an error send participant back to the previous view
            logger.error("[Player {}] Database error on finish_round_view".format(player.pk))
            return HttpResponseRedirect(
                reverse_lazy("experiments:game", kwargs={'session_id': player.session_id}))
        except KeyError:
            logger.error("[Player {}] {}".format(player.pk, KeyError))
            # if there is an error go back to the previous view
            return HttpResponseRedirect(
                reverse_lazy("experiments:game", kwargs={'session_id': player.session_id}))

    # otherwise send participant to the wait view
    try:
        RequestMonitor.wait(player, monitor_name="{}r{}".format(Constants.MONITOR_S3, player.profile.last_round))
    except DatabaseError:
        logger.error("[Player {}] did not wait on monitor".format(player.pk))
    except RequestMonitor.DoesNotExist:
        logger.exception("[Player {0}] did not wait on monitor {1}r{2}".format(player.pk, Constants.MONITOR_S3,
                                                                               player.profile.last_round))
    return render(request, 'experiments/wait.html', {
        'session_id': player.session.id,
        'next': reverse("experiments:results", kwargs={'session_id': player.session.id}),
        'can_continue': False
    })


@login_required(login_url=reverse_lazy('experiments:login'))
@check_game_finished()
@check_experiment_state(sender=[Constants.STATE_TEST, Constants.STATE_GAME_S3])
def finish_results_view(request, *args, **kwargs):
    """Defines the view that transitions between the results view (S3) and the game view (S2)"""
    finished_game = False
    player = get_object_or_404(Player, pk=request.user.id)

    if player.profile.transition_state != Constants.STATE_TRANSITION_S2:
        try:
            with transaction.atomic():
                if player.profile.experiment_state == Constants.STATE_GAME_S3:
                    game_data, created = GameData.objects.get_or_create(player=player, session=player.session,
                                                                        opponent=player,
                                                                        round=player.profile.last_round,
                                                                        group=player.group)
                    game_data.prediction_question = request.POST['prediction']
                    game_data.time_question_start = request.POST['time_round_start']
                    game_data.time_question_end = request.POST['time_round_end']
                    game_data.time_question_elapsed = request.POST['time_elapsed']
                    game_data.save()

                    if created:
                        logger.error(
                            "[player {}]:Game data created on S3 and not S2 (when making an action)".format(player.pk))

                    game = CollectiveRiskGame.objects.get(id=player.session.treatment.game.id)
                    finished_game = check_game_has_finished(player, game)

                # I must check that players never acquire the previous state
                Profile.objects.filter(player=player).update(last_round=F('last_round') + 1,
                                                             transition_state=Constants.STATE_TRANSITION_S2)
        except DatabaseError:
            logger.error("[Player {}] Database error on finish_results_view".format(player.pk))
            # if there is an error go back to the previous view
            return HttpResponseRedirect(
                reverse_lazy("experiments:results", kwargs={'session_id': player.session_id}))
        except KeyError:
            logger.error("[Player {}] {}".format(player.pk, KeyError))
            # if there is an error go back to the previous view
            return HttpResponseRedirect(
                reverse_lazy("experiments:results", kwargs={'session_id': player.session_id}))

    if finished_game:
        return HttpResponseRedirect(
            reverse_lazy("experiments:results_risk_wait", kwargs={'session_id': player.session_id}))
    else:
        try:
            player.profile.refresh_from_db()
            RequestMonitor.wait(player, monitor_name="{}r{}".format(Constants.MONITOR_S2, player.profile.last_round))
        except DatabaseError:
            logger.error("[Player {}] did not wait on monitor".format(player.pk))
        except RequestMonitor.DoesNotExist:
            logger.exception("[Player {0}] did not wait on monitor {1}r{2}".format(player.pk, Constants.MONITOR_S2,
                                                                                   player.profile.last_round))
        return render(request, 'experiments/wait.html', {
            'session_id': player.session.id,
            'next': reverse("experiments:game", kwargs={'session_id': player.session.id}),
            'can_continue': False
        })


@login_required(login_url=reverse_lazy('experiments:login'))
@check_game_finished()
@check_experiment_state(sender=[Constants.STATE_GAME_S2, Constants.STATE_GAME_S3])
def results_view(request, *args, **kwargs):
    """Defines the view where participants can see the results of the round"""
    player = get_object_or_404(Player, pk=request.user.id)
    Profile.objects.filter(player=player).update(experiment_state=Constants.STATE_GAME_S3,
                                                 transition_state=Constants.STATE_NO_TRANSITION)
    request.session['experiment_state'] = Constants.STATE_GAME_S3
    request.session.save()

    RequestMonitor.check_condition(group=player.group,
                                   monitor_name="{}r{}".format(Constants.MONITOR_S3, player.profile.last_round),
                                   condition=lambda x: x == 0, update_value=False)

    game = CollectiveRiskGame.objects.get(id=player.session.treatment.game.id)

    dice_result = -1
    show_dice_result = False
    total_rounds = game.rounds
    percentage = (player.profile.last_round / total_rounds) * 100

    if game.is_round_variable:
        total_rounds = game.min_round
        percentage = (player.profile.last_round / total_rounds) * 100
        show_dice_result = player.profile.last_round >= game.min_round
        if show_dice_result:
            dice_result = player.group.get_round_dice_result(player.profile.last_round, game.min_round)
            percentage = 100
    game_end = player.group.finishing_round <= player.profile.last_round

    return render(request, 'experiments/roundpred.html', {
        'session_id': player.session.id,
        'round': {
            'norm': player.profile.last_round,
            'percentage': percentage,
            'total_rounds': total_rounds,
        },
        'player': player,
        'prediction_question': Constants.PREDICT_PUBLIC_ACCOUNT,
        'show_dice_result': show_dice_result,
        'dice_result': dice_result,
        'game_end': game_end,
        'accepted_dice_values': [i for i in range(1, int(game.termination_probability * game.dice_faces) + 1)],
        'is_round_variable': game.is_round_variable,
    })


@transaction.atomic
def check_game_has_finished(player, game):
    """
    Checks if the game has finished
    :param player: (Player object) Current player
    :param game: current game being played
    :return: (boolean) True if the game has finished, else False
    """
    finished_game = False

    # Check if game has finished
    if game.is_round_variable:
        # Check if game already finished
        if player.group.finishing_round <= player.profile.last_round:
            finished_game = True
            Group.objects.filter(pk=player.group.pk).update(game_finished=True)
    elif game.rounds <= player.profile.last_round:
        finished_game = True
        Group.objects.filter(pk=player.group.pk).update(finishing_round=player.profile.last_round, game_finished=True)

    return finished_game


@login_required(login_url=reverse_lazy('experiments:login'))
@check_game_finished()
@check_experiment_state(sender=[Constants.STATE_GAME_S3])
def transition_risk(request, *args, **kwargs):
    """Defines the view that transitions between the results view (S3) and the game view (S2)"""
    player = get_object_or_404(Player, pk=request.user.id)
    Profile.objects.filter(player=player).update(transition_state=Constants.STATE_TRANSITION_S4)

    try:
        RequestMonitor.wait(player, monitor_name=Constants.MONITOR_S4)
    except DatabaseError:
        logger.error("[Player {}] did not wait on monitor".format(player.pk))
    return render(request, 'experiments/wait.html', {
        'session_id': player.session.id,
        'next': reverse("experiments:results_risk", kwargs={'session_id': player.session.id}),
        'can_continue': False
    })


@login_required(login_url=reverse_lazy('experiments:login'))
@check_game_finished()
@check_experiment_state(sender=[Constants.STATE_GAME_S3, Constants.STATE_GAME_S4])
def check_threshold_view(request, *args, **kwargs):
    player = get_object_or_404(Player, pk=request.user.id)
    Profile.objects.filter(player=player).update(experiment_state=Constants.STATE_GAME_S4,
                                                 transition_state=Constants.STATE_NO_TRANSITION)

    # reinitialize monitor
    RequestMonitor.check_condition(group=player.group, monitor_name=Constants.MONITOR_S4,
                                   condition=lambda x: x == 0, update_value=False)

    # first we get the game object
    game = CollectiveRiskGame.objects.get(id=player.session.treatment.game.id)

    # then we check how much was accumulated in the public account
    # for that we check the private account of all members of the group
    accounts_info = Profile.objects.filter(
        group_number=player.profile.group_number,
        player__experiment=player.experiment,
        player__session=player.session,
        player__user__is_active=True).aggregate(
        public_account=Count('player') * game.endowment - Sum('private_account', output_field=IntegerField()))

    # check whether the random value has been generated
    try:
        with transaction.atomic():
            if not player.group.random_value_generated:
                Group.objects.filter(pk=player.group.pk).update(random_value=random.rand(), random_value_generated=True)
    except DatabaseError:
        logger.error("[Player {}] did not set group random value correctly!".format(player.pk))

    player.group.refresh_from_db()
    random_value = player.group.random_value
    risk = game.risk_prob
    gain_emus = player.profile.private_account
    # Now compare it to the threshold
    if accounts_info['public_account'] < game.threshold:
        # throw the dice to decide if everybody loses everything
        if random_value < game.risk_prob:
            # Return loss phrase
            return_state = 'LOSS'
            Profile.objects.filter(pk=player.profile.pk).update(threshold_state=Constants.LOSS)
            risk = (game.risk_prob * 100) + 1
            gain_emus = 0
        else:
            # return not loss but threshold not achieved phrase
            return_state = 'NLOSS'
            Profile.objects.filter(pk=player.profile.pk).update(threshold_state=Constants.NLOSS)
            risk = (game.risk_prob * 100) + 1
    else:
        # return threshold achieved phrase
        return_state = 'ACK'
        Profile.objects.filter(pk=player.profile.pk).update(threshold_state=Constants.ACK)

    return render(request, 'experiments/risk_check.html', {
        'session_id': player.session.id,
        'return_state': return_state,
        'risk': risk,
        'random_value': floor(random_value * 100) + 1,
        'threshold': game.threshold,
        'public_account': accounts_info['public_account'],
        'gain': {
            'emus': gain_emus,
            'euros': gain_emus * game.conversion_rate + 2.5
        },
    })


class UserInfoView(LoginRequiredMixin, generic.FormView):
    template_name = 'experiments/userinfo.html'
    form_class = UserInfoForm
    model = Survey
    context_object_name = 'player'
    login_url = reverse_lazy('experiments:login')

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed
        # It should return and HttpResponse
        obj = form.save(commit=False)
        obj.player = self.request.user.player
        try:
            survey = Survey.objects.get(player=obj.player)
        except Survey.DoesNotExist:
            obj.save()
        return super(UserInfoView, self).form_valid(form)

    def get_success_url(self):
        participant = get_object_or_404(Player, pk=self.request.user.id)
        return reverse_lazy('experiments:thanks', kwargs={'session_id': participant.session.id})

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        participant = get_object_or_404(Player, pk=self.request.user.id)
        context = super(UserInfoView, self).get_context_data(**kwargs)
        context['title'] = 'Experiments admin'
        Profile.objects.filter(player=participant).update(experiment_state=Constants.STATE_QUIZ)

        return context


class ThanksView(LoginRequiredMixin, generic.ListView):
    template_name = 'experiments/thanks.html'
    context_object_name = 'player'
    login_url = reverse_lazy('experiments:login')

    def get_queryset(self):
        player = get_object_or_404(Player, pk=self.request.user.id)
        Profile.objects.filter(player=player).update(experiment_state=Constants.STATE_FINISH, finished=True,
                                                     time_ends_experiment=timezone.now())
        self.request.session['experiment_state'] = Constants.STATE_FINISH

        return player
