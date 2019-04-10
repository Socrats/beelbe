from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from experiments.utils import export_as_csv
# Register your models here.
from .models import (
    Player, Experiment, Session, RunNow, Treatment, Game,
    CollectiveRiskGame, Survey, Profile, RequestMonitor, Group, GameData, EndProbability, Instruction,
)

admin.site.register(Profile, admin.ModelAdmin)
admin.site.register(Game, admin.ModelAdmin)
# admin.site.register(CollectiveRiskGame, admin.ModelAdmin)
admin.site.register(RunNow, admin.ModelAdmin)
admin.site.register(Group, admin.ModelAdmin)
admin.site.register(EndProbability, admin.ModelAdmin)


# Define filters
class ExperimentFilter(admin.SimpleListFilter):
    title = 'experiment'
    parameter_name = 'experiment'

    def lookups(self, request, model_admin):
        experiments = set([c.player.experiment for c in model_admin.model.objects.all()])
        return [(c.id, c.experiment_name) for c in experiments]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(player__experiment=self.value())
        else:
            return queryset


class SessionFilter(admin.SimpleListFilter):
    title = _('session')
    parameter_name = 'session'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        return [(c[0],
                 "{}|s{}".format(c[1], c[2])) for c
                in qs.order_by('player__session__treatment__treatment_name', 'player__session__session_number')
                    .values_list('player__session', 'player__session__treatment__treatment_name',
                                 'player__session__session_number').distinct()]

    def queryset(self, request, queryset):
        if self.value():
            print(self.value())
            return queryset.filter(player__session=self.value())
        else:
            return queryset


class GroupFilter(admin.SimpleListFilter):
    title = _('group')
    parameter_name = 'group'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        return [(i, i) for i in qs.order_by('player__group__group_number').values_list('player__group__group_number',
                                                                                       flat=True).distinct()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(player__group__group_number=self.value())
        else:
            return queryset


class GameDataAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'game_round', 'group_number', 'session', 'action', 'private_account', 'public_account',
        'prediction')
    list_filter = [ExperimentFilter, SessionFilter, GroupFilter, 'round', 'player']
    search_fields = ['session', 'group', 'round', 'action', 'prediction_question']
    ordering = ('session', 'round', 'group',)
    actions = [export_as_csv()]

    can_delete = False

    def username(self, obj):
        return obj.player.user.username

    username.short_description = 'username'

    def game_round(self, obj):
        return obj.round

    game_round.short_description = 'round'

    def prediction(self, obj):
        return obj.prediction_question

    prediction.short_description = 'prediction'

    def group_number(self, obj):
        return obj.group.group_number

    group_number.short_description = 'group'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Meta:
        verbose_name_plural = 'game data'


admin.site.register(GameData, GameDataAdmin)


class RequestMonitorAdmin(admin.ModelAdmin):
    fields = ('name', 'var', 'condition', 'group', 'queue')

    def session(self, obj):
        return obj.group.session

    def experiment(self, obj):
        return obj.group.session.experiment

    list_display = ('experiment', 'session', 'group', 'name', 'var', 'condition',)
    list_filter = ['group', 'name']
    search_fields = ['name', 'group']


admin.site.register(RequestMonitor, RequestMonitorAdmin)


class InstructionAdmin(admin.ModelAdmin):
    fields = ('treatment', 'text', 'lang')
    actions = [export_as_csv()]

    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        if not change:
            obj.created_by = request.user
        obj.save()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            instance.modified_by = request.user
            if not change:
                instance.created_by = request.user
            instance.save()
        formset.save_m2m()


admin.site.register(Instruction, InstructionAdmin)


class InstructionInline(admin.StackedInline):
    model = Instruction
    extra = 0
    classes = ['collapse']
    fieldsets = [
        (None, {'fields': ['lang', 'text']}
         ),
    ]


