# -*- coding: utf-8 -*-
__author__ = 'a.melnikov'
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from lyrics.models import Song, IndexElement
import csv
import os

# -----------------------------------------------------------------------------pymorphy
from pymorphy.contrib import tokenizers
from pymorphy import get_morph                      # Морф анализатор https://pythonhosted.org/pymorphy/intro.html
from ..pymorphy_dicts_dir import ret
morph = get_morph(ret())    # Директория со словарями для pymorphy

DIR_OF_COLLECT_DATA = os.path.dirname(os.path.abspath(__file__))[:-17] + "collect_data/"
FILE_WITH_PESNIFILM = DIR_OF_COLLECT_DATA + "all_pesnifilm.csv"


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."

        csvfile1 = open(FILE_WITH_PESNIFILM, 'rb')
        reader1 = csv.reader(csvfile1, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        # Дополняем базу новыми записями
        added_songs = 0
        added_terms = 0
        recognized_tokens = 0
        for row1 in reader1:
            print added_songs

            # [self.artist, self.title, self.duration, self.url, lyrics, movie]
            # duration везде 0
            artist, title, duration, url, lyrics, movie = row1[0:6]
            duration = int(duration)

            # Возможны коллизии по aid (наш диапазон [-10000 : -19999]) - заносим в базу
            s = Song(aid=-10000-added_songs, artist=artist, title=title, duration=duration,
                     url=url, lyrics=lyrics, linked_movie=movie)
            s.save()

            # В индекс не пишем лишнее из авторов
            ar = artist.replace("исполнение", "").replace("текст", "").replace("музыка", "").replace("слова", "")
            ar = ar.replace(" и ", " ").replace("автор", "")
            all_text = lyrics + " " + title + " " + movie + " " + ar

            print artist

            # Теперь вытащим все токены из текста
            for word in tokenizers.extract_words(all_text.decode('utf8')):
                recognized_tokens += 1
                for term in morph.normalize(word.upper()):
                    # Берем все варианты нормализации - т.к. могут быть омонимы
                    try:
                        w = IndexElement.objects.get(term=term)     # Слово уже было в обратном индексе
                    except IndexElement.DoesNotExist:
                        w = IndexElement(term=term)
                        w.save()
                    except IndexElement.MultipleObjectsReturned:
                        print "WTF"
                        return
                    w.song.add(s)   # Приписали новую ссылку на слово
                    added_terms += 1

            added_songs += 1

        csvfile1.close()
        print "Added songs", added_songs
        print "Found words", recognized_tokens
        print "Added terms", added_terms

    def backwards(self, orm):
        "Write your backwards methods here."
        all_songs_in_db = Song.objects.all()
        am = 0
        deleted = 0
        for s in all_songs_in_db:
            if s.am_i_song_from_movie():
                s.delete()
                deleted += 1
            am += 1
        print "Deleted", deleted
        print "Of all", am

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
