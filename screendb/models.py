#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from logging import root, basicConfig
import datetime
from compounddb.models import Compound
from django import forms
from django.forms.widgets import *
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
basicConfig()

SCREEN_TYPE = (('g', 'visiable to registered users'), ('o',
               'visiable to the owner only'), ('x',
               'visiable to everybody'))


# Create your models here.

class Screen(models.Model):

    owner = models.ForeignKey(User)
    create_time = models.DateTimeField(default=datetime.datetime.now)
    last_update = models.DateTimeField(default=datetime.datetime.now)
    name = models.TextField()
    description = models.TextField(blank=True, verbose_name='Abstract')

    pi = models.CharField(max_length=256, blank=True)
    co_author = models.CharField(max_length=256, blank=True)
    funding = models.TextField(blank=True)
    number_of_cmp_screened = models.IntegerField(null=True, blank=True)
    strategy = models.TextField(blank=True)
    type = models.CharField(max_length=1, choices=SCREEN_TYPE)
    extra_annotation = models.TextField(blank=True)
    inactive_compounds = models.ManyToManyField(Compound,
            related_name='inactive_in_screen')

    class Meta:

        get_latest_by = 'create_time'

    def __unicode__(self):
        return '%s_%s' % (self.id, self.name)

    def get_absolute_url(self):
        return reverse('screen-detail', args=(self.id, ))

    @classmethod
    def search(cls, available_screens, query):
        ids = [s.id for s in available_screens]
        queryset = \
            Screen.objects.filter(id__in=ids).filter(Q(owner__first_name__icontains=query)
                | Q(owner__last_name__icontains=query)
                | Q(pi__icontains=query)
                | Q(co_author__icontains=query)
                | Q(strategy__icontains=query)
                | Q(extra_annotation__icontains=query)
                | Q(name__icontains=query)
                | Q(description__icontains=query))

        return queryset.distinct()

    def save(self):
        self.last_update = datetime.datetime.now()
        super(Screen, self).save()


class ScreenForm(forms.ModelForm):

    name = forms.CharField(widget=TextInput(attrs={'size': '30'}))
    description = forms.CharField(widget=Textarea(attrs={'cols': '30',
                                  'rows': '2'}))
    funding = forms.CharField(widget=TextInput(attrs={'size': '30'}))
    strategy = forms.CharField(widget=Textarea(attrs={'cols': '30',
                               'rows': '2'}))
    extra_annotation = \
        forms.CharField(widget=TextInput(attrs={'size': '30'}),
                        required=False)

    class Meta:

        model = Screen
        exclude = ['owner', 'create_time', 'last_update',
                   'inactive_compounds']

    def clean(self):
        cleaned_data = self.cleaned_data
        from screendb.templatetags.annotationformat import parse, \
            annotation_to_li, SyntaxError
        value = cleaned_data.get('strategy', '')
        if ',' in value or '{' in value or '}' in value:
            try:
                parse(value)
            except SyntaxError, inst:
                self._errors['strategy'] = \
                    self.error_class(['Syntax error: '
                        + inst.description + ':: pos = '
                        + str(inst.offset) + " near '"
                        + value[inst.offset:inst.offset + 20] + "'"])
        elif ':' in value:
            try:
                annotation_to_li(value, lambda x: x)
            except:
                self._errors['strategy'] = \
                    self.error_class(['Syntax error '])
        return cleaned_data


ACTIVE_LEVEL_CHOICES = (
    (0, '0: not active'),
    (1, '1: active in primary screen'),
    (2, '2: active in primary and secondary screen'),
    (3, '3: active in all previous and follow-up screens'),
    (4, '4: target protein(s) identified'),
    (5, '5: selectivity for target protein(s) demonstrated'),
    )


# a mix-in to check compound ID input

class CompoundInputMixIn(object):

    def clean_compound(self):
        compound = self.cleaned_data.get('compound')
        if not compound:
            return None
        try:
            compound = Compound.objects.get(id=int(compound))
        except:
            raise forms.ValidationError('No such compound!')
        return compound


class ScreenFile(models.Model, CompoundInputMixIn):

    screen = models.ForeignKey(Screen)
    title = models.TextField(blank=True)
    compound = models.ForeignKey(Compound, null=True, blank=True)
    description = models.TextField(blank=True)

    # path = models.FilePathField()

    mime = models.TextField()
    original_name = models.CharField(max_length=256, blank=True)

    ordering = models.IntegerField(null=True)

    def __unicode__(self):
        return '%s_%s' % (self.id, self.title)

    def invalidate_screenstats_cache(self):
        """when a screenfile is added/deleted, this will invalidate the 
........cached screen statistics"""

        if self.screen:

            # invalidate cache

            cache_key = 'screen:stats:%d' % self.screen.id
            cache.delete(cache_key)

            # force update of last_update on screen

            self.screen.save()

    def save(self):
        self.invalidate_screenstats_cache()
        super(ScreenFile, self).save()

    def delete(self):
        self.invalidate_screenstats_cache()
        super(ScreenFile, self).delete()


