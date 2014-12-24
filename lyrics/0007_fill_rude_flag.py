# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
import os
from lyrics.models import Song, IndexElement

DIR_OF_COLLECT_DATA = os.path.dirname(os.path.abspath(__file__))[:-17] + "collect_data/"
FILE_WITH_RUDES = DIR_OF_COLLECT_DATA + "rude_words.csv"


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        f_rude = open(FILE_WITH_RUDES, "rb")
        rude_set = set()
        for line in f_rude:
            rude_set.add(line.strip().decode("utf8").upper())

        for ru in rude_set:
            try:
                w = IndexElement.objects.prefetch_related('song').get(term=ru)
                for s in w.song.all():
                    s.rude = True
                    s.save(update_fields=['rude'])
            except IndexElement.DoesNotExist:
                pass

        f_rude.close()

    def backwards(self, orm):
        "Write your backwards methods here."
        s_list = Song.objects.all()
        for e in s_list:
            e.rude = False
            e.save(update_fields=['rude'])

    models = {
        u'lyrics.indexelement': {
            'Meta': {'ordering': "['term']", 'object_name': 'IndexElement'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'song': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['lyrics.Song']", 'symmetrical': 'False'}),
            'synonyms': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'im_syn_of'", 'symmetrical': 'False', 'to': u"orm['lyrics.IndexElement']"}),
            'term': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'lyrics.song': {
            'Meta': {'ordering': "['title']", 'object_name': 'Song'},
            'aid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'artist': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'duration': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'linked_movie': ('django.db.models.fields.TextField', [], {'default': 'None', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'lyrics': ('django.db.models.fields.TextField', [], {}),
            'rude': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['lyrics']
    symmetrical = True
