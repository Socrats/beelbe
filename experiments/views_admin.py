from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.generic.edit import FormView

from .forms import RunNowForm
from .models import (
    Experiment, RunNow, Player, Session, Group, CollectiveRiskGame, GameData,
)


class BaseAdminExperimentView(generic.TemplateView):
    """
    Base view for admindocs views.
    """

    @method_decorator(staff_member_required(login_url=reverse_lazy('experiments:login_admin')))
    def dispatch(self, request, *args, **kwargs):
        # Put contition specific to experiments admin
        return super(BaseAdminExperimentView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs.update({'root_path': reverse('experiments:admin')})
        kwargs.update({'is_popup': False})
        kwargs.update({'user': self.request.user})
        kwargs.update({'has_permission': True})
        # kwargs.update(admin.site.each_context(self.request))
        # create method that adds context variables needed for all experiments admin pages
        return super(BaseAdminExperimentView, self).get_context_data(**kwargs)


class ExperimentsAdminView(BaseAdminExperimentView, FormView):
    template_name = 'experiments/admin/index.html'
    form_class = RunNowForm
    success_url = reverse_lazy('experiments:admin')

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ExperimentsAdminView, self).get_context_data(**kwargs)
        # Add in the publisher
        context['run_now'] = RunNow.objects.all()[0]
        # Get players for current experiment
        run_now = RunNow.objects.all()[0]
        experiment = Experiment.objects.get(pk=run_now.experiment_id)
        session = Session.objects.get(pk=run_now.session_id)
        players = Player.objects.filter(experiment=experiment, session=session, user__is_active=True)
        context['players'] = players
        context['session'] = session
        context['title'] = 'Experiments admin'
        return context

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        form.save()
        return super(ExperimentsAdminView, self).form_valid(form)

    def get_form(self, form_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        if form_class is None:
            form_class = self.get_form_class()
        run_now = RunNow.objects.all()[0]
        return form_class(**self.get_form_kwargs(), instance=run_now)


class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    """

    def form_invalid(self, form):
        response = super(AjaxableResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        else:
            return response

    def form_valid(self, form):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super(AjaxableResponseMixin, self).form_valid(form)
        if self.request.is_ajax():
            data = {
                'pk': self.object.pk,
            }
            return JsonResponse(data)
        else:
            return response


class SessionGameView(BaseAdminExperimentView):
    template_name = 'experiments/admin/monitor.html'
    context_object_name = 'groups'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SessionGameView, self).get_context_data(**kwargs)
        # Add in the publisher
        context['run_now'] = RunNow.objects.all()[0]
        # Get players for current experiment session
        run_now = RunNow.objects.all()[0]
        experiment = Experiment.objects.get(pk=run_now.experiment_id)
        session = Session.objects.get(pk=run_now.session_id)
        context['experiment'] = experiment
        context['session'] = session
        players = Player.objects.filter(experiment=experiment, session=session, user__is_active=True)
        context['players'] = players
        # Get groups for current session
        groups = Group.objects.filter(session=session).order_by('group_number')
        # for group in groups:
        #     group.members = group.members.filter(user__is_active=True)
        context['groups'] = groups
        context['threshold'] = CollectiveRiskGame.objects.get(id=session.treatment.game.id).threshold
        context['title'] = 'Monitor session'
        context['deadline_variable'] = CollectiveRiskGame.objects.get(id=session.treatment.game.id).is_round_variable
        return context


class GraphView(SessionGameView):
    template_name = 'experiments/admin/visualize_session.html'
    context_object_name = 'groups'


def fetch_session_data(request):
    """
    First checks whether we have the correct admin permissions,
    then returns the data of the session in json format.
    :param request:
    :return:
    """
    # get resource value
    group_number = request.GET.get('group_number', 0)

    # get current session
    run_now = RunNow.objects.all()[0]
    experiment = Experiment.objects.get(pk=run_now.experiment_id)
    session = Session.objects.get(pk=run_now.session_id)
    game_data = GameData.objects.filter(session=session).order_by('round')

    # prepare game data as json
    data = {
        'game_data': list(game_data.values()),
    }
    return JsonResponse(data)