PUBLICATION_MODE_CHOICES = (('pubmed', 'PubMed ID'), ('publication',
                            'Publication Details'), ('web',
                            'Web Address'))


class Publication(ScreenFile):

    mode = models.CharField(choices=PUBLICATION_MODE_CHOICES,
                            max_length=256)

    # mode: pubmed

    pubmed_id = models.CharField(max_length=256, blank=True)

    # mode: publication

    journal = models.TextField(blank=True)
    volume = models.TextField(blank=True)
    pages = models.CharField(blank=True, max_length=32)
    pub_title = models.TextField(blank=True)
    author = models.TextField(blank=True)
    publication_url = models.TextField(blank=True)

    # mode: web address

    web_url = models.TextField(blank=True)


class PublicationForm(forms.ModelForm, CompoundInputMixIn):

    compound = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                               required=False)
    title = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                            required=True)
    journal = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                              required=False)
    volume = forms.CharField(widget=TextInput(attrs={'size': '3'}),
                             required=False)
    pub_title = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                                required=False)
    publication_url = \
        forms.CharField(widget=TextInput(attrs={'size': '30'}),
                        required=False)
    author = forms.CharField(widget=TextInput(attrs={'size': '10'}),
                             required=False)
    web_url = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                              required=False)

    class Meta:

        model = Publication
        exclude = ['screen', 'mime', 'original_name', 'ordering']

    def clean(self):
        cleaned_data = self.cleaned_data
        mode = cleaned_data.get('mode')
        pubmed_id = cleaned_data.get('pubmed_id')

        if mode == 'pubmed':
            if not pubmed_id:
                self._errors['pubmed_id'] = \
                    self.error_class(['This field is required when mode is set to PubMed ID'
                        ])
            else:

                # load info from pubmed website

                try:
                    abstract = pubmed_abstract(pubmed_id)
                    self.cleaned_data['journal'] = abstract['journal']
                    self.cleaned_data['volume'] = abstract['volume']
                    self.cleaned_data['pages'] = abstract['pages']
                    self.cleaned_data['pub_title'] = \
                        abstract['pub_title']
                    self.cleaned_data['author'] = abstract['author']
                    self.cleaned_data['url'] = abstract['url']
                except:
                    self._errors['pubmed_id'] = \
                        self.error_class(['This does not seem to be a valid PubMed ID'
                            ])
        elif mode == 'publication':

            required = ['journal', 'volume', 'pages', 'pub_title',
                        'author']
            for field in required:
                if not cleaned_data.get(field):
                    self._errors[field] = \
                        self.error_class(['This field is required when mode is set to Publication Details'
                            ])
        elif mode == 'web':
            if not cleaned_data.get('web_url'):
                self._errors['web_url'] = \
                    self.error_class(['This field is required when mode is set to Web Address'
                        ])
        else:
            self._errors['mode'] = \
                self.error_class(['Please select one mode from the dropdown menu'
                                 ])

        return cleaned_data


class StandardCompoundAnnotation(ScreenFile):

    extra_annotation = models.TextField(blank=True)

    # assay 1 (mandatory)

    a1_name = models.CharField(max_length=256, verbose_name='Assay Name'
                               )
    a1_desc = models.TextField(blank=True, verbose_name='Description')
    a1_score = models.IntegerField(choices=ACTIVE_LEVEL_CHOICES,
                                   verbose_name='Score')
    a1_concentration = models.CharField(max_length=256,
            verbose_name='Concentration')

    # assay 2 (optional)

    a2_name = models.CharField(max_length=256, blank=True,
                               verbose_name='Assay Name')
    a2_desc = models.TextField(blank=True, verbose_name='Description')
    a2_score = models.IntegerField(choices=ACTIVE_LEVEL_CHOICES,
                                   null=True, blank=True,
                                   verbose_name='Score')
    a2_concentration = models.CharField(max_length=256, blank=True,
            verbose_name='Concentration')

    # assay 3 (optional)

    a3_name = models.CharField(max_length=256, blank=True,
                               verbose_name='Assay Name')
    a3_desc = models.TextField(blank=True, verbose_name='Description')
    a3_score = models.IntegerField(choices=ACTIVE_LEVEL_CHOICES,
                                   null=True, blank=True,
                                   verbose_name='Score')
    a3_concentration = models.CharField(max_length=256, blank=True,
            verbose_name='Concentration')


