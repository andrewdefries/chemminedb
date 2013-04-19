#!/usr/bin/python
# -*- coding: utf-8 -*-

from compounddb.models import LibraryHeader, Library, Compound
from screendb.models import DTS251Entry
import sys
import csv


def upload(csvfile):
    rd = csv.reader(open(csvfile), delimiter=',')
    rd.next()

    for (count, data) in enumerate(rd):
        try:
            (lib_name, c_id, plate, well) = data[0:4]
            (raw, score, stdev) = data[4:7]

            control = '-'
            compound = None

            # get compound

            if c_id == 'NC':
                control = 'N'
            elif c_id == 'PC':
                control = 'P'
            else:

                # if lib_name == 'Microsource Spectrum':
                # ....c_id = '0' * (8 - len(c_id)) + c_id

                lib_header = \
                    LibraryHeader.objects.get(name__iexact=lib_name)
                lib = Library.objects.filter(header=lib_header).latest()
                compound = lib.compound_set.get(cid=c_id)

            # import pdb
            # pdb.set_trace()

            entry = DTS251Entry(
                compound=compound,
                plate=plate,
                well=well,
                control=control,
                raw=raw,
                score=score,
                stdev=stdev,
                )
            entry.save()
        except:
            import pdb
            pdb.set_trace()


