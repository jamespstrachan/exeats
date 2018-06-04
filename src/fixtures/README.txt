Basic fixtures for a few companies and a superuser JS with password asdasdasd

 - trigger new dump: `python manage.py dumpdata --format yaml -o fixtures/basic_fixtures.yaml ommawebapp`
 - load into a fresh database with `python manage.py loaddata fixtures/basic_fixtures.yaml`
 - image assets are stored in `./assets` to match below fixtures they should be moved to `../uploads/transmissions/`

 todo - use json fixtures instead of yaml to avoid datetime timezone bug
        see https://code.djangoproject.com/ticket/18867
