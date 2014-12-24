# -*- coding: utf-8 -*-
#!/usr/bin/python
__author__ = 'a.melnikov'

import os
from lyrics.models import Song, IndexElement

import argparse
from pymorphy_dicts_dir import ret

from pymorphy import get_morph
morph = get_morph(ret())
RUS_LETTERS = "ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ".decode('utf-8')

set_of_marked_words = set()     # слова, которые можно извлечь из запроса, включая синонимы
                                # нужны для выделения в сниппете
encoding = 0
OK = 1
ERROR = 0

#====================================================================================Операции над постинг-листами=======
class ExtendedPostingList():
    """
    Оболочка над постинг-листом, позволяет строить дополнение, чтобы не создавать огромный постинг-лист для операции NOT
    """
    def __init__(self, posting_list, freq, trend=True):
        self.posting_list = posting_list    # постинг-лист
        self.freq = freq                    # частота
        self.trend = trend                  # тренд: если False - то реальный постинг-лист - дополнение указанного

    def __repr__(self):
        return repr((self.posting_list, self.freq, self.trend))

    def build_supplementation(self):
        """
        Операция NOT
        """
        self.trend = not self.trend
        return self

    def add_element(self, e):
        self.posting_list.append(e)
        self.freq += 1

    def pop(self):
        self.posting_list.pop(0)
        self.freq -= 1

    def fst(self):
        return self.posting_list[0]


def intersect(pl1, pl2):
    """
    Пересечение двух постинг-листов
    """
    #print "int inp"
    #print pl1.posting_list
    #print pl2.posting_list

    pl = ExtendedPostingList(list(), 0, pl1.trend)
    while pl1.freq > 0 and pl2.freq > 0:
        pl1_fst = pl1.posting_list[0]
        pl2_fst = pl2.posting_list[0]
        if pl1_fst == pl2_fst:
            pl.add_element(pl1_fst)
            pl1.pop()
            pl2.pop()
        elif pl1_fst < pl2_fst:
            pl1.pop()
        else:
            pl2.pop()

    #print "int out"
    #print pl.posting_list
    return pl


def union(pl1, pl2):
    """
    Объединение двух постинг-листов
    """
    #print "int inp"
    #print pl1.posting_list
    #print pl2.posting_list

    pl = ExtendedPostingList(list(), 0, pl1.trend)
    while pl1.freq > 0 and pl2.freq > 0:
        pl1_fst = pl1.posting_list[0]
        pl2_fst = pl2.posting_list[0]
        if pl1_fst == pl2_fst:
            pl.add_element(pl1_fst)
            pl1.pop()
            pl2.pop()
        elif pl1_fst < pl2_fst:
            pl.add_element(pl1_fst)
            pl1.pop()
        else:
            pl.add_element(pl2_fst)
            pl2.pop()
    while pl1.freq > 0:
        pl.add_element(pl1.posting_list[0])
        pl1.pop()
    while pl2.freq > 0:
        pl.add_element(pl2.posting_list[0])
        pl2.pop()

    #print "int out"
    #print pl.posting_list
    return pl


def diff(pl1, pl2):
    """
    Разность двух постинг-листов, используется для x AND NOT y
    """
    #print "dif inp"
    #print pl1.posting_list
    #print pl2.posting_list

    pl = ExtendedPostingList(list(), 0, pl1.trend)
    while pl1.freq > 0 and pl2.freq > 0:
        pl1_fst = pl1.posting_list[0]
        pl2_fst = pl2.posting_list[0]
        if pl1_fst == pl2_fst:
            pl1.pop()
            pl2.pop()
        elif pl1_fst < pl2_fst:
            pl.add_element(pl1_fst)
            pl1.pop()
        else:
            pl2.pop()

    while pl1.freq > 0:
        pl.add_element(pl1.posting_list[0])
        pl1.pop()

    #print "dif out"
    #print pl.posting_list
    return pl

#===========================================================================================================Парсинг=====

#   Такая получается БНФ:
#   exp ::= term {OR term}
#   term ::= factor {AND factor}
#   factor := NOT factor | word | (exp)


def parse_exp(s):
    """
    a OR b OR NOT c OR NOT d
    :param s:
    :return:
    """
    s = s.lstrip().rstrip()
    print "EXP " + s
    term_list = s.split("OR")

    l1 = list()     # прямой тренд
    l2 = list()     # дополнения

    # Распределим постинг-листы по тренду
    for term in term_list:
        new_pl = parse_term(term)
        if new_pl.trend:
            l1.append(new_pl)
        else:
            l2.append(new_pl)

    # OR(NOT xi) = NOT пересечения списков
    l2 = sorted(l2, key=lambda pl: pl.freq)
    while len(l2) > 1:
        l2.insert(0, intersect(l2.pop(0), l2.pop(0)))

    # OR(xi) = Объединение списков
    l1 = sorted(l1, key=lambda pl: -pl.freq)
    while len(l1) > 1:
        l1.insert(0, union(l1.pop(0), l1.pop(0)))

    if len(l1) == 0 and len(l2) == 0:
        return ExtendedPostingList(list(), 0, False)

    if len(l2) == 0:
        return l1.pop()

    if len(l1) == 0:
        return l2.pop()

    # a OR NOT b = NOT (b - a)
    return diff(l2.pop(), l1.pop())


