# coding=utf-8
# ==============================================================================
# BEELPlatform
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


class AbstractAgent:
    """
    This class works as interface for the other agents.
    """

    def play(self):
        pass

    def update(self, environment):
        pass

    def __str__(self):
        return "[WARNING] Abstract Agent: this object" \
               "has no function by itself. Works as interface for the other agents"


class TwoPDAgent(AbstractAgent):

    def __init__(self):
        pass

    def play(self):
        pass

    def update(self, environment):
        pass

    def __str__(self):
        pass
