# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from lyrics.models import Song, IndexElement

# -----------------------------------------------------------------------------pymorphy
from pymorphy.contrib.tokenizers import extract_words
from pymorphy import get_morph                      # Морф анализатор https://pythonhosted.org/pymorphy/intro.html
from ..pymorphy_dicts_dir import ret
morph = get_morph(ret())    # Директория со словарями для pymorphy


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for song in Song.objects.all():
            to_write = list()
            try:
                for i, word in enumerate(extract_words(song.lyrics)):
                    for term in morph.normalize(word.upper()):
                        to_write.append('1 ' + str(i) + " " + term)
            except TypeError:
                pass
            try:
                for i, word in enumerate(extract_words(song.artist)):
                    for term in morph.normalize(word.upper()):
                        to_write.append('2 ' + str(i) + " " + term)
            except TypeError:
                pass
            try:
                for i, word in enumerate(extract_words(song.title)):
                    for term in morph.normalize(word.upper()):
                        to_write.append('3 ' + str(i) + " " + term)
            except TypeError:
                pass
            try:
                for i, word in enumerate(extract_words(song.linked_movie)):
                    for term in morph.normalize(word.upper()):
                        to_write.append('4 ' + str(i) + " " + term)
            except TypeError:
                pass

            song.map_of_normalized_words = "|".join(to_write)
            song.save(update_fields=["map_of_normalized_words"])
            print "Done", song.id

    def backwards(self, orm):
        for song in Song.objects.all():
            song.map_of_normalized_words = ""
            song.save(update_fields=["map_of_normalized_words"])

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
            'map_of_normalized_words': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'rude': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['lyrics']
    symmetrical = True
