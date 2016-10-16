import xbmc
import xbmcgui
import kodigui

from lib import colors
from lib import util

from plexnet import playlist

import busy
import musicplayer
import videoplayer
import dropdown
import windowutils
import opener
import search


class EpisodesWindow(kodigui.BaseWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-episodes.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_AR16X9_DIM = (178, 100)
    POSTER_DIM = (420, 630)

    EPISODE_PANEL_ID = 101
    LIST_OPTIONS_BUTTON_ID = 111

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202
    PLAYER_STATUS_BUTTON_ID = 204

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.season = kwargs.get('season')
        self.parentList = kwargs.get('parentList')
        self.seasons = None
        self.show = kwargs.get('show')
        self.exitCommand = None

    def onFirstInit(self):
        self.episodePanelControl = kodigui.ManagedControlList(self, self.EPISODE_PANEL_ID, 5)

        self.setup()
        self.setFocusId(self.EPISODE_PANEL_ID)
        self.checkForHeaderFocus(xbmcgui.ACTION_MOVE_DOWN)

    def setup(self):
        self.updateProperties()
        self.fillEpisodes()

    def onAction(self, action):
        controlID = self.getFocusId()
        try:
            if action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.next()
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                self.next()
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.prev()

            if controlID == self.EPISODE_PANEL_ID:
                self.checkForHeaderFocus(action)
            if controlID == self.LIST_OPTIONS_BUTTON_ID and self.checkOptionsAction(action):
                return
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def checkOptionsAction(self, action):
        if action == xbmcgui.ACTION_MOVE_UP:
            mli = self.episodePanelControl.getSelectedItem()
            if not mli:
                return False
            pos = mli.pos() - 1
            if self.episodePanelControl.positionIsValid(pos):
                self.setFocusId(self.EPISODE_PANEL_ID)
                self.episodePanelControl.selectItem(pos)
            return True
        elif action == xbmcgui.ACTION_MOVE_DOWN:
            mli = self.episodePanelControl.getSelectedItem()
            if not mli:
                return False
            pos = mli.pos() + 1
            if self.episodePanelControl.positionIsValid(pos):
                self.setFocusId(self.EPISODE_PANEL_ID)
                self.episodePanelControl.selectItem(pos)
            return True

        return False

    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.closeWithCommand('HOME')
        elif controlID == self.EPISODE_PANEL_ID:
            self.episodePanelClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.LIST_OPTIONS_BUTTON_ID:
            mli = self.episodePanelControl.getSelectedItem()
            if mli:
                self.optionsButtonClicked(mli)
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

    def getSeasons(self):
        if not self.seasons:
            if self.season.TYPE == 'season':
                self.seasons = self.season.show().seasons()
            elif self.season.TYPE == 'album':
                self.seasons = self.season.artist().albums()

        if not self.seasons:
            return False

        return True

    def next(self):
        if not self._next():
            return
        self.setup()

    @busy.dialog()
    def _next(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.season)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.season = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getSeasons():
                return False

            if self.season not in self.seasons:
                return False

            pos = self.seasons.index(self.season)
            pos += 1
            if pos >= len(self.seasons):
                pos = 0

            self.season = self.seasons[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.season)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.season = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getSeasons():
                return False

            if self.season not in self.seasons:
                return False

            pos = self.seasons.index(self.season)
            pos -= 1
            if pos < 0:
                pos = len(self.seasons) - 1

            self.season = self.seasons[pos]

        return True

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.season.getLibrarySectionId() or None))

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.season.all(), self.season.getServer())
        pl.shuffle(shuffle, first=True)
        videoplayer.play(play_queue=pl)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def episodePanelClicked(self):
        mli = self.episodePanelControl.getSelectedItem()
        if not mli:
            return

        command = opener.open(mli.dataSource)
        if mli.dataSource.exists():
            mli.setProperty('watched', mli.dataSource.isWatched and '1' or '')
            self.season.reload()
            self.processCommand(command)
        else:
            self.episodePanelControl.removeItem(mli.pos())

            if not self.episodePanelControl.size():
                self.closeWithCommand(command)

    def optionsButtonClicked(self, item=None):
        options = []

        if item:
            if item.dataSource.isWatched:
                options.append({'key': 'mark_unwatched', 'display': 'Mark Unwatched'})
            else:
                options.append({'key': 'mark_watched', 'display': 'Mark Watched'})

            if True:
                options.append({'key': 'add_to_playlist', 'display': '[COLOR FF808080]Add To Playlist[/COLOR]'})
        else:
            if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
                options.append({'key': 'play_next', 'display': 'Play Next'})

            if not isinstance(self, AlbumWindow):
                if self.season.isWatched:
                    options.append({'key': 'mark_unwatched', 'display': 'Mark Unwatched'})
                else:
                    options.append({'key': 'mark_watched', 'display': 'Mark Watched'})

            # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
            #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

            if options:
                options.append(dropdown.SEPARATOR)

            options.append({'key': 'to_show', 'display': isinstance(self, AlbumWindow) and 'Go to Artist' or 'Go To Show'})
            options.append({'key': 'to_section', 'display': u'Go to {0}'.format(self.season.getLibrarySectionTitle())})

        pos = (460, 1106)
        bottom = True
        setDropdownProp = False
        if item:
            viewPos = self.episodePanelControl.getViewPosition()
            if viewPos > 6:
                pos = (1490, 312 + (viewPos * 100))
                bottom = True
            else:
                pos = (1490, 167 + (viewPos * 100))
                bottom = False
            setDropdownProp = True
        choice = dropdown.showDropdown(options, pos, pos_is_bottom=bottom, close_direction='right', set_dropdown_prop=setDropdownProp)
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            media = item and item.dataSource or self.season
            media.markWatched()
            self.updateItems(item)
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_unwatched':
            media = item and item.dataSource or self.season
            media.markUnwatched()
            self.updateItems(item)
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'to_show':
            self.processCommand(opener.open(self.season.parentRatingKey))
        elif choice['key'] == 'to_section':
            self.closeWithCommand('HOME:{0}'.format(self.season.getLibrarySectionId()))

    def checkForHeaderFocus(self, action):
        if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
            if self.episodePanelControl.getSelectedItem().getProperty('is.header'):
                xbmc.executebuiltin('Action(up)')
        if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
            if self.episodePanelControl.getSelectedItem().getProperty('is.header'):
                xbmc.executebuiltin('Action(down)')

    def updateProperties(self):
        self.setProperty(
            'background',
            (self.show or self.season.show()).art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('season.thumb', self.season.thumb.asTranscodedImageURL(*self.POSTER_DIM))
        self.setProperty('show.title', self.show and self.show.title or '')
        self.setProperty('season.title', self.season.title)

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(
            obj.title, obj.originallyAvailableAt.asDatetime('%b %d, %Y'), thumbnailImage=obj.thumb.asTranscodedImageURL(*self.THUMB_AR16X9_DIM), data_source=obj
        )
        mli.setProperty('episode.number', str(obj.index) or '')
        mli.setProperty('episode.duration', util.durationToText(obj.duration.asInt()))
        mli.setProperty('watched', obj.isWatched and '1' or '')
        return mli

    def updateItems(self, item=None):
        if item:
            self.season.reload()
            item.setProperty('watched', item.dataSource.isWatched and '1' or '')
        else:
            self.fillEpisodes(update=True)

    @busy.dialog()
    def fillEpisodes(self, update=False):
        items = []
        idx = 0
        for episode in self.season.episodes():
            mli = self.createListItem(episode)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.episodePanelControl.replaceItems(items)


class AlbumWindow(EpisodesWindow):
    xmlFile = 'script-plex-album.xml'

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.season.all(), self.season.getServer())
        pl.startShuffled = shuffle
        self.openWindow(musicplayer.MusicPlayerWindow, track=pl.current(), playlist=pl)

    def episodePanelClicked(self):
        mli = self.episodePanelControl.getSelectedItem()
        if not mli:
            return

        self.openWindow(musicplayer.MusicPlayerWindow, track=mli.dataSource, album=self.season)

    def updateProperties(self):
        self.setProperty(
            'background',
            self.season.art.asTranscodedImageURL(self.width, self.height, blur=128, opacity=60, background=colors.noAlpha.Background)
        )
        self.setProperty('season.thumb', self.season.thumb.asTranscodedImageURL(*self.POSTER_DIM))
        self.setProperty('artist.title', self.season.parentTitle or '')
        self.setProperty('album.title', self.season.title)

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title, data_source=obj)
        mli.setProperty('track.number', str(obj.index) or '')
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(obj.duration.asInt()))
        return mli

    @busy.dialog()
    def fillEpisodes(self):
        items = []
        idx = 0
        multiDisc = 0

        for track in self.season.tracks():
            disc = track.parentIndex.asInt()
            if disc > 1:
                if not multiDisc:
                    items.insert(0, kodigui.ManagedListItem('DISC 1', properties={'is.header': '1'}))

                if disc != multiDisc:
                    items[-1].setProperty('is.footer', '1')
                    multiDisc = disc
                    items.append(kodigui.ManagedListItem('DISC {0}'.format(disc), properties={'is.header': '1'}))

            mli = self.createListItem(track)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty('artist', self.season.parentTitle)
                mli.setProperty('disc', str(disc))
                mli.setProperty('album', self.season.title)
                mli.setProperty('number', '{0:0>2}'.format(track.index))
                items.append(mli)
                idx += 1

        if items:
            items[-1].setProperty('is.footer', '1')

        self.episodePanelControl.replaceItems(items)
