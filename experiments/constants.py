from django.utils.translation import ugettext_lazy as _


class Constants(object):
    # Experiments
    UNFINISHED = 0
    COMPLETED = 1
    EXPERIMENT_STATUS = (
        (UNFINISHED, _('unfinished')),
        (COMPLETED, _('completed')),
    )

    # Game
    PRISONERS_DILEMMA = 'PD'
    PUBLIC_GOODS_GAME = 'PGG'
    SNOW_DRIFT = 'SD'
    STAG_HUNT = 'SH'
    COLLECTIVE_RISK = 'CR'
    GAME_CHOICES = (
        (PRISONERS_DILEMMA, 'Prisoners\' Dilemma'),
        (PUBLIC_GOODS_GAME, 'Public Goods Game'),
        (SNOW_DRIFT, 'Snow Drift'),
        (STAG_HUNT, 'Stag Hunt'),
        (COLLECTIVE_RISK, 'Collective RIsk'),
    )

    # Topologies
    NONE = 'None'
    GROUP = 'Group'
    GRID = 'GD'
    TORUS = 'TR'
    RANDOM_NETWORK = 'RN'
    SMALL_WORLD = 'SW'
    SCALE_FREE = 'SF'
    TOPOLOGY_CHOICES = (
        (NONE, _('No Topology')),
        (GROUP, _('Group game')),
        (GRID, 'GRID'),
        (TORUS, 'Torus'),
        (RANDOM_NETWORK, 'Random Network'),
        (SMALL_WORLD, 'Small World Network'),
        (SCALE_FREE, 'Scale Free Network'),
    )

    # Random distributions
    UNIFORM = 'UN'
    NORMAL = 'NR'
    DISTRIBUTION_CHOICES = (
        (UNIFORM, _('uniform distribution')),
        (NORMAL, _('normal distribution')),
    )

    ACTION1 = 0
    ACTION2 = 2
    ACTION3 = 4
    CRD_VALID_ACTIONS = (
        (ACTION1, _('0 EMUs')),
        (ACTION2, _('2 EMUs')),
        (ACTION3, _('4 EMUs'))
    )

    ENDOWMENT = 40

    MONITOR_S2 = "monitorS2"  # defines name of the queue for going to state S2
    MONITOR_S3 = "monitorS3"  # defines the name of the queue for going to state S3
    MONITOR_S4 = "monitorS4"  # defines the name of the queue for going to state S4

    GENDER_MALE = 'M'
    GENDER_FERMALE = 'F'
    GENDER_OTHER = 'O'
    GENDERS = (
        (GENDER_MALE, _('Male')),
        (GENDER_FERMALE, _('Female')),
        (GENDER_OTHER, _('Other'))
    )

    STATE_INACTIVE = 'INACTIVE'
    STATE_LOGIN = 'LOGIN'
    STATE_INSTRUCTIONS = 'INST'
    STATE_TEST = 'TEST'
    STATE_GAME_S1 = 'GAMES1'
    STATE_GAME_S2 = 'GAMES2'
    STATE_GAME_S3 = 'GAMES3'
    STATE_GAME_S4 = "GAMES4"
    STATE_QUIZ = 'QUIZ'
    STATE_FINISH = 'END'
    STATE_WAIT = 'WAIT'
    EXPERIMENT_STATES = (
        (STATE_INACTIVE, _('Inactive')),
        (STATE_LOGIN, _('Login')),
        (STATE_INSTRUCTIONS, _('Instructions')),
        (STATE_TEST, _('Test')),
        (STATE_GAME_S1, _('Game wait (S1)')),
        (STATE_GAME_S2, _('Game select action (S2)')),
        (STATE_GAME_S3, _('Game view result (S3)')),
        (STATE_GAME_S4, _('Game check threshold (S4)')),
        (STATE_QUIZ, _('Quiz')),
        (STATE_FINISH, _('End of the experiment')),
        (STATE_WAIT, _('Waiting for the other players...')),
    )
    STATE_TRANSITION_S2 = 'TRANS2'
    STATE_TRANSITION_S3 = 'TRANS3'
    STATE_NO_TRANSITION = 'NOTRANS'
    STATE_TRANSITION_S4 = 'TRANS4'
    TRANSITION_STATES = (
        (STATE_TRANSITION_S2, _('Transition Game')),
        (STATE_TRANSITION_S3, _('Transition Prediction')),
        (STATE_TRANSITION_S4, _('Transition Risk')),
        (STATE_NO_TRANSITION, _('Not in a transition')),
    )
    PREDICT_PUBLIC_ACCOUNT = _('Please, estimate the current total content of the public account')

    LOSS = 0
    NLOSS = 1
    ACK = 2
    THRESHOLD_STATES = (
        (LOSS, _('Threshold not met and loss')),
        (NLOSS, _('Threshold not met, but no loss')),
        (ACK, _('Threshold met'))
    )


