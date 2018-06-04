# Usage:
#   Build image:   docker build -t djangoapp .
#   Run image:     docker run -ti --name djangoapp -v "$(pwd)":/app -p 80:80 --rm djangoapp

FROM python:3.6.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        vim \
        nginx \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . .

# remove nginx's default config, add ours and symlink it as 'available'
RUN rm /etc/nginx/sites-enabled/default
RUN cp django-nginx.conf /etc/nginx/sites-available/django-nginx.conf
RUN ln -s /etc/nginx/sites-available/django-nginx.conf /etc/nginx/sites-enabled/django-nginx.conf

# move supervisor config file into place
RUN cp supervisor.conf /etc/supervisor/conf.d/supervisor.conf

# collect static files from django app into main /static dir
#RUN python src/manage.py collectstatic --no-input

# Expose port 80 for production server and 81 for django's dev runserver
EXPOSE 80 81
CMD ["supervisord", "-n"]
