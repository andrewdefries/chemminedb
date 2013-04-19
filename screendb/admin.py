#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.contrib import admin
from screendb.models import *


class ScreenAdmin(admin.ModelAdmin):

    raw_id_fields = ('inactive_compounds', )


admin.site.register(Screen, ScreenAdmin)


class ScreenFileAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(ScreenFile, ScreenFileAdmin)


class PublicationAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(Publication, PublicationAdmin)


class StandardCompoundAnnotationAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(StandardCompoundAnnotation,
                    StandardCompoundAnnotationAdmin)


class TextFileAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(TextFile, TextFileAdmin)


class ImageFileAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(ImageFile, ImageFileAdmin)


class AnnotationFileAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(AnnotationFile, AnnotationFileAdmin)


class OtherFileAdmin(admin.ModelAdmin):

    raw_id_fields = ('compound', )


admin.site.register(OtherFile, OtherFileAdmin)

admin.site.register(ExtraAnnotation)
admin.site.register(GlobalReferenceImageFile)
