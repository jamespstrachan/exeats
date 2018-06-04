import datetime
import csv
import hashlib

from django.shortcuts import render
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import Tutor, Slot, Student

def home(request):
    return render(request, 'exeatsapp/home.html')

# todo - do we need to exempt this still or could we add a token to the login form?
@csrf_exempt
def login(request):
    context = {}
    if request.method == 'POST':
        try:
            tutor = Tutor.objects.get(email=request.POST['__email'])
            if tutor.password == request.POST['__password']:
                request.session['tutor_id'] = tutor.id;
                request.session['tutor_email'] = tutor.email;
                return HttpResponseRedirect(reverse('exeatsapp:home'))
        except Tutor.DoesNotExist:
            pass
        context['login_failed'] = True;
    return render(request, 'exeatsapp/login.html', context)


def logout(request):
    del request.session['tutor_id'];
    del request.session['tutor_email'];
    return render(request, 'exeatsapp/logout.html')

def login_required(view):
    def wrap(request, *args, **kwargs):
        if request.session.get('tutor_id', False):
            return view(request, *args, **kwargs)
        return HttpResponseRedirect(reverse('exeatsapp:login'))
    return wrap

@login_required
def times(request):
    tutor_id = request.session.get('tutor_id')
    if request.method == 'POST':
        if request.POST.get('startingAt', False):
            start = datetime.datetime.strptime(request.POST['startingAt'], "%d/%m/%y %H:%M")
            start = timezone.make_aware(start)
            if request.POST.get('endingAt', False):
                end = datetime.datetime.strptime(request.POST['endingAt'], "%d/%m/%y %H:%M")
                end = timezone.make_aware(end)
            else:
                end = start
            duration = request.POST.get('duration', 10)
            duration = duration if duration else 10
            tutor = Tutor.objects.get(id=tutor_id)

            first = True
            while first or start < end:
                first = False
                slot = Slot.objects.create(start=start, location=request.POST['location'], tutor=tutor)
                slot.save()
                start += datetime.timedelta(minutes=int(duration))

        if request.POST.get('submitted', False) == 'currentTimes':
            slot_ids = [k[5:] for k,v in request.POST.items() if k[0:5] == 'slot_']
            slots = Slot.objects.filter(id__in=slot_ids, tutor=tutor_id)
            slots.delete()

        return HttpResponseRedirect(reverse('exeatsapp:times'))

    midnight_today = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
    suggested_time = midnight_today + datetime.timedelta(hours=33)  # 9am tomorrow morning
    context = {
        'suggested_slot': suggested_time,
        'slots': Slot.objects.filter(tutor=tutor_id, start__gte=datetime.datetime.now()).order_by('start')
    }

    return render(request, 'exeatsapp/times.html', context)


@login_required
def students(request):
    tutor_id = request.session.get('tutor_id')
    if request.method == 'POST':
        csv_string = request.POST.get('csvText', False)
        if csv_string:
            tutor = Tutor.objects.get(id=tutor_id)
            for line in csv_string.split('\n'):
                details = list(map(str.strip, line.split(',')))
                if len(details) == 3:
                    name = f'{details[1]} {details[0]}'
                    email = details[2]
                else:
                    name = details[0]
                    email = details[1]
                email = email if '@' in email else f'{email}@cam.ac.uk'
                student = Student.objects.create(name=name, email=email, tutor=tutor)
                student.save()

        if request.POST.get('submitted', False) == 'students':
            student_ids = [k[8:] for k,v in request.POST.items() if k[0:8] == 'student_']
            students = Student.objects.filter(id__in=student_ids, tutor=tutor_id)
            students.delete()

        return HttpResponseRedirect(reverse('exeatsapp:students'))

    context = {
        'students': Student.objects.filter(tutor=tutor_id).order_by('name')
    }
    return render(request, 'exeatsapp/students.html', context)



def get_student_for_hash(hash):
    student_id, _ = hash.split('-')
    student = Student.objects.get(id=student_id)
    return student if hash == get_hash_for_student(student) else None


def get_hash_for_student(student):
    salt = 'zzov5!5!2onxl'
    cleartext = salt + student.email
    return str(student.id) + '-' + hashlib.md5(cleartext.encode('utf-8')).hexdigest()[0:12]


def get_url_for_student(student):
    hash = get_hash_for_student(student)
    return settings.BASE_URL + reverse('exeatsapp:signup', kwargs={'hash': hash})


@login_required
def emails(request):
    tutor_id = request.session.get('tutor_id')
    tutor = Tutor.objects.get(id=tutor_id)
    if request.method == 'POST':
        body = request.POST.get('emailBody', False)
        student_ids = [k[8:] for k,v in request.POST.items() if k[0:8] == 'student_']
        students = Student.objects.filter(id__in=student_ids, tutor=tutor_id)

        subject = 'Terminal exeat signup'
        for student in students:
            to_email = 'jamespstrachan@gmail.com' # student.email
            body = body.replace('[link]', get_url_for_student(student))
            email = EmailMessage(subject, body, f'{settings.SYSTEM_FROM_NAME}<{settings.SYSTEM_FROM_EMAIL}>',
                                 [to_email], headers = {'Reply-To': tutor.email})
            email.send()
        return render(request, 'exeatsapp/emailsdelivered.html')

    context = {
        'students': Student.objects.filter(tutor=request.session['tutor_id']).order_by('name'),
        'tutor': tutor,
    }
    return render(request, 'exeatsapp/emails.html', context)


def signup(request, hash):
    student = get_student_for_hash(hash)
    if not student:
        raise Exception('link appears to be invalid')

    if request.method == 'POST':
        slot_id = [k[5:] for k,v in request.POST.items() if k[0:5] == 'slot_'][0]
        slot = Slot.objects.get(id=slot_id, tutor=student.tutor.id, allocatedto=None)
        if slot:
            # un-book any booked future slots
            existing_bookings = Slot.objects.filter(allocatedto=student.id, start__gte=datetime.datetime.now())
            for booking in existing_bookings:
                booking.allocatedto = None
                booking.save()
            # book chosen slot
            slot.allocatedto = student
            slot.save()
            subject  = 'Terminal exeat confirmation'
            body     = render_to_string('exeatsapp/emailconfirmation.html', {'slot': slot, 'url': get_url_for_student(student)})
            to_email = 'jamespstrachan@gmail.com' # student.email
            email = EmailMessage(subject, body, f'{settings.SYSTEM_FROM_NAME}<{settings.SYSTEM_FROM_EMAIL}>',
                                 [to_email])
            email.send()
        else:
            raise Exception('slot not found')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    context = {
        'slots': Slot.objects.filter(tutor=student.tutor.id, start__gte=datetime.datetime.now()).order_by('start')
    }
    return render(request, 'exeatsapp/signup.html', context)

@login_required
def view(request):
    midnight = datetime.datetime.combine(datetime.datetime.today(), datetime.time.min)
    context = {
        'slots': Slot.objects.filter(tutor=request.session['tutor_id'], start__gte=midnight).order_by('start')
    }
    return render(request, 'exeatsapp/view.html', context)


@login_required
def history(request):
    context = {
        'slots': Slot.objects.filter(tutor=request.session['tutor_id'], start__lte=datetime.datetime.now()).order_by('-start')
    }
    return render(request, 'exeatsapp/history.html', context)
