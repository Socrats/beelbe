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

from django.conf.urls import url, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from experiments.forms import ExperimentsAuthenticationForm
from . import (
    views, views_admin,
)

app_name = 'experiments'
urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name='experiments:login', permanent=False)),
    url(r'^login/$', views.ExperimentsLogin.as_view(authentication_form=ExperimentsAuthenticationForm), name='login'),
    url(r'^instructions/$', views.InstructionsView.as_view(), name='instructions'),
    url(r'^(?P<session_id>[0-9]+)/test/$', views.TestView.as_view(), name='test'),
    url(r'^(?P<session_id>[0-9]+)/game/$', views.game_view, name='game'),
    url(r'^(?P<session_id>[0-9]+)/results/round/$', views.finish_round_view, name='game_round'),
    url(r'^(?P<session_id>[0-9]+)/results/$', views.results_view, name='results'),
    url(r'^(?P<session_id>[0-9]+)/game/round/$', views.finish_results_view, name='results_round'),
    url(r'^(?P<session_id>[0-9]+)/results/risk_check/wait$', views.transition_risk, name='results_risk_wait'),
    url(r'^(?P<session_id>[0-9]+)/results/risk_check/$', views.check_threshold_view, name='results_risk'),
    url(r'^(?P<session_id>[0-9]+)/userinfo/$', views.UserInfoView.as_view(), name='userinfo'),
    url(r'^(?P<session_id>[0-9]+)/thanks/$', views.ThanksView.as_view(), name='thanks'),
    url(r'^(?P<session_id>[0-9]+)/wait-sync/$', views.sync_view, name='sync'),
    url(r'^logout/$', auth_views.LogoutView.as_view(next_page='experiments:login'), name='logout'),
    url(r'^i18n/', include('django.conf.urls.i18n'), name='set_language'),
    # admin part
    url(r'^monitor/login$', auth_views.LoginView.as_view(), name='login_admin'),
    url(r'^monitor/$', views_admin.ExperimentsAdminView.as_view(), name='admin'),
    url(r'^monitor/(?P<session_id>[0-9]+)/$', views_admin.SessionGameView.as_view(), name='monitor'),
    url(r'^monitor/(?P<session_id>[0-9]+)/graph/$', views_admin.GraphView.as_view(), name='monitor_graph'),
    url(r'^monitor/ajax/$', views_admin.fetch_session_data, name='fetch_data'),
]
