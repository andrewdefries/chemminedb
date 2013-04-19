#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.contrib import admin
from compounddb.models import *

admin.site.register(Library)
admin.site.register(LibraryHeader)
admin.site.register(Compound)


class AnnotationAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(Annotation, AnnotationAdmin)
admin.site.register(PropertyField)


class PropertyAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(Property, PropertyAdmin)


class SDFFileAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(SDFFile, SDFFileAdmin)


class PlateAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(Plate, PlateAdmin)


class FinerprintAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(Fingerprint, FinerprintAdmin)