class SurveyInline(admin.StackedInline):
    model = Survey
    extra = 0
    classes = ['collapse']
    fieldsets = [
        (None,
         {'fields': ['player', 'gender', 'age', 'level_studies', 'degree_question', 'profession']}),
        ('Questions', {'fields': ['game_theory_question', 'which_game', 'which_game_text', 'expect_game_end_text',
                                  'information_question', 'risk_question', 'contribution_question',
                                  'fairness_question', 'game_duration_question', 'know_experiments_question',
                                  'suggestion_question'],
                       'classes': ['collapse']}),
    ]
    can_delete = False
    verbose_name_plural = 'Survey'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class GameDataInLine(admin.TabularInline):
    model = GameData
    extra = 0
    classes = ['collapse']
    fields = (
        'round', 'action', 'private_account', 'public_account', 'time_elapsed',
        'prediction_question', 'time_question_elapsed')
    ordering = ('round',)
    fk_name = "opponent"
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Meta:
        verbose_name_plural = 'Game Data'


class ProfileInLine(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'player'
    classes = ['collapse']
    fieldsets = [
        (None, {'fields': ['private_account', 'last_round', 'experiment_state', 'threshold_state', 'language']}),
        ('Advanced',
         {'fields': ['time_start_experiment', 'time_ends_experiment', 'finished', 'participated', 'created'],
          'classes': ['collapse']}),
    ]
    readonly_fields = ('created',)


class PlayerAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['user', 'experiment', 'session', 'group']}),
    ]
    inlines = [ProfileInLine, GameDataInLine, SurveyInline, ]

    list_display = ('user', 'experiment', 'session', 'group',)
    list_filter = ['experiment', 'session', ]
    search_fields = ['experiment', 'session', ]


admin.site.register(Player, PlayerAdmin)


class PlayerInLine(admin.TabularInline):
    model = Player
    extra = 0
    classes = ['collapse']
    fields = ('user', 'group', 'user_is_active', 'see_more')
    readonly_fields = ('user_is_active', 'see_more')
    ordering = ('group', 'user',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        field = super(PlayerInLine, self).formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == 'group':
            if request._obj_ is not None:
                field.queryset = field.queryset.filter(session=request._obj_)
            else:
                field.queryset = field.queryset.none()

        return field

    def user_is_active(self, obj):
        if obj.user.is_active:
            return mark_safe("<span style='color:green;'>{}</span>".format(obj.user.is_active))
        else:
            return mark_safe("<span style='color:tomato;'>{}</span>".format(obj.user.is_active))

    def see_more(self, obj):
        return mark_safe('<a href="{}">edit</a>'.format(reverse('admin:experiments_player_change',
                                                                args=(obj.pk,))))


class SessionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['session_number', 'session_metadata', 'scheduled_date']}),
        ('Experiment info', {'fields': ['experiment', 'treatment']}),
        ('Advanced', {'fields': ['time_start', 'time_finish', 'finished', 'structure_assigned', 'group_size'],
                      'classes': ['collapse']}),
    ]
    inlines = [PlayerInLine, ]

    list_display = ('session_number', 'experiment', 'treatment', 'scheduled_date', 'finished',)
    list_filter = ['experiment', 'treatment', ]
    search_fields = ['treatment__treatment_name', 'experiment__experiment_name']
    actions = [export_as_csv()]

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(SessionAdmin, self).get_form(request, obj, **kwargs)


admin.site.register(Session, SessionAdmin)


class SessionInLine(admin.TabularInline):
    model = Session
    extra = 0
    classes = ['collapse']
    fieldsets = [
        (None, {'fields': ['experiment', 'treatment', 'session_number', 'session_metadata', 'scheduled_date']}),
        ('Advanced', {'fields': ['group_size', 'change_link', 'monitor_session_link'],
                      'classes': ['collapse']}),
    ]
    readonly_fields = ('change_link', 'monitor_session_link',)
    ordering = ('session_number', 'treatment',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        field = super(SessionInLine, self).formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == 'treatment':
            if request._obj_ is not None:
                field.queryset = field.queryset.filter(experiment=request._obj_)
            else:
                field.queryset = field.queryset.none()
        elif db_field.name == 'experiment':
            if request._obj_ is not None:
                field.queryset = field.queryset.filter(id=request._obj_.id)
            else:
                field.queryset = field.queryset.none()

        return field

    def change_link(self, obj):
        return mark_safe('<a href="{}">edit</a>'.format(reverse('admin:experiments_session_change',
                                                                args=(obj.id,))))

    def monitor_session_link(self, obj):
        return mark_safe('<a href="{}">monitor session</a>'.format(reverse('experiments:admin')))


class TreatmentAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['treatment_name', 'treatment_metadata']}),
        ('Experiment', {'fields': ['experiment'], 'classes': ['collapse']}),
        ('Game', {'fields': ['game']}),
    ]
    inlines = [InstructionInline, SessionInLine, ]

    list_display = ('treatment_name', 'experiment', 'game',)
    list_filter = ['experiment', 'game', 'experiment__experiment_status']
    search_fields = ['treatment_name', 'experiment__experiment_name', 'game__game_name']

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj.experiment
        return super(TreatmentAdmin, self).get_form(request, obj, **kwargs)


