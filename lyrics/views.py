# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from lyrics.models import Song, IndexElement
from search import search
import time
from pymorphy.contrib.tokenizers import extract_words
from pymorphy_dicts_dir import ret
import re
from math import log
import itertools

from pymorphy import get_morph
morph = get_morph(ret())
OK = 1
ERROR = 0


def round_time(seconds):
    return "%.2f" % seconds


def index(request):
    params_dict = {
    }

    return render(request, 'index.html', params_dict)


def song_detail(request, song_id):    
    song = get_object_or_404(Song.objects.all(), id=song_id)
    params_dict = {
        'song': song
    }
    return render(request, 'song_detail.html', params_dict)


def song_list(request):    
    start_time = time.time()
    query = request.GET.get('query','')
    if query:

        status, res = search(query.replace("L", "AND").replace(" X", " AND").replace("X", "").encode('utf-8'))
        if status == OK:
            song_list = Song.objects.filter(id__in=res)

            list_of_links = list()
            l_ew = list()

            ended_row_with_dependencies = False
            for i in extract_words(query.encode('utf-8').decode('utf-8').lstrip().rstrip()):
                if i not in ["AND", "OR", "NOT"] and "X" not in i and "L" not in i:
                    l_ew.append(i)
                elif i == "NOT":
                    ended_row_with_dependencies = True
                elif i == "AND" and not ended_row_with_dependencies:
                    list_of_links.append(0)
                elif "X" in i and not ended_row_with_dependencies:
                    list_of_links.append(len(i))
                elif "L" in i and not ended_row_with_dependencies:
                    list_of_links.append(100500)

            list_of_normalized_query_words = [0]*len(l_ew)
            for i, ew in enumerate(l_ew):
                list_of_normalized_query_words[i] = IndexElement.objects.filter(term__in=morph.normalize(ew.upper())).select_related("synonyms", "song")
                if list_of_normalized_query_words[i] is None:
                    print "AAAAAAA"

            # Range here
            for s in song_list:
                l_of_clear_repeats = [0]*len(l_ew)
                l_of_normalized_repeats = [0]*len(l_ew)
                l_of_synonym_repeats = [0]*len(l_ew)
                l_of_tf_idfs = [0]*len(l_ew)
                l_of_positions = [set()]*len(l_ew)
                set_of_highlights = set()                                                # TODO highlight it

                # clear repeats
                low = list(extract_words(s.lyrics))
                i = 0
                for i, w in enumerate(low):
                    w = w.upper()
                    for ii, ew in enumerate(l_ew):
                        if ew.upper() == w:
                            l_of_clear_repeats[ii] += 1
                            set_of_highlights.add(i)
                            l_of_positions[ii].add(i)
                amount_of_words_in_song = i + 1

                for ii, ew in enumerate(l_ew):
                    #   ((^|\|)[^|]*tr($|\|))
                    ss = list()
                    syn_list = list()
                    freq = 0

                    for nor in list_of_normalized_query_words[ii]:
                        ss.append(nor.term)
                        freq += nor.get_linked_songs_amount()
                        for syn in nor.synonyms.all():
                            syn_list.append(syn.term)

                    idf_of_ew = log((100000. - freq + 0.5)/(freq + 0.5))

                    # normalized repeats
                    pat = re.compile("((^|\|)[^\|]*(" + "|".join(ss) + ")($|\|))")
                    print "NORM", "|".join(ss)
                    includes = re.findall(pat, s.map_of_normalized_words)

                    for el in includes:
                        seg, pos, word = el[0].strip("|").split(" ")
                        if seg == '1':
                            set_of_highlights.add(int(pos))
                            l_of_positions[ii].add(int(pos))
                        l_of_normalized_repeats[ii] += 1

                    # Synonyms repeats
                    pat = re.compile("((^|\|)[^\|]*(" + "|".join(syn_list) + ")($|\|))")
                    print "SL", "|".join(syn_list)
                    includes = re.findall(pat, s.map_of_normalized_words)

                    for el in includes:
                        seg, pos, word = el[0].strip("|").split(" ")
                        if seg == '1':
                            set_of_highlights.add(int(pos))
                            l_of_positions[ii].add(int(pos))
                        l_of_synonym_repeats[ii] += 1

                    weighted_tf = (0.6)*l_of_clear_repeats[ii] + (0.3)*l_of_normalized_repeats[ii] + (0.1)*l_of_synonym_repeats[ii]
                    l_of_tf_idfs[ii] = (weighted_tf / amount_of_words_in_song) * idf_of_ew

                range_by = sum(l_of_tf_idfs)                                                            # TODO

                # additional ranking

                all_pos = list()
                for brakes in itertools.product(*l_of_positions):
                    flag = False
                    for i in xrange(len(brakes)-1):
                        if brakes[i] >= brakes[i+1]:
                            flag = True
                            break
                    if not flag:
                        all_pos.append(brakes)

                all_pos2 = list()
                # neighbors through AND
                for b in all_pos:
                    ff = True
                    for i in xrange(len(l_ew)-1):
                        if list_of_links[i] == 0:
                            if b[i+1] != b[i]+1:
                                ff = False
                    if ff:
                        all_pos2.append(b)

                print "AND done", len(all_pos2)

                all_pos3 = list()
                # neighbors through XXX
                for b in all_pos2:
                    ff = True
                    for i in xrange(len(l_ew)-1):
                        if 0 < list_of_links[i] < 100500:
                            trashline = ""
                            for ww in low[b[i] + 1: b[i+1]]:
                                trashline += ww
                            trashline = trashline.upper()
                            am_of_gl = trashline.count("А".decode('utf-8')) + trashline.count("Е".decode('utf-8')) + \
                                       trashline.count("О".decode('utf-8')) + trashline.count("У".decode('utf-8')) + \
                                       trashline.count("Ы".decode('utf-8')) + trashline.count("Э".decode('utf-8')) + \
                                        trashline.count("Я".decode('utf-8')) + trashline.count("И".decode('utf-8')) + \
                                       trashline.count("Ю".decode('utf-8')) + trashline.count("Ё".decode('utf-8'))
                            if am_of_gl != list_of_links[i]:
                                ff = False
                    if ff:
                        all_pos3.append(b)

                for b in all_pos3:
                    print "XXX done", b

                if len(all_pos3) > 0:
                    range_by += 1.0

                print set_of_highlights, l_of_clear_repeats, l_of_normalized_repeats, l_of_synonym_repeats, range_by


            count = song_list.count()
        else:
            return error(request, res)
    else:
        song_list = []
        count = 0


    params_dict = {
        'song_list': song_list,
        'results_count': count,
        'elapsed_time': round_time(time.time() - start_time)
    }

    return render(request, 'song_list.html', params_dict)


def error(request, msg):
    params_dict = {
        'message': msg
    }

    return render(request, 'error.html', params_dict)