def parse_term(s):
    """
    a AND b AND c AND NOT d AND NOT e
    :param s:
    :return:
    """
    s = s.lstrip().rstrip()
    print "TERM " + s
    factor_list = s.split("AND")
    l1 = list()     # прямой тренд
    l2 = list()     # дополнения

    # Распределим постинг-листы по тренду
    for factor in factor_list:
        new_pl = parse_factor(factor)
        if new_pl.trend:
            l1.append(new_pl)
        else:
            l2.append(new_pl)

    # AND(xi) = Пересечение списков
    l1 = sorted(l1, key=lambda pl: pl.freq)
    while len(l1) > 1:
        l1.insert(0, intersect(l1.pop(0), l1.pop(0)))

    # AND(NOT xi) = NOT объединения списков
    l2 = sorted(l2, key=lambda pl: -pl.freq)
    while len(l2) > 1:
        l2.insert(0, union(l2.pop(0), l2.pop(0)))

    if len(l1) == 0 and len(l2) == 0:
        return ExtendedPostingList(list(), 0)

    if len(l2) == 0:
        return l1.pop()

    if len(l1) == 0:
        return l2.pop()

    # Сольем два суммарных списка x AND NOT y
    return diff(l1.pop(), l2.pop())


def parse_factor(s):
    s = s.lstrip().rstrip()
    if len(s) == 0:
        raise IndexError
    print "FACTOR " + s
    if s[0] == '(' and s[-1] == ')':
        s = s[1:-1]
        return parse_exp(up(s))
    elif s[0:3] == 'NOT':
        s = s[3:]
        return parse_factor(s).build_supplementation()
    else:
        words, freq = find_word(s)
        return ExtendedPostingList(words, freq)

#    def handle_data(self, data=''):
#        """
#        Ищем абзац по обратному индексу
#        """
#        if self.in_dd_tag and self.limit > 0:
#            if self.ex_page_list.trend:
#                if self.ex_page_list.freq > 0 and self.ex_page_list.posting_list[0] == self.page:
#                    s = data.decode('koi8-r')
#
#                    print self.page
#                    print mark_terms_in_snippet(s)
#
#                    self.ex_page_list.pop()
#                    self.limit -= 1
#            else:
#                if self.ex_page_list.freq > 0 and self.ex_page_list.posting_list[0] == self.page:
#                    self.ex_page_list.pop()
#                else:
#                    # номер текущей страницы меньше первого, которого не нужно включать
#                    # или не осталось запрещенных страниц
#                    s = data.decode('koi8-r')
#
#                    print self.page
#                    print mark_terms_in_snippet(s)
#
#                    self.limit -= 1


def mark_terms_in_snippet(s):
    """
    Парсинг и выделение слов в абзаце
    :param s: абзац
    глоб. set_of_marked_terms: термы, которые надо выделить
    :return строка с выделенными токенами
    """
    res = ""
    word = ""
    word_started = False

    s += " "
    for sign in s:
        if word_started:
            if sign.upper() in (RUS_LETTERS + '-'.decode('utf-8')):
                # Слово продолжается
                word += sign
            else:
                # Слово закончилось
                # Надо ли его выделить или оставить в прежнем виде
                set_of_normalized = morph.normalize(word.upper())       # Здесь на совсем плохих токенах бывают косяки

                if type(set_of_normalized).__name__ == 'set' and set_of_normalized & set_of_marked_words:
                    res += word.upper()
                else:
                    res += word
                word_started = False
                res += sign
        else:
            if sign.upper() in RUS_LETTERS:
                # Слово началось
                word = sign
                word_started = True
            else:
                res += sign

    return res


def find_word(word):
    """
    Для всех вариантов нормализации токена выведем список всех похожих термов, по нему - все контексты
    :param word: токен
    :return постинг-лист, частота
    """
    set_of_contexts = set()
    for term in morph.normalize(word):
        print "> н.ф. "
        print term

        try:
            e = IndexElement.objects.select_related("synonyms__song", "song").get(term=term)
            print "Вариант", term
            set_of_marked_words.add(e.term)
            for s in e.song.all():
                set_of_contexts.add(s.id)

            # Добавление синонимов
            for syn in e.synonyms.all():
                set_of_marked_words.add(syn.term)
                for sy_song in syn.song.all():
                    set_of_contexts.add(sy_song.id)
        except IndexElement.DoesNotExist:
            pass
    print "Найдено песен для вариантов слова", word, " с синонимами:", str(len(set_of_contexts))
    page_list = sorted(set_of_contexts)

    return page_list, len(page_list)


def get_posting_list(posting_list):
    global encoding
    if encoding == 0:
        return posting_list


def up(s):
    """
    Преобразования строки для корректной работы с уровнями вложенности
    В верхнем регистре останутся операции только верхнего уровня, по ним парсер будет разбивать строку
    """
    res = ""
    in_brakes = 0
    for symb in s:
        if in_brakes == 0:
            res += symb.upper()
        else:
            res += symb.lower()
        if symb == '(':
            in_brakes += 1
        if symb == ')':
            in_brakes -= 1
    return res


def parse_args():
    """
    Парсинг аргументов командной строки
    """
    c_l_parser = argparse.ArgumentParser(description='Булев поиск')
    c_l_parser.add_argument('-l', type=str, dest='line', help='Разбираемая строка', required=True)
    c_l_parser.add_argument('-n', dest='limit', type=int, default=100500, help='Лимит на результат')
    c_l_parser.add_argument('-e', dest='encoding', type=int, default=0, help='Кодировка постинга:\t1 s9\t 2 vb')
    return c_l_parser.parse_args()


def search(query):
    global encoding
    encoding = 0

    try:
        res = parse_exp(up(query.decode('utf-8').lstrip().rstrip()))
        return OK, res.posting_list

    except IndexError:        
        return ERROR, _("Please, try something easier!")


if __name__ == '__main__':
    status, res = search("кто AND ищет")
    if status == OK:
        for song in Song.objects.filter(id__in=res):
            print song.lyrics

    else:
        print res