admin.site.register(Treatment, TreatmentAdmin)


class TreatmentInLine(admin.TabularInline):
    model = Treatment
    extra = 0
    classes = ['collapse']
    fields = ('treatment_name', 'treatment_metadata', 'game')
    ordering = ('game',)


class ExperimentAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['experiment_name', 'experiment_metadata']}),
        ('Date information', {'fields': ['created', 'last_modified'], 'classes': ['collapse']}),
        ('Experiment status', {'fields': ['experiment_status'], 'classes': ['collapse']}),
    ]
    readonly_fields = ('created',)
    inlines = [TreatmentInLine, SessionInLine]

    list_display = ('experiment_name', 'experiment_metadata', 'created', 'last_modified', 'experiment_status',)
    list_filter = ['experiment_status', 'last_modified']
    search_fields = ['experiment_name']

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(ExperimentAdmin, self).get_form(request, obj, **kwargs)


admin.site.register(Experiment, ExperimentAdmin)


class SurveyAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,
         {'fields': ['experiment', 'session', 'player', 'gender', 'age', 'level_studies', 'profession']}),
        ('Questions', {'fields': ['game_theory_question', 'which_game', 'which_game_text', 'expect_game_end_text',
                                  'information_question', 'risk_question', 'contribution_question',
                                  'fairness_question', 'game_duration_question', 'know_experiments_question',
                                  'suggestion_question'],
                       'classes': ['collapse']}),
    ]
    readonly_fields = ('experiment', 'session', 'player')

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(SurveyAdmin, self).get_form(request, obj, **kwargs)

    def experiment(self, obj):
        return obj.player.experiment

    def treatment(self, obj):
        return obj.player.session.treatment.treatment_name

    def session(self, obj):
        return obj.player.session

    can_delete = False

    def username(self, obj):
        return obj.player.user.username

    username.short_description = 'username'

    def group_number(self, obj):
        return obj.player.group.group_number

    group_number.short_description = 'group'

    list_display = ('username', 'group_number', 'experiment', 'treatment', 'session',)
    list_filter = (ExperimentFilter, SessionFilter, 'gender', 'age', 'level_studies', 'profession',)
    search_fields = ['player__pk']
    actions = [export_as_csv()]


admin.site.register(Survey, SurveyAdmin)


class CollectiveRiskGameAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['game_uid', 'game_name', 'game_metadata']}),
        ('Game Info', {'fields': ['topology', 'num_players', 'is_using_emus', 'real_currency', 'conversion_rate'],
                       'classes': ['collapse']}),
        ('CRD Info', {'fields': ['group_size', 'endowment', 'rounds', 'threshold', 'risk_prob', 'valid_actions'],
                      'classes': ['collapse']}),
        ('Timing Uncertainty', {'fields': ['is_round_variable', 'min_round', 'termination_probability', 'dice_faces'],
                                'classes': ['collapse']}),
        ('Legacy Fields (deprecated)',
         {'fields': ['round_distribution', 'round_variance', 'distribution_steps', 'end_probabilities'],
          'classes': ['collapse']}),
    ]

    list_display = ('game_uid', 'game_name', 'risk_prob', 'is_round_variable',)
    list_filter = ['game_uid', 'is_round_variable']
    search_fields = ['game_uid']

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(CollectiveRiskGameAdmin, self).get_form(request, obj, **kwargs)


admin.site.register(CollectiveRiskGame, CollectiveRiskGameAdmin)
