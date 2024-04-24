import sys
import re
import json

import requests
from urllib.parse import urlencode, parse_qsl

import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc

addon = xbmcaddon.Addon

PLUGIN_URL      = sys.argv[0]
PLUGIN_HANDLE   = int(sys.argv[1])
AANBA_URL       = 'https://aanba.ru'

def getBroadcasts():
    response = requests.get(AANBA_URL)
    if not response.ok:
        return []

    scheduleBlock = re.search('<div class="col-md-12 h3 text-center">Расписание</div>[\s\S]*?(?=<div class="custom)', response.text)
    if not scheduleBlock:
        return []

    schedulesData = re.findall('<div class="col-xs-12 col-md-6 jbzoo-item jbzoo-item-match jbzoo-item-full">.*data_date="(.*?)">[\s\S]*?title="(.*?)"[\s\S]*?src="(.*?)"[\s\S]*?<span class="mf-31">([\s\S]*?)<\/span>[\s\S]*?title="(.*?)"[\s\S]*?src="(.*?)"', scheduleBlock.group(0))
    if not schedulesData:
        return []

    casts = re.search('<ul class="nav nav-tabs" id="broadcasts">[\s\S]*<div class="col-md-3 p-no">', response.text)
    if not casts:
        return []

    titles = re.findall('<a data-toggle="tab" href="#\S*">(.*)</a></li>', casts.group(0))
    if not titles:
        return []

    links = re.findall('<iframe.*src="(.*?)".*</iframe>', casts.group(0))

    if len(titles) != len(links):
        return []

    result = []
    for i in range(len(titles)):
        castTitle = titles[i]
        castDate = ''
        castTime = ''
        team1Logo = ''
        team2Logo = ''
        poster = ''
        castLink = ''
        castUrl = ''
        plot = ''
        
        for scheduleData in schedulesData:
            scheduleTitle = '{} – {}'.format(scheduleData[1].strip(), scheduleData[4].strip())
            if len(scheduleData) == 6 and scheduleTitle == castTitle:
                castDate = scheduleData[0].strip()
                castTime = scheduleData[3].strip()
                team1Logo = scheduleData[2].strip()
                team2Logo = scheduleData[5].strip()

        if re.search('kinescope.io', links[i]):
            response = requests.get(links[i])
            if response.ok:
                scriptData = re.search('<script type="application\/ld\+json">([\s\S]*?)<\/script>', response.text)
                if scriptData:
                    try:
                        data = json.loads(scriptData.group(1))
                        castUrl = data['contentUrl'].strip()
                        poster = data['thumbnailUrl'].strip()
                        plot = castDate + '\n' + castTime + '\n\n' + data['description'].strip().replace('\\n', '\n')
                    except:
                        castUrl = ''

        elif re.search('youtube.com', links[i]):
            link = links[i].replace('embed/', 'watch?v=')
            if re.search('watch\?v=.*', link):
                response = requests.get(link)
                if response.ok:
                    castUrl = link
                    playerData = re.search('var ytInitialPlayerResponse =([\s\S]*?);(var meta =|<\/script>)', response.text)
                    if playerData:
                        try:
                            data = json.loads(playerData.group(1))
                            plot = data['videoDetails']['shortDescription'].strip().replace('\\n', '\n')
                            thumbs = data['videoDetails']['thumbnail']['thumbnails']
                            poster = thumbs[len(thumbs) - 1]['url']
                            #castTitle = data['videoDetails']['title']
                        except:
                            castUrl = ''

        if xbmcplugin.getSetting(PLUGIN_HANDLE, 'onlineOnly') != 'true' or castTime != '':
            result.append({'title': castTitle, 'url': castUrl, 'plot': plot, 'poster': poster})

    return result

def main(paramStr):
    params = dict(parse_qsl(paramStr))

    if not params:
        xbmcplugin.setContent(PLUGIN_HANDLE, "videos")
        xbmcplugin.setPluginCategory(PLUGIN_HANDLE, 'aanba.ru Live')

        broadcasts = getBroadcasts()

        for broadcast in broadcasts:
            listItem = xbmcgui.ListItem(broadcast['title'])
            listItem.setArt({'thumb' : broadcast['poster'], 'poster' : broadcast['poster']})
        
            infoTag = listItem.getVideoInfoTag()
            infoTag.setMediaType("video")
            infoTag.setTitle(broadcast['title'])
            infoTag.setPlot(broadcast['plot'])
            infoTag.setPath(broadcast['url'])
        
            url = '{}?{}'.format(PLUGIN_URL, 'video=' + broadcast['url'])

            listItem.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(PLUGIN_HANDLE, url, listItem, False)

        xbmcplugin.endOfDirectory(PLUGIN_HANDLE, True, True, False)

    elif params['video'] != '':

        castUrl = params['video']
        if re.search('youtube.com', castUrl):
            id = re.search('watch\?v=(.*)', castUrl)
            castUrl = 'plugin://plugin.video.youtube/play/?video_id=' + id.group(1)
            xbmc.executebuiltin('RunPlugin({})'.format(castUrl))
        else:
            xbmc.executebuiltin('PlayMedia({})'.format(castUrl))

if __name__ == '__main__':
    main(sys.argv[2][1:])