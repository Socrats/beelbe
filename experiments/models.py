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

# import the logging library
import logging

from django.contrib.auth.models import User
from django.core.exceptions import (ValidationError, NON_FIELD_ERRORS)
from django.core.validators import validate_comma_separated_integer_list
from django.db import models, transaction
from django.db.models import Max, F, Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from nltk.corpus import words
from numpy import random

from beelbe.settings import LANGUAGES
from experiments.constants import Constants, SurveyStrings

# Get an instance of a logger
logger = logging.getLogger(__name__)


# Create your models here.
class Experiment(models.Model):
    experiment_name = models.CharField(max_length=100)
    experiment_metadata = models.CharField(max_length=400)
    created = models.DateTimeField('Creation Date', editable=False)
    last_modified = models.DateTimeField('Last modified')
    experiment_status = models.IntegerField(
        choices=Constants.EXPERIMENT_STATUS,
        default=Constants.UNFINISHED,
    )

    def save(self, *args, **kwargs):
        """On save, update timestamps"""
        if not self.id:
            self.created = timezone.now()
        self.last_modified = timezone.now()
        return super(Experiment, self).save(*args, **kwargs)

    def __str__(self):
        return self.experiment_name


class Game(models.Model):
    game_uid = models.CharField("Unique Identifier", unique=True, max_length=10)
    game_name = models.CharField("Name", max_length=100)
    game_metadata = models.CharField("Metadata", max_length=400)
    topology = models.CharField(
        max_length=10,
        choices=Constants.TOPOLOGY_CHOICES,
        default=Constants.NONE,
    )
    num_players = models.IntegerField('Number of players')
    is_using_emus = models.BooleanField("Uses EMUs", default=True)
    real_currency = models.CharField("Real monetary currency", max_length=10,
                                     default="EUR")
    conversion_rate = models.FloatField("Conversion rate", default=1.0)

    def __str__(self):
        return self.game_name


class EndProbability(models.Model):
    """Is associated to each game and determines"""
    round = models.IntegerField("Round at which the experiment might finish", default=0)
    probability = models.FloatField("Probability that the experiment might finish at the given round", default=0)

    class Meta:
        unique_together = ('round', 'probability',)

    def __str__(self):
        return "round: {round} | p: {probability}".format(round=self.round, probability=self.probability)


class CollectiveRiskGame(Game):
    threshold = models.IntegerField('Threshold')
    risk_prob = models.FloatField('Risk probability', default=0.9)
    group_size = models.IntegerField("Group Size")
    endowment = models.IntegerField("Endowment", default=Constants.ENDOWMENT)
    valid_actions = models.CharField("Valid actions", max_length=10, default="0,2,4",
                                     validators=[validate_comma_separated_integer_list])
    rounds = models.IntegerField("Game rounds")
    is_round_variable = models.BooleanField('Deadline variable?', default=False)
    round_distribution = models.CharField(
        "Stochastic model to calculate final round",
        max_length=10,
        choices=Constants.DISTRIBUTION_CHOICES,
        default=Constants.UNIFORM
    )
    round_variance = models.FloatField("Threshold variance", default=0)
    distribution_steps = models.IntegerField("Number of rounds for which there will be a"
                                             "certain probability that the game will finish", default=0)
    end_probabilities = models.ManyToManyField(EndProbability, related_name="end_probabilities", blank=True)
    termination_probability = models.FloatField("Probability that the game will finish at a certain round", default=0.0)
    min_round = models.IntegerField("Minimum number of rounds that the game will take", default=0)
    dice_faces = models.IntegerField("Number of faces for the dice representation of the random generator", default=6)

    def get_initial_public_account(self):
        return self.endowment * self.group_size

    def get_valid_actions_as_list(self):
        return self.valid_actions.split(",")

    def set_rounds_model(self):
        pass

    def get_rounds(self):
        if not self.is_round_variable:
            return self.rounds

    def is_probability_correct(self):
        aggr = self.end_probabilities.aggregate(sum_prob=Sum('probabilities'))
        if aggr['sum_prob'] > 1:
            return False
        return True

    get_rounds.short_description = "Returns final round according to the specified model"


class Treatment(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="treatments")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="treatments")
    treatment_name = models.CharField(max_length=100)
    treatment_metadata = models.CharField(max_length=400, blank=True)

    def __str__(self):
        return "Experiment {} | {}".format(self.experiment.experiment_name, self.treatment_name)

    class Meta:
        ordering = ('experiment', 'game',)


