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
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from ..constants import SurveyStrings


class NameForm(forms.Form):
    your_name = forms.CharField(label='Your name', max_length=100)


class CustomChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return mark_safe("<img src='{}'/>".format(obj.itemImage.url))


def validate_question_one(value):
    if value != 120:
        raise ValidationError(
            _('The answer is not correct.'),
        )


class TestForm(forms.Form):
    """
    This is an example of test from, You should modify the questions here to
    create the comprehension test that the participants on the experiment will have.
    In future versions, we plan to make this test dynamic and to enable to possibility
    to select which test will be associated to each treatment and experiment form
    the admin view.
    """
    question_one = forms.IntegerField(label=_(
        'How many EMUs need to be in the Public Account in order for you to be sure to keep the rest?'),
        validators=[validate_question_one])
    # Add more questions here!