class StandardCompoundAnnotationForm(forms.ModelForm,
    CompoundInputMixIn):

    compound = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                               required=False)
    title = forms.CharField(widget=TextInput(attrs={'size': '30',
                            'value': 'Standard Compound Annotation'}))

    class Meta:

        exclude = ['screen', 'mime', 'original_name', 'ordering']
        model = StandardCompoundAnnotation

    def clean(self):
        cleaned_data = self.cleaned_data

        # check compound

        if not cleaned_data.get('compound'):
            self._errors['compound'] = \
                self.error_class(['You must specify the compound to be annotated'
                                 ])

        # check assay 2 and 3: if any of anme or score or concentration appears,
        # it must all appear. in other words, AND == OR

        missing = []

        # this is optional field but if presents will set others mandatory

        optional = ['a2_desc', 'a3_desc']
        required = [['a2_name', 'a2_score', 'a2_concentration'],
                    ['a3_name', 'a3_score', 'a3_concentration']]
        for assay in required:
            _and = True
            _or = cleaned_data.get(optional[0])
            del optional[0]
            for i in assay:
                _and = _and and cleaned_data.get(i)
                _or = _or or cleaned_data.get(i)
            if _and != _or:
                for i in assay:
                    if not cleaned_data.get(i):
                        self._errors[i] = \
                            self.error_class(['This field is required if you enable this assay'
                                ])

        return cleaned_data


class TextFile(ScreenFile):

    extra_annotation = models.TextField(blank=True)
    path = models.FileField(upload_to='text_files/%y/%m/%d/')


class TextFileForm(forms.ModelForm, CompoundInputMixIn):

    compound = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                               required=False)
    title = forms.CharField(widget=TextInput(attrs={'size': '30'}))

    class Meta:

        exclude = ['screen', 'mime', 'original_name', 'ordering']
        model = TextFile

    def clean(self):
        cleaned_data = self.cleaned_data
        if 'path' in cleaned_data:
            try:
                mime = cleaned_data['path'].content_type
                if not mime.startswith('text/'):
                    self._errors['path'] = \
                        self.error_class(['The uploaded file does not seem to be a text file.'
                            ])
                cleaned_data['mime'] = 'text/plain'
                cleaned_data['original_name'] = cleaned_data['path'
                        ].name
            except AttributeError:

                # this happens when you modify a file and do not reupload
                  # a file

                pass
        return cleaned_data


class ImageFile(ScreenFile):

    extra_annotation = models.TextField(blank=True)
    path = models.FileField(upload_to='images/%y/%m/%d/')
    reference = models.FileField(upload_to='images/%y/%m/%d/')


class ImageFileForm(forms.ModelForm, CompoundInputMixIn):

    compound = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                               required=False)
    title = forms.CharField(widget=TextInput(attrs={'size': '30'}))
    reference = \
        forms.FileField(help_text='Display a reference image next to the above image (optional)'
                        , required=False)

    class Meta:

        exclude = ['screen', 'mime', 'original_name', 'ordering']
        model = ImageFile

    def clean(self):
        cleaned_data = self.cleaned_data
        if 'path' in cleaned_data:
            try:
                mime = cleaned_data['path'].content_type
                if not mime.startswith('image/'):
                    self._errors['path'] = \
                        self.error_class(['The uploaded file does not seem to be an image file.'
                            ])
                if cleaned_data['reference'] \
                    and not cleaned_data['reference'
                        ].content_type.startswith('image/'):
                    self._errors['reference'] = \
                        self.error_class(['The uploaded file does not seem to be an image file.'
                            ])
                cleaned_data['mime'] = mime
                cleaned_data['original_name'] = cleaned_data['path'
                        ].name
            except AttributeError:

                # this happens when you modify a file and do not reupload
                  # a file

                pass
        return cleaned_data


class AnnotationFile(ScreenFile):

    extra_annotation = models.TextField(blank=True)
    path = models.FileField(upload_to='annotation_files/%y/%m/%d/')


