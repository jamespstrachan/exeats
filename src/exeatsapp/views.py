import datetime
import hashlib
import hmac
import subprocess
import re
import http
import json
import smtplib
from email.mime.text import MIMEText
from statistics import mode, median, StatisticsError

from django.shortcuts import render
from django.template.loader import render_to_string
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, Http404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from django.db.models import Max, Q

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
                request.session['tutor_id'] = tutor.id
                request.session['tutor_email'] = tutor.email
                return HttpResponseRedirect(reverse('exeatsapp:home'))
        except Tutor.DoesNotExist:
            pass
        context['login_failed'] = True
    return render(request, 'exeatsapp/login.html', context)


def logout(request):
    del request.session['tutor_id']
    del request.session['tutor_email']
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
            duration = int(request.POST.get('duration', 10))
            duration = duration if duration >= 1 else 10
            tutor = Tutor.objects.get(id=tutor_id)

            first = True
            slot_count = 0
            while first or start < end:
                first = False
                slot = Slot.objects.create(start=start,
                                           location=request.POST['location'],
                                           tutor=tutor)
                slot.save()
                slot_count += 1
                start += datetime.timedelta(minutes=int(duration))

            message = '{} time slot{} added'.format(slot_count, '' if slot_count == 1 else 's')
            messages.add_message(request, messages.INFO, message)

        if request.POST.get('submitted', False) == 'currentTimes':
            slot_ids = [k[5:] for k, v in request.POST.items() if k[0:5] == 'slot_']
            slots = Slot.objects.filter(id__in=slot_ids, tutor=tutor_id)
            message = '{} time slot{} deleted'.format(len(slots), '' if len(slots) == 1 else 's')
            messages.add_message(request, messages.INFO, message)
            slots.delete()

        return HttpResponseRedirect(reverse('exeatsapp:times'))

    midnight_today = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
    suggested_start = midnight_today + datetime.timedelta(hours=33)  # 9am tomorrow morning

    latest_slot = Slot.objects.filter(tutor=tutor_id).order_by('-start').first()
    suggested_location = latest_slot.location if latest_slot else ''

    if latest_slot:  # meaning if they have at least one slot
        last_50_slot_times = Slot.objects.filter(tutor=tutor_id) \
                                 .order_by('-start') \
                                 .values_list('start', flat=True)[0:50]
        minute_diffs = [(last_50_slot_times[i] - last_50_slot_times[i + 1]).total_seconds() / 60
                        for i in range(len(last_50_slot_times) - 1)]
        try:
            suggested_duration = int(mode(minute_diffs))
        except StatisticsError:  # if there's no unique most popular duration, use the middle one
            suggested_duration = int(median(minute_diffs))
    else:
        suggested_duration = 10

    context = {
        'suggested_start': suggested_start,
        'suggested_end': suggested_start + datetime.timedelta(hours=1),
        'suggested_location': suggested_location,
        'suggested_duration': suggested_duration,
        'slots': Slot.objects.filter(tutor=tutor_id, start__gte=get_midnight()).order_by('start')
    }

    return render(request, 'exeatsapp/times.html', context)


@login_required
def students(request):
    if request.method == 'POST':
        return update_students(request)

    tutor_id = request.session.get('tutor_id')
    context = {
        'students': Student.objects.filter(tutor=tutor_id).order_by('name'),
    }
    return render(request, 'exeatsapp/students.html', context)


def update_students(request):
    tutor_id = request.session.get('tutor_id')

    # handle addition of new students
    csv_string = request.POST.get('csvText', False)
    student_count = 0
    skipped_count = 0
    if csv_string:
        tutor = Tutor.objects.get(id=tutor_id)
        for (name, email) in parse_student_details(csv_string):
            email = email if '@' in email else '{}@cam.ac.uk'.format(email)
            if not Student.objects.filter(email=email):
                student = Student.objects.create(name=name, email=email, tutor=tutor)
                student_count += 1
                student.save()
            else:
                skipped_count += 1

        skipped_details = ', {} skipped as they have already been added'.format(skipped_count) \
                          if skipped_count else ''
        message = '{} student{} added{}'.format(student_count,
                                                '' if student_count == 1 else 's',
                                                skipped_details)
        messages.add_message(request, messages.INFO, message)

    # handle removal of existing students
    if request.POST.get('submitted', False) == 'students':
        student_ids = [k[8:] for k, v in request.POST.items() if k[0:8] == 'student_']
        students = Student.objects.filter(id__in=student_ids, tutor=tutor_id)
        students.delete()
        message = '{} student{} deleted'.format(len(student_ids),
                                                '' if len(student_ids) == 1 else 's')
        messages.add_message(request, messages.INFO, message)

    return HttpResponseRedirect(reverse('exeatsapp:students'))


