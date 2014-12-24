from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse


class Song(models.Model):
    aid      = models.IntegerField(_('aid'), unique=True)
    artist   = models.CharField(_('artist'), max_length=128)
    title    = models.CharField(_('title'), max_length=128)
    duration = models.IntegerField(_('duration'))
    url      = models.URLField(_('url'), max_length=100)
    lyrics   = models.TextField(_('lyrics'))
    linked_movie = models.TextField(_('movie'), max_length=128, blank=True, null=True, default=None)
    rude = models.BooleanField(_('rude'), default=False)
    map_of_normalized_words = models.TextField(_('map_norm'), default="")

    def am_i_song_from_movie(self):
        return self.linked_movie is not None

    def __unicode__(self):
        return self.artist + ' - ' + "'" + self.title + "'"

    def get_absolute_url(self):
        return reverse('song', args=[str(self.id)])

    class Meta:
        verbose_name = _('song')
        verbose_name_plural = _('songs')
        ordering = ['title',]


class IndexElement(models.Model):
    term = models.CharField(_('term'), unique=True, max_length=100)
    song = models.ManyToManyField(Song)
    synonyms = models.ManyToManyField("self", symmetrical=False, related_name='im_syn_of')

    def __unicode__(self):
        return self.term

    def get_linked_songs_amount(self):
        return len(self.song.objects.all())

    class Meta:
        ordering = ['term', ]