class AnnotationFileForm(forms.ModelForm, CompoundInputMixIn):

    compound = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                               required=False)
    title = forms.CharField(widget=TextInput(attrs={'size': '30'}))

    class Meta:

        exclude = ['screen', 'mime', 'original_name', 'ordering']
        model = AnnotationFile

    def clean(self):
        cleaned_data = self.cleaned_data
        if 'path' in cleaned_data:
            try:
                mime = cleaned_data['path'].content_type
                if not mime.startswith('text/'):
                    self._errors['path'] = \
                        self.error_class(['The uploaded file does not seem to be an annotation file.'
                            ])
                cleaned_data['mime'] = 'text/annotation'
                cleaned_data['original_name'] = cleaned_data['path'
                        ].name
            except:

                # this happens when you modify a file and do not reupload
                  # a file

                pass
        return cleaned_data


class OtherFile(ScreenFile):

    extra_annotation = models.TextField(blank=True)
    path = models.FileField(upload_to='other_files/%y/%m/%d/')


class OtherFileForm(forms.ModelForm, CompoundInputMixIn):

    compound = forms.CharField(widget=TextInput(attrs={'size': '30'}),
                               required=False)
    title = forms.CharField(widget=TextInput(attrs={'size': '30'}))

    class Meta:

        exclude = ['screen', 'mime', 'original_name', 'ordering']
        model = OtherFile

    def clean(self):
        cleaned_data = self.cleaned_data
        if 'path' in cleaned_data:
            cleaned_data['mime'] = 'application/octet-stream'
            cleaned_data['original_name'] = cleaned_data['path'].name
        return cleaned_data


class ExtraAnnotation(models.Model):

    screen = models.ForeignKey(Screen)

    # title = models.TextField()

    extra_annotation = models.TextField(blank=True)


class ExtraAnnotationForm(forms.ModelForm):

    # title = forms.CharField(widget=TextInput(attrs={'size':'30'}))

    class Meta:

        exclude = ['screen']
        model = ExtraAnnotation

    def clean(self):
        cleaned_data = self.cleaned_data
        return cleaned_data


class GlobalReferenceImageFile(models.Model):

    screen = models.ForeignKey(Screen)

    # title = models.TextField()

    mime = models.TextField()
    path = models.FileField(upload_to='global_ref_image_files/%y/%m/%d/'
                            )


class GlobalReferenceImageFileForm(forms.ModelForm):

    # title = forms.CharField(widget=TextInput(attrs={'size':'30'}))

    class Meta:

        exclude = ['screen', 'mime', 'original_name']
        model = GlobalReferenceImageFile

    def clean(self):
        cleaned_data = self.cleaned_data
        if 'path' in cleaned_data:
            mime = cleaned_data['path'].content_type
            if not mime.startswith('image/'):
                self._errors['path'] = \
                    self.error_class(['The uploaded file does not seem to be an image file.'
                        ])
        return cleaned_data


def pubmed_abstract(pubmed_id):

    from re import compile

    abstract = dict()
    abstract['journal'] = ''
    abstract['volume'] = ''
    abstract['pages'] = ''
    abstract['pub_title'] = ''
    abstract['author'] = ''
    abstract['url'] = ''

    import urllib2
    url = 'http://www.ncbi.nlm.nih.gov/pubmed/%s' % pubmed_id
    try:
        handler = urllib2.urlopen(url)
    except:
        raise

    source = handler.read()

    pattern = \
        compile(r'div\s+class="rprt\s+abstract"><p\s+class="citation"><a\s+.*?>(.*?)</a>(.*?)</p><h1\s+class="title">(.*?)</h1><p\s+class="auth_list">(.*?)</p>'
                )
    m = pattern.search(source)

    if m:
        abstract['journal'] = m.group(1)
        pub = m.group(2)
        try:
            (abstract['volume'], abstract['pages']) = pub.split(':')
            abstract['volume'] = abstract['volume'].strip()
        except:
            abstract['volume'] = pub
            abstract['pages'] = ''
        abstract['pub_title'] = m.group(3)
        au_list = m.group(4)

        start = compile(r'<a.*?>')
        end = compile(r'</a>')
        abstract['author'] = end.sub('', start.sub('', au_list))
        abstract['url'] = url

    return abstract


class DTSEntry(models.Model):

    """Defined Target Screen common info """

    compound = models.ForeignKey(Compound, blank=True, null=True)
    plate = models.CharField(max_length=16)
    well = models.CharField(max_length=16)
    control = models.CharField(max_length=1, choices=(('-',
                               'regular compound'), ('N',
                               'negative control'), ('P',
                               'positive control')))

    class Info:

        all_fields = []

    def __unicode__(self):
        """this control how data entry is displayed in virtual plate's tooltip"""

        if self.compound is None:
            if self.control == 'P':
                x = 'Positive Control'
            elif self.control == 'N':
                x = 'Negative Control'
        else:
            x = (self.compound.library.all()[0].header.name,
                 self.compound.cid)
            if self.control == '-':
                url = reverse('compound_detail', args=(x[0], x[1], ''))
                _ = '''Library: %s
ID: <a href="%s">%s</a>
'''
                x = _ % (x[0], url, x[1])
            else:
                _ = '''Library: %s
ID: %s
'''
                x = _ % x
        x += '''Plate: %s
Well: %s
''' % (self.plate, self.well)
        for field in self.__class__.Info.all_fields:
            x += '%s: %s\n' % (field, getattr(self, field))
        return mark_safe(x)