def parse_student_details(raw_string):
    """ returns an array of (name, email) tuples from an input with format one of:
        1) 'Alice Smith<alice@smith.com>, Bob Smith<bob@smith.com>'
               (all one line, as produced by the student email list builder)
        2) 'Alice Smith, alice@smith.com
            Bob Smith, bob@smith.com'
        3) 'Smith, Alice, alice@smith.com
            Smith, Bob, bob@smith.com'
    """
    # Try to detect camsis export format


    # Try to detect 'Alice Smith<alice@smith.com>, Bob Smith<bob@smith.com>' format
    details = re.findall(r'\s*(?P<name>[^,\<\>]+?)\s*\<(?P<email>.+?@.+?)\>\s*', raw_string)
    if details:
        return details

    # Try to detect comma or tab separated formats
    # 'Alice Smith, alice@smith.com \n Bob Smith, bob@smith.com'
    details = []
    column_lookup = None
    for line in str.strip(raw_string).split('\n'):
        separator = '\t' if line[0:3] == '360' else ','
        parts = list(map(str.strip, line.split(separator)))

        if 'First Name - Pref/Prim' in parts:
            column_lookup = (
                parts.index('Last Name'),
                parts.index('First Name - Pref/Prim'),
                parts.index('CRSID')
            )
            continue

        if column_lookup:
            reordered_parts = (parts[i] for i in column_lookup)
            parts = list(reordered_parts)

        if len(parts) == 3:
            name = '{} {}'.format(parts[1], parts[0])
            email = parts[2]
        else:
            name = parts[0]
            email = parts[1]
        details.append((name, email))
    return details


def get_student_for_hash(hash):
    student_id, _ = hash.split('-')
    student = Student.objects.get(id=student_id)
    return student if hash == get_hash_for_student(student) else None


def get_hash_for_student(student):
    salt = 'zov5!5!2onxl'  # todo - move this into config and change value (at time when it won't matter that all old links failed)
    cleartext = salt + student.email
    return str(student.id) + '-' + hashlib.md5(cleartext.encode('utf-8')).hexdigest()[0:12]


def get_url_for_student(student):
    hash = get_hash_for_student(student)
    return settings.BASE_URL + reverse('exeatsapp:signup', kwargs={'hash': hash})


def is_mailgun():
    """ returns true if we are using mailgun as our smtp host """
    return 'mailgun' in settings.EMAIL_HOST


@login_required
def emails(request):
    tutor_id = request.session.get('tutor_id')
    tutor = Tutor.objects.get(id=tutor_id)
    if request.method == 'POST':
        body_template = request.POST.get('emailBody', False)
        student_ids   = [k[8:] for k, v in request.POST.items() if k[0:8] == 'student_']
        students      = Student.objects.filter(id__in=student_ids, tutor=tutor_id)

        subject    = request.POST['subject']
        from_email = '{}<{}>'.format(settings.SYSTEM_FROM_NAME, settings.SYSTEM_FROM_EMAIL)
        headers    = {'Reply-To': tutor.email}
        recipient_vars = {}
        try:
            for student in students:
                to_email = email_policy_check(student.email)
                link     = get_url_for_student(student)
                if is_mailgun():  # for mailgun we build a list for a single-request multi-send
                    recipient_vars[to_email] = {'link': link}
                else:  # for regular smtp we make a request per student
                    body  = body_template.replace('[link]', link)
                    email = EmailMessage(subject, body, from_email, [to_email], headers=headers)
                    email.send()

            if is_mailgun():
                # to use mailgun's batch sending feature we need to pass a separate To: header on
                # the message from that we give in the RCPT handshake, so we need to use a lower-
                # level smtplib class.
                # https://documentation.mailgun.com/en/latest/user_manual.html#batch-sending
                body           = body_template.replace('[link]', '%recipient.link%')
                msg            = MIMEText(body)
                msg['Subject'] = subject
                msg['From']    = from_email
                msg['To']      = "%recipient%"
                rcpt_to        = list(recipient_vars.keys())
                # todo - Docs suggest 998 char limit but testing shows effective with 1394
                #        I suspect email.policy.SMTP.fold is already being called here
                msg['X-Mailgun-Recipient-Variables'] = json.dumps(recipient_vars)
                smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
                smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                smtp.sendmail(settings.SYSTEM_FROM_EMAIL, rcpt_to, msg.as_string())
                smtp.quit()

            message_text = '{} email{} sent'.format(len(students),
                                                    '' if len(students) == 1 else 's')
        except (smtplib.SMTPDataError, smtplib.SMTPAuthenticationError) as e:
            message_text = 'Email sending failed. ' + \
                           'This normally means we have hit a daily or hourly sending limit.'

        messages.add_message(request, messages.INFO, message_text)
        return HttpResponseRedirect(reverse('exeatsapp:emails'))

    context = {
        'students': Student.objects.filter(tutor=request.session['tutor_id'])
                                   .annotate(last_slot=Max('slot__start'))
                                   .annotate(last_attended=Max('slot__start',
                                                               filter=Q(slot__attended=True)))
                                   .order_by('name'),
        'tutor': tutor,
    }
    return render(request, 'exeatsapp/emails.html', context)


