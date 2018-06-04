from django.db import models
from django.contrib.auth.models import AbstractUser

class Exeat(models.Model):
    tutor = models.IntegerField()

    class Meta:
        db_table = 'exeat'

class Slot(models.Model):
    start = models.DateTimeField()
    location = models.CharField(max_length=100)
    tutor = models.ForeignKey('Tutor', on_delete=models.PROTECT, db_column='tutor')
    allocatedto = models.ForeignKey('Student', on_delete=models.SET_NULL, db_column='allocatedto', blank=True, null=True)

    class Meta:
        db_table = 'slot'

class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    tutor = models.ForeignKey('Tutor', on_delete=models.PROTECT, db_column='tutor')

    class Meta:
        db_table = 'student'

class Tutor(models.Model):
    name = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    isadmin = models.BooleanField()
    email = models.CharField(unique=True, max_length=100)

    class Meta:
        db_table = 'tutor'
