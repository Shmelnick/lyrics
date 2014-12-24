# -*- coding: utf-8 -*-
__author__ = 'a.melnikov'

from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from lyrics.models import Song, IndexElement
import os
import csv

# -----------------------------------------------------------------------------pymorphy
from pymorphy.contrib import tokenizers
from pymorphy import get_morph                      # Морф анализатор https://pythonhosted.org/pymorphy/intro.html
from ..pymorphy_dicts_dir import ret
morph = get_morph(ret())    # Директория со словарями для pymorphy

DIR_OF_COLLECT_DATA = os.path.dirname(os.path.abspath(__file__))[:-17] + "collect_data/"
FILE_WITH_SONGS_INFO = DIR_OF_COLLECT_DATA + 'songs.csv'                   # тут основная информация
#FILE_WITH_TEXTS_OF_SONGS = DIR_OF_COLLECT_DATA + 'texts_of_songs.csv'      # а тут текст
FILE_WITH_TEXTS_OF_SONGS = DIR_OF_COLLECT_DATA + 'test_texts_of_songs.csv'


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        all_songs_in_db = Song.objects.all()

        ids_of_songs = set()
        for rec in all_songs_in_db:
            song_id = rec.aid
            ids_of_songs.add(int(song_id))

        csvfile1 = open(FILE_WITH_SONGS_INFO, 'rb')
        reader1 = csv.reader(csvfile1, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        # Дополняем базу новыми записями
        added_songs = 0
        added_terms = 0
        recognized_tokens = 0
        for row1 in reader1:

            # [self.aid, self.artist, self.title, self.duration, self.lyrics, self.url]
            aid, artist, title, duration, lyrics_id, url = row1[0:6]

            csvfile2 = open(FILE_WITH_TEXTS_OF_SONGS, 'rb')
            reader2 = csv.reader(csvfile2, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for row2 in reader2:
                # [id_of_song, flag, text]
                lyrics_id2, flag, text = row2[0:3]

                if lyrics_id == lyrics_id2 and flag == 'russian' and int(aid) not in ids_of_songs:

                    # Не встреченная ранее русская песня - заносим в базу
                    s = Song(aid=int(aid), artist=artist, title=title, duration=duration, url=url, lyrics=text)
                    s.save()

                    # Теперь вытащим все токены из текста
                    for word in tokenizers.extract_words(text.decode('utf8')):
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
                    ids_of_songs.add(int(aid))
                    break

            csvfile2.close()

        csvfile1.close()
        print "Added songs", added_songs
        print "Found words", recognized_tokens
        print "Added terms", added_terms

    def backwards(self, orm):
        "Write your backwards methods here."
        # Вот здесь поаккуратнее - чистится все, не только последние добавления
        all_songs_in_db = Song.objects.all()
        print "Deleted", len(all_songs_in_db), "songs"
        all_terms_in_db = IndexElement.objects.all()
        print "Deleted", len(all_terms_in_db), "words"
        db.clear_table('lyrics_song')
        db.clear_table('lyrics_indexelement')

    models = {
        u'lyrics.indexelement': {
            'Meta': {'object_name': 'IndexElement'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'song': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['lyrics.Song']", 'symmetrical': 'False'}),
            'term': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'lyrics.song': {
            'Meta': {'ordering': "['title']", 'object_name': 'Song'},
            'aid': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'artist': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'duration': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lyrics': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['lyrics']
    symmetrical = True