def signup(request, hash):
    student = get_student_for_hash(hash)
    if not student:
        raise Http404('link appears to be invalid')

    if request.method == 'POST':
        slot_id = [k[5:] for k, v in request.POST.items() if k[0:5] == 'slot_'][0]
        slot = Slot.objects.filter(id=slot_id, tutor=student.tutor.id, allocatedto=None).first()
        if slot:
            # un-book any booked future slots
            existing_bookings = Slot.objects.filter(allocatedto=student.id,
                                                    start__gte=datetime.datetime.now())
            for booking in existing_bookings:
                booking.allocatedto = None
                booking.save()
            # book chosen slot
            slot.allocatedto = student
            slot.save()
            subject  = 'Booking confirmation'
            context  = {'slot': slot, 'url': get_url_for_student(student)}
            body     = render_to_string('exeatsapp/emailconfirmation.html', context)
            to_email = email_policy_check(student.email)
            email = EmailMessage(subject, body,
                                 '{}<{}>'.format(settings.SYSTEM_FROM_NAME,
                                                 settings.SYSTEM_FROM_EMAIL),
                                 [to_email])
            try:
                email.send()
                message_text = 'Slot booked. We have sent you a confirmation by email.'
            except (smtplib.SMTPDataError, smtplib.SMTPAuthenticationError) as e:
                message_text = 'Slot booked. We were unable to send an email confirmation.'

        else:
            message_text = 'Booking slot not available, please choose a different slot.'

        messages.add_message(request, messages.INFO, message_text)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    context = {
        'student': student,
        'chosen_slot': Slot.objects.filter(allocatedto=student.id,
                                           start__gte=datetime.datetime.now()
                                           ).first(),
        'slots': Slot.objects.filter(tutor=student.tutor.id,
                                     start__gte=datetime.datetime.now()
                                     ).order_by('start')
    }
    return render(request, 'exeatsapp/signup.html', context)


@login_required
def view(request):
    context = {
        'slots': Slot.objects.filter(tutor=request.session['tutor_id'],
                                     start__gte=get_midnight()
                                     ).order_by('start')
    }
    return render(request, 'exeatsapp/view.html', context)


@login_required
def toggle_attended(request, id):
    try:
        slot = Slot.objects.get(id=id, tutor=request.session['tutor_id'])
    except Slot.DoesNotExist:
        raise Http404("Not found")

    slot.attended = not slot.attended
    slot.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def toggle_alert(request, id):
    try:
        student = Student.objects.get(id=id, tutor=request.session['tutor_id'])
    except Student.DoesNotExist:
        raise Http404("Not found")

    student.alert = not student.alert
    student.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required
def history(request):
    context = {
        'slots': Slot.objects.filter(tutor=request.session['tutor_id'],
                                     start__lte=datetime.datetime.now(),
                                     allocatedto__isnull=False
                                     ).order_by('-start')
    }
    return render(request, 'exeatsapp/history.html', context)


@login_required
def tutor_settings(request):
    tutor = Tutor.objects.get(id=request.session['tutor_id'])
    if request.method == 'POST':
        tutor.name = request.POST['tutor_name']
        tutor.save()
        message_text = 'Tutor name changed'
        messages.add_message(request, messages.INFO, message_text)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    context = {
        'tutor': tutor
    }
    return render(request, 'exeatsapp/settings.html', context)


@csrf_exempt
def deploy(request):
    """ triggers git pull of updated application code on receipt of valid webhook """
    github_signature = request.META['HTTP_X_HUB_SIGNATURE']
    signature = hmac.new(settings.SECRET_DEPLOY_KEY.encode('utf-8'), request.body, hashlib.sha1)
    expected_signature = 'sha1=' + signature.hexdigest()
    if not hmac.compare_digest(github_signature, expected_signature):
        return HttpResponseForbidden('Invalid signature header')

    if subprocess.run(["git", "pull"], timeout=15).returncode == 0 and \
       subprocess.run(["python", "manage.py", "migrate"], timeout=15).returncode == 0 and \
       subprocess.run(["python", "manage.py", "collectstatic", "--noinput"], timeout=15).returncode == 0:
        return HttpResponse('Webhook received', status=http.client.ACCEPTED)
    raise Http404("Update failed")


def email_policy_check(email):
    """ overwrites email addresses with a saftey address if set """
    return getattr(settings, 'ALL_EMAILS_TO', email)


def get_midnight():
    return datetime.datetime.combine(datetime.datetime.today(), datetime.time.min)