class DTS249Entry(DTSEntry):

    raw = models.DecimalField(max_digits=10, decimal_places=2)
    score = models.DecimalField(max_digits=10, decimal_places=2)
    comment = models.CharField(max_length=256)
    plate_z1 = models.DecimalField(max_digits=10, decimal_places=2)
    plate_z = models.DecimalField(max_digits=10, decimal_places=2)
    sample_mean = models.DecimalField(max_digits=10, decimal_places=2)
    sample_SD = models.DecimalField(max_digits=10, decimal_places=2)

    class Info:

        per_plate = 384
        all_fields = [
            'raw',
            'score',
            'comment',
            'plate_z1',
            'plate_z',
            'sample_mean',
            'sample_SD',
            ]
        virtual_plate_fields = ['raw', 'score']

    @classmethod
    def table_header(cls):
        """table header in DTS tabular view"""

        return """
		<td>Library</td>
		<td>ID</td>
		<td class="hidden_title">Plate</td>
		<td>Well</td>
		<td>Raw Value</td>
		<td>Score</td>
		<td>Comment</td>
		<td class="hidden_title">Plate_Z1</td>
		<td class="hidden_title">Plate_Z</td>
		<td class="hidden_title">Sample_mean</td>
		<td class="hidden_title">Sample_SD</td>
		"""

    def as_tds(self):
        """table rows in DTS tabular view"""

        url = ''
        if self.control == 'P':
            x = ('', 'Positive Control')
        elif self.control == 'N':
            x = ('', 'Negative Control')
        else:
            x = (self.compound.library.all()[0].header.name,
                 self.compound.cid)
            url = reverse('compound_detail', args=(x[0], x[1], ''))
        table = """<td>%s</td><td class="compoundid">%s</td>""" % x
        if url:
            table = \
                """<td>%s</td><td class="compoundid"><a href="%s">%s</a></td>""" \
                % (x[0], url, x[1])

        return table + """<td class="hidden_value">%s</td>""" \
            % self.plate + """<td>%s</td>""" % self.well \
            + """<td>%s</td>""" % self.raw + """<td>%s</td>""" \
            % self.score + """<td>%s</td>""" % self.comment \
            + """<td class="hidden_value">%s</td>""" % self.plate_z1 \
            + """<td class="hidden_value">%s</td>""" % self.plate_z \
            + """<td class="hidden_value">%s</td>""" % self.sample_mean \
            + """<td class="hidden_value">%s</td>""" % self.sample_SD


class DTS251Entry(DTSEntry):

    raw = models.DecimalField(max_digits=10, decimal_places=2)
    score = models.DecimalField(max_digits=10, decimal_places=2)
    stdev = models.DecimalField(max_digits=10, decimal_places=2)

    class Info:

        per_plate = 96
        all_fields = ['raw', 'score', 'stdev']
        virtual_plate_fields = ['raw', 'score', 'stdev']

    @classmethod
    def table_header(cls):
        """table header in tabular view"""

        return """
		<td>Library</td>
		<td>ID</td>
		<td class="hidden_title">Plate</td>
		<td>Well</td>
		<td>Raw Value</td>
		<td>Score</td>
		<td>Stdev</td>
		"""

    def as_tds(self):
        """table rows in tabular view"""

        url = ''
        if self.control == 'P':
            x = ('', 'Positive Control')
        elif self.control == 'N':
            x = ('', 'Negative Control')
        else:
            x = (self.compound.library.all()[0].header.name,
                 self.compound.cid)
            url = reverse('compound_detail', args=(x[0], x[1], ''))
        table = """<td>%s</td><td class="compoundid">%s</td>""" % x
        if url:
            table = \
                """<td>%s</td><td class="compoundid"><a href="%s">%s</a></td>""" \
                % (x[0], url, x[1])

        return table + """<td class="hidden_value">%s</td>""" \
            % self.plate + """<td>%s</td>""" % self.well \
            + """<td>%s</td>""" % self.raw + """<td>%s</td>""" \
            % self.score + """<td>%s</td>""" % self.stdev