class Session(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="sessions")
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE, related_name="sessions")
    session_number = models.IntegerField("Session number")
    session_metadata = models.CharField(max_length=200, blank=True)
    scheduled_date = models.DateTimeField('Scheduled for')
    time_start = models.DateTimeField('Start at', null=True, blank=True)
    time_finish = models.DateTimeField('Finished at', null=True, blank=True)
    finished = models.BooleanField('finished', default=False)
    structure_assigned = models.BooleanField(
        verbose_name='structure assigned',
        default=False
    )
    group_size = models.IntegerField('group size', default=0)

    def set_time_start(self):
        pass

    def set_time_finish_and_duration(self):
        pass

    def set_session_number(self):
        pass

    def get_session_duration(self):
        return self.time_finish - self.time_start

    get_session_duration.admin_order_field = 'experiment'
    get_session_duration.short_description = "Duration of the session"

    def __str__(self):
        return "Session {}".format(self.session_number)

    class Meta:
        ordering = ('experiment', 'treatment', 'session_number',)


class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="player", primary_key=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.PROTECT, related_name="players", null=True)
    session = models.ForeignKey(Session, on_delete=models.PROTECT, related_name="players", null=True)
    group = models.ForeignKey("Group", related_name="members", null=True, blank=True, on_delete=models.PROTECT)

    def get_last_round(self):
        return self.game_data.aggregate(Max('round'))

    def get_last_action(self):
        return self.game_data.filter(round=self.get_last_round()).action

    def get_last_round_actions_others(self):
        return GameData.objects.filter(round=self.profile.last_round - 1, session=self.session,
                                       group=self.group).exclude(player=self).values_list('action', flat=True).order_by(
            'player')

    def get_last_round_action(self):
        try:
            action = GameData.objects.get(round=self.profile.last_round - 1, session=self.session,
                                          group=self.group, player=self).action
        except GameData.DoesNotExist:
            logger.exception("[ERROR] There is no game data for player {}".format(self))
            return None
        return action

    def __str__(self):
        return "{} | {} | {}".format(self.experiment, self.session, self.pk)


@receiver(post_save, sender=User)
def create_player(sender, instance, created, **kwargs):
    if created:
        if not instance.is_superuser:
            Player.objects.create(user=instance)
            instance.player.save()


class Profile(models.Model):
    """
    Holds extra information of each user needed for the experiment,
    and has a link to the game data
    """
    player = models.OneToOneField(
        Player,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='profile',
    )
    group_number = models.IntegerField('Group number', null=True, blank=True)
    private_account = models.IntegerField('Private account', default=Constants.ENDOWMENT)
    time_start_experiment = models.DateTimeField('Time session starts', null=True, blank=True)
    time_ends_experiment = models.DateTimeField('Time session ends', null=True, blank=True)
    last_round = models.IntegerField('Round number', default=0)
    finished = models.BooleanField(default=False)
    participated = models.BooleanField(default=False)
    experiment_state = models.CharField(
        "State of the experiment (e.g. Instructions)",
        max_length=10,
        choices=Constants.EXPERIMENT_STATES,
        default=Constants.STATE_INACTIVE
    )
    transition_state = models.CharField(
        "If player is in a transition",
        max_length=10,
        choices=Constants.TRANSITION_STATES,
        default=Constants.STATE_NO_TRANSITION
    )
    created = models.DateTimeField('Creation Date', editable=False)
    language = models.CharField(
        "Language in which the player did the experiment.",
        max_length=10,
        choices=LANGUAGES,
        blank=True
    )
    threshold_state = models.IntegerField("End state of the game", choices=Constants.THRESHOLD_STATES, null=True,
                                          blank=True)

    def get_experiment_duration(self):
        """:returns timedelta"""
        return self.time_ends_experiment - self.time_start_experiment

    def get_value_in_euros(self):
        """:returns float - convert EMUs to euros"""
        if self.threshold_state != Constants.LOSS:
            value = self.private_account * self.player.session.treatment.game.conversion_rate + 2.5
        else:
            value = 2.5
        return value

    def __str__(self):
        return 'Player {} Profile'.format(self.player.pk)

    class Meta:
        ordering = ('player', 'group_number',)


@receiver(post_save, sender=Player)
def create_player_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(player=instance,
                               created=timezone.now(),
                               experiment_state=Constants.STATE_LOGIN)


@receiver(post_save, sender=Player)
def save_player_profile(sender, instance, **kwargs):
    instance.profile.save()


