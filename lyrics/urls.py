from django.conf.urls import patterns, url, include
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'lyrics.views.song_list', name='song_list'),
    url(r'^song/(?P<song_id>\d+)/$', 'lyrics.views.song_detail', name='song')
)
