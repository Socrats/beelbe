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

"""
This module provides helper functions to generate a pool of agents to:
1. Test through the web browser experiments in which multiple players are required.
2. Provide a framework for performing hybrid experiments
"""

import json
# Multi-processing
from multiprocessing import Pool

import numpy as np
import time
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse_lazy
from django.utils import timezone


def generate_workers(nb_workers, worker_params, worker_type='crd'):
    """
    This function creates a number of workers to perform a given task
    :param nb_workers:
    :param worker_params:
    :param worker_type:
    :return: None
    """
    if worker_type is 'crd':
        worker = crd_experiment_test_agent
    else:
        raise Exception("No worker specified")

    pool = Pool(processes=nb_workers)

    jobs = [pool.apply_async(worker, (value["username"], value["password"])) for key, value in worker_params.items()]
    results = [i.get() for i in jobs]

    if 1 in results:
        raise Exception("Some of the jobs did not terminate correctly!")

    pool.close()
    pool.join()


def crd_experiment_test_agent(username, password):
    """ perform the code you want to test here; it must be thread-safe
       (e.g., each thread must have its own Django test client)
    """
    UserModel = get_user_model()
    user = UserModel.objects.get(username='{}'.format(username))
    session_id = user.player.session_id
    login_url = '/en/experiments/login/'

    def test_ajax_wait(condition):
        while not condition:
            time.sleep(10 * np.random.rand())
            r = c.post(reverse_lazy('experiments:sync', kwargs={'session_id': session_id}))
            json_str = r.content.decode('utf8').replace("'", '"')
            json_data = json.loads(json_str)
            condition = json_data['can_continue']
        return condition

    if username is None:
        return

    c = Client(user=user)

    # First we check the login
    response = c.post(login_url,
                      {'username': ''.format(username), 'password': ''.format(password)})

    # Then we move through the windows until game
    response = c.get(reverse_lazy('experiments:test', kwargs={'session_id': session_id}))

    # Syncronize players before game
    response = c.get(reverse_lazy('experiments:results_round', kwargs={'session_id': session_id}))
    can_continue = response.context['can_continue']
    if not can_continue:
        can_continue = test_ajax_wait(can_continue)

    # The while is needed to take into account redirections due to db errors
    finished_game = False
    while not finished_game:
        move_next = False
        while not move_next:
            # game starts
            response = c.get(reverse_lazy('experiments:game', kwargs={'session_id': session_id}))

            time_now = timezone.now()
            elapsed = time_now - time_now
            response = c.post(reverse_lazy('experiments:game_round', kwargs={'session_id': session_id}),
                              {
                                  'time_round_start': time_now,
                                  'time_round_end': time_now,
                                  'time_elapsed': elapsed,
                                  'action': '{}'.format(np.random.choice([0, 2, 4], size=1))
                              }
                              )
            if response.status_code == 200:
                move_next = True

        can_continue = response.context['can_continue']
        if not can_continue:
            can_continue = test_ajax_wait(can_continue)

        # The while is needed to take into account redirections due to db errors
        move_next = False
        while not move_next:
            # Get results page
            response = c.get(reverse_lazy('experiments:results', kwargs={'session_id': session_id}))
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

        can_continue = response.context['can_continue']
        if not can_continue:
            can_continue = test_ajax_wait(can_continue)

    response = c.get(reverse_lazy("experiments:results_risk_wait", kwargs={'session_id': session_id}))
    can_continue = response.context['can_continue']
    if not can_continue:
        can_continue = test_ajax_wait(can_continue)

    # check that risk page works
    response = c.post(reverse_lazy('experiments:results_risk', kwargs={'session_id': session_id}))