class GameData(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="game_data")
    session = models.ForeignKey(Session, on_delete=models.PROTECT, related_name="game_data")
    opponent = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="opponent")
    group = models.ForeignKey("Group", null=True, related_name="game_data", on_delete=models.PROTECT)
    round = models.IntegerField('Round number')
    action = models.IntegerField('Action', choices=Constants.CRD_VALID_ACTIONS, null=True, blank=True)
    private_account = models.IntegerField('Private account', default=0, null=True, blank=True)
    public_account = models.IntegerField('Public account', default=0, null=True, blank=True)
    time_round_start = models.DateTimeField('Time round starts', null=True, blank=True)
    time_round_ends = models.DateTimeField('Time round ends', null=True, blank=True)
    time_elapsed = models.TimeField('Time taken to make the action', null=True, blank=True)
    prediction_question = models.CharField(Constants.PREDICT_PUBLIC_ACCOUNT, blank=True, max_length=50)
    time_question_start = models.DateTimeField('Time question starts', null=True)
    time_question_end = models.DateTimeField('Time question ends', null=True)
    time_question_elapsed = models.TimeField('Time taken to make the prediction', null=True, blank=True)

    def get_decision_interval(self):
        """:returns timedelta"""
        return self.time_round_ends - self.time_round_start

    def get_question_interval(self):
        """:returns timedelta"""
        return self.time_question_start - self.time_question_end

    get_decision_interval.admin_order_field = 'player'
    get_decision_interval.short_description = "Time to make a decision"

    @staticmethod
    def get_last_round(session, group):
        return GameData.objects.filter(session=session, group=group).aggregate(Max('round'))['round__max']

    @staticmethod
    def get_last_round_actions(session, group):
        return GameData.objects.filter(round=GameData.get_last_round(session, group), session=session,
                                       group=group).values_list('action', flat=True).order_by('player')

    def __str__(self):
        return "{} | {} | {} | round {}".format(self.session, self.player, self.player.group, self.round)

    class Meta:
        ordering = ('session', 'player__group', 'player')


def generate_random_password():
    psw = ""
    word_list = words.words()
    rr = [word_list[random.randint(0, len(word_list))] for _ in range(2)]
    for wrd in rr:
        psw += str(wrd)

    return psw


class RunNow(models.Model):
    experiment_id = models.IntegerField('Experiment ID', default=0)
    treatment_id = models.IntegerField('Treatment ID', default=0)
    session_id = models.IntegerField('Session ID', default=0)
    experiment_on = models.BooleanField(default=False)

    def __str__(self):
        return 'Run now experiment' + str(self.experiment_id) + ' treatment' + str(self.treatment_id) + \
               ' session ' + str(self.session_id)


class RequestMonitor(models.Model):
    name = models.CharField(max_length=20)
    var = models.IntegerField('Queue 1', default=0)
    condition = models.BooleanField('Condition', default=False)
    group = models.ForeignKey("Group", related_name="monitors", on_delete=models.PROTECT)
    queue = models.ManyToManyField(Player, related_name='monitors', blank=True)

    @staticmethod
    @transaction.atomic
    def wait(player, monitor_name):
        monitor = RequestMonitor.objects.get(group=player.group,
                                             name=monitor_name)
        if player not in monitor.queue.all():
            monitor.queue.add(player)
            RequestMonitor.objects.filter(id=monitor.id).update(var=F('var') + 1)

    @staticmethod
    @transaction.atomic
    def check_condition(group, monitor_name, condition, update_value):
        monitor = RequestMonitor.objects.get(group=group, name=monitor_name)
        # If the condition is not update_value, then we update the condition if it's true
        if monitor.condition is not update_value:
            if condition(monitor.var):
                RequestMonitor.objects.filter(id=monitor.id).update(condition=update_value)
        monitor.refresh_from_db()

        return monitor.condition

    @staticmethod
    @transaction.atomic
    def signal(player, monitor_name):
        monitor = RequestMonitor.objects.get(group=player.group,
                                             name=monitor_name)
        if player in monitor.queue.all():
            monitor.queue.remove(player)
            RequestMonitor.objects.filter(id=monitor.id).update(var=F('var') - 1)

    def validate_unique(self, *args, **kwargs):
        super(RequestMonitor, self).validate_unique(*args, **kwargs)
        if not self.id:
            if self.__class__.objects.filter(name=self.name, group=self.group).exists():
                raise ValidationError(
                    {
                        NON_FIELD_ERRORS: [
                            'Monitor with group {} and name {} already exists.'.format(self.group, self.name),
                        ],
                    }
                )

    class Meta:
        ordering = ('group',)

    def __str__(self):
        return "{} {}".format(self.group, self.name)


