# coding=utf-8
# ==============================================================================
# EvoSim
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

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from .constants import SurveyStrings
from .models import RunNow, Survey, Session


class UserInfoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserInfoForm, self).__init__(*args, **kwargs)
        self.fields['age'].required = True
        self.fields['which_game'].required = True
        self.fields['expect_game_end_text'].required = True
        self.fields['information_question'].required = True
        self.fields['risk_question'].required = True
        self.fields['contribution_question'].required = True
        self.fields['fairness_question'].required = True
        self.fields['game_duration_question'].required = True
        self.fields['know_experiments_question'].required = True

    class Meta:
        model = Survey
        exclude = ('player',)
        widgets = {
            'which_game_text': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
            'expect_game_end_text': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
            'information_question': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
            'risk_question': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
            'contribution_question': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
            'fairness_question': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
            'game_duration_question': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
            'know_experiments_question': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
            'suggestion_question': forms.Textarea(attrs={'rows': 3, 'cols': 100, 'style': 'max-width: 100%;'}),
        }


class NameForm(forms.Form):
    your_name = forms.CharField(label='Your name', max_length=100)


class CustomChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return mark_safe("<img src='{}'/>".format(obj.itemImage.url))


class ExperimentsAuthenticationForm(AuthenticationForm):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(username=username, password=password, request=self.request, dummy=None)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class RunNowForm(forms.ModelForm):
    error_messages = {
        'invalid_session': _(
            "Session with id %(session_id)s does not exist, please enter a valid session."
        ),
    }

    class Meta:
        model = RunNow
        fields = ['experiment_id', 'treatment_id', 'session_id', 'experiment_on']

    def clean(self):
        data = self.cleaned_data
        try:
            session = Session.objects.get(id=data.get('session_id'),
                                          experiment__id=data.get('experiment_id'),
                                          treatment__id=data.get('treatment_id')
                                          )
        except Session.DoesNotExist:
            raise forms.ValidationError(
                self.error_messages["invalid_session"],
                code='invalid_session',
                params={'session_id': data.get('session_id')}
            )
