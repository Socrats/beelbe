# beelbe
Platform for behavioural experiments

## Installation
This project is implemented as a Django plug-in.

To install, add it to your INSTALLED_APPS on your settings.py
Afterwards, you should create a .env file where you should write the
SECRET_KEY for Django and your database credentials.

> If you want to create a survey that will show up at the end of the experiments you should modify
the Survey model in experiments/models.py

Then, run on a terminal the following:

```.bash
python manage.py makemigrations
python manage.py migrate
python manage.py compilemessages
``` 

This will populate your database with the tables of the experiment module and compile the translation files.

Finally, create a super user to be able to access the admin website:

```.bash
python manage.py createsuperuser
``` 

With this you should be able to access the admin website and generate your experiment with:

```.bash
python manage.py runserver 0.0.0.0:8000
``` 

This will start your server on IP 0.0.0.0 and port 8000. Now, you can go to your browser and access the admin interface:

```.bash
http://0.0.0.0:8000/admin
``` 