class Group(models.Model):
    group_number = models.IntegerField('Group number', default=0)
    session = models.ForeignKey(Session, related_name="groups", on_delete=models.PROTECT)
    dice_results = models.CharField("Dice trials until success (game ends)", max_length=1000, default="0",
                                    validators=[validate_comma_separated_integer_list])
    finishing_round = models.IntegerField("Indicate at which round the game finishes", default=0)
    finishing_round_selected = models.BooleanField("Indicates if the finishing round has been selected", default=False)
    game_finished = models.BooleanField("Indicate if the game has finished", default=False)
    public_account = models.IntegerField("Public account of the group", default=0)
    current_round = models.IntegerField("indicates the current round of the game", default=0)
    random_value = models.FloatField("Random value generated to determine loss", default=0)
    random_value_generated = models.BooleanField("Indicate if the random value has been already generated",
                                                 default=False)

    def __str__(self):
        return "{} Group {}".format(self.session, self.group_number)

    def get_round_dice_result(self, current_round, min_round):
        """
        Returns the result of the dice for the correspondent round
        :return: int - result of the dice
        """
        dice_results = self.dice_results.split(',')
        idx = current_round - min_round
        return dice_results[idx]


class Survey(models.Model):
    """
    This model generates a table to be used as a small survey
    at the end of the experiment. We offer some example question,
    You should add more if you or adapt them to your experiment.
    In future version, we plan to make this survey dynamic, with
    questions stored in another table. This ways you should be able to
    create new surveys by selecting different types of questions and associate
    them to an specific experiment or treatment.
    """
    player = models.OneToOneField(Player, on_delete=models.CASCADE)
    gender = models.CharField(
        SurveyStrings.GENDER_QUESTION,
        max_length=10,
        choices=SurveyStrings.GENDER_CHOICES,
    )
    age = models.IntegerField(SurveyStrings.AGE_QUESTION)
    level_studies = models.CharField(SurveyStrings.STUDIES_QUESTION, choices=SurveyStrings.LEVEL_STUDIES_CHOICE,
                                     max_length=100)
    degree_question = models.CharField(SurveyStrings.DEGREE_QUESTION, choices=SurveyStrings.STUDIES_CHOICE,
                                       max_length=100)
    profession = models.CharField(SurveyStrings.PROFESSION_QUESTION, choices=SurveyStrings.PROFESSION_CHOICE,
                                  max_length=100, blank=True)
    game_theory_question = models.NullBooleanField(SurveyStrings.GAME_THEORY_QUESTION,
                                                   choices=SurveyStrings.YES_NO_CHOICE,
                                                   blank=True)
    which_game = models.NullBooleanField(SurveyStrings.WHICH_GAME_QUESTION, choices=SurveyStrings.YES_NO_CHOICE,
                                         blank=True)
    which_game_text = models.TextField(SurveyStrings.WHICH_GAME_ELABORATE, max_length=500, blank=True)
    expect_game_end_text = models.TextField(SurveyStrings.EXPECTATION_QUESTION, max_length=500, blank=True)
    information_question = models.TextField(SurveyStrings.INFORMATION_QUESTION, max_length=500, blank=True)
    risk_question = models.TextField(SurveyStrings.RISK_QUESTION, max_length=500, blank=True)
    contribution_question = models.TextField(SurveyStrings.CONTRIBUTION_QUESTION, max_length=500, blank=True)
    fairness_question = models.TextField(SurveyStrings.FAIRNESS_QUESTION, max_length=500, blank=True)
    game_duration_question = models.TextField(SurveyStrings.GAME_DURATION_QUESTION, max_length=500, blank=True)
    know_experiments_question = models.TextField(SurveyStrings.KNOW_EXPERIMENTS_QUESTION, max_length=500, blank=True)
    suggestion_question = models.TextField(SurveyStrings.SUGGESTIONS_QUESTION, max_length=500, blank=True)

    # Add more questions here!

    def __str__(self):
        return "Survey of {}".format(self.player.pk)


class Instruction(models.Model):
    treatment = models.ForeignKey("Treatment", on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, related_name='created_instructions')
    created_at = models.DateTimeField('Creation Date', editable=False)
    modified_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, related_name='modified_instructions')
    modified_at = models.DateTimeField('Last modified')
    text = models.TextField(verbose_name=_("Experiment instructions"))
    lang = models.CharField(
        "Language of the instruction.",
        max_length=10,
        choices=LANGUAGES
    )

    def save(self, *args, **kwargs):
        """On save, update timestamps"""
        if not self.id:
            self.created_at = timezone.now()
        self.modified_at = timezone.now()
        return super(Instruction, self).save(*args, **kwargs)

    def __str__(self):
        return "Instructions treatment {} | {}".format(self.treatment, self.lang)

    class Meta:
        permissions = (
            ("can_create", "Can create instructions"),
            ("can_modify", "Can vote in elections"),
        )
        ordering = ('treatment', 'created_at',)
        unique_together = ('treatment', 'lang')
