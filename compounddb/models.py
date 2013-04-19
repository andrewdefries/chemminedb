#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.auth.models import User
from logging import root, basicConfig
import datetime

basicConfig()


class LibraryNotExistError(Exception):

    pass


class LibraryHeaderAlreadyExistError(Exception):

    pass


class LibraryHeaderNotExistError(Exception):

    pass


class LibraryAlreadyExistError(Exception):

    pass


class LibraryHeader(models.Model):

    name = models.CharField(max_length=256, unique=True)

    class Meta:

        verbose_name_plural = 'Library Headers'

    def __unicode__(self):
        return '%s' % self.name


class Library(models.Model):

    header = models.ForeignKey(LibraryHeader)
    version = models.IntegerField(default=0)
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:

        verbose_name_plural = 'Libraries'

        # ordering = ['id', 'version']

        get_latest_by = 'created_time'

    def __unicode__(self):
        return '%s_v%s' % (self.header.name, self.version)

    def get_absolute_url(self):
        return '/library/%s/%s' % (self.header.name.replace(' ', '_'),
                                   self.version)


class Compound(models.Model):

    library = models.ManyToManyField(Library)
    cid = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    formula = models.CharField(max_length=256)
    weight = models.DecimalField(max_digits=10, decimal_places=2)
    inchi = models.TextField()
    smiles = models.CharField(max_length=1024)
    username = models.CharField(max_length=30, default='', blank=True)

    # sdf_file = models.OneToOneField(SDFFile)

    # pub_date = models.DateTimeField(auto_now_add=True)
    # header = models.ForeignKey(CompoundHeader)
    # version = models.IntegerField()
    # is_latest = models.BooleanField(default=True)

    class Meta:

        # ordering = ['id']
        # get_latest_by = 'pub_date'

        pass

    def __unicode__(self):
        return '%s_%s' % (self.id, self.cid)

    @models.permalink
    def get_absolute_url(self):
        return ('compound_detail', (), dict(library=self.library,
                cid=self.header.cid))


class WorkbenchCompounds(models.Model):

    compound = models.ForeignKey(Compound, primary_key=True)
    username = models.CharField(max_length=30)

    def __unicode__(self):
        return '%s' % self.id


class SDFFile(models.Model):

    sdffile = models.TextField()
    compound = models.ForeignKey(Compound)

    class Meta:

        # ordering = ['id']

        pass

    def __unicode__(self):
        return '%s' % self.id


class Annotation(models.Model):

    name = models.CharField(max_length=256)
    value = models.TextField()
    create_time = models.DateTimeField(default=datetime.datetime.now)
    compound = models.ForeignKey(Compound)

    class Meta:

        # ordering = ['id']

        pass

    def __unicode__(self):
        return '%s %s %s' % (self.id, self.compound.id, self.name)


class PropertyField(models.Model):

    name = models.CharField(max_length=256)
    description = models.TextField()
    is_integer = models.BooleanField()
    source_tag = models.CharField(max_length=256)

    class Meta:

        verbose_name_plural = 'PropertyFields'

        # ordering = ['id']

    def __unicode__(self):
        return '%s, %s: %s' % (self.name, self.description,
                               self.is_integer)


class Property(models.Model):

    field = models.ForeignKey(PropertyField)
    value = models.FloatField()
    compound = models.ForeignKey(Compound, editable=False)

    class Meta:

        verbose_name_plural = 'Properties'

        # ordering = ['id', 'compound']

    def __unicode__(self):
        return '%s' % self.field


class Plate(models.Model):

    format = models.IntegerField()
    plate = models.IntegerField()
    well = models.CharField(max_length=3)
    compound = models.ForeignKey(Compound)
    plate_string = models.CharField(max_length=20, blank=True)

    class Meta:

        # ordering = ['id', 'compound']

        pass

    def __unicode__(self):
        return '%s_%s_%s' % (self.compound, self.plate, self.well)


class Fingerprint(models.Model):

    compound = models.ForeignKey(Compound)

    # fingerprint = models.CharField(max_length=512)

    md5 = models.CharField(max_length=32)

    class Meta:

        # ordering = ['id', 'compound']

        pass

    def __unicode__(self):
        return '%s' % self.compound