class SurveyStrings(object):
    YES = True
    NO = False
    YES_NO_CHOICE = (
        (YES, _('Yes')),
        (NO, _('No')),
    )
    GENDER_MASC = 'Male'
    GENDER_FEM = 'Female'
    GENDER_INDEF = 'Undefined'
    GENDER_CHOICES = (
        (GENDER_MASC, _('Male')),
        (GENDER_FEM, _('Female')),
        (GENDER_INDEF, _('Undefined')),
    )
    GENDER_QUESTION = _('Please, select your gender')
    AGE_QUESTION = _('Enter your age')
    STUDIES_QUESTION = _('Indicate your level of studies (e.g. master)')
    DEGREE_QUESTION = _('Indicate your field of studies (e.g. Chemistry)')
    PROFESSION_QUESTION = _('Indicate your current profession (e.g. Student)')
    GAME_THEORY_QUESTION = _('Do you have any previous knowledge of Game Theory?')
    WHICH_GAME_QUESTION = _('Do you know which game have you played in this experiment?')
    WHICH_GAME_ELABORATE = _(
        'If you answered yes on the previous question, please describe in a few sentences the game you have played.')
    EXPECTATION_QUESTION = _('How did you expect the game would end and why?')
    INFORMATION_QUESTION = _(
        'Did the information about the actions of other players influence your decisions? If yes, in which way?')
    RISK_QUESTION = _('Did the risk of losing all your EMUs influence your decisions? In which way?')
    CONTRIBUTION_QUESTION = _(
        'Did you expect the other players to contribute more? If not, did you expect them to contribute less? '
        'Explain briefly your answer?')
    FAIRNESS_QUESTION = _(
        'Did you consider fairness in your decisions? Or did you only try to keep as much as possible?')

    LEVEL_STUDIES_CHOICE = (
        ('high school', _('high school')),
        ('bachelor', _('bachelor')),
        ('master', _('master')),
        ('PhD', _('PhD')),
        ('postdoctoral', _('postdoctoral')),
        ('other', _('other')),
    )

    STUDIES_CHOICE = (
        ('Economy', _('Economy')),
        ('Psychology', _('Psychology')),
        ('Computer Science', _('Computer Science')),
        ('Engineering', _('Engineering')),
        ('Languages', _('Languages')),
        ('Physics', _('Physics')),
        ('Chemistry', _('Chemistry')),
        ('Biology', _('Biology')),
        ('Bio-informatics', _('Bio-informatics')),
        ('Mathematics', _('Mathematics')),
        ('Social Sciences', _('Social Sciences')),
        ('Other', _('Other')),
    )

    PROFESSION_CHOICE = (
        ('student', _('student')),
        ('researcher', _('researcher')),
        ('professor', _('professor')),
        ('employee', _('employee')),
        ('other', _('other')),
    )

    GAME_DURATION_QUESTION = _(
        'Did you expect the experiment to last longer or shorter that it did? How did it affect your decisions?')
    KNOW_EXPERIMENTS_QUESTION = _('How did you get to know about our Experiments?')
    SUGGESTIONS_QUESTION = _('Do you have any suggestions or comments about the experiment?')
