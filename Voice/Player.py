from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError
from discord.ext import commands
import asyncio

class Player:
    QueueURL=[]
    voice_clients={}
    players={}
    volumes={}

    async def _join(self, bot, server_id, voice_channel):
        """Bot joins specific voice channel."""
        if not voice_channel:
            return
        if server_id in self.voice_clients:
            if voice_channel != self.voice_clients[server_id].channel:
                await self.voice_clients[server_id].move_to(voice_channel)
        else:
            voice = await bot.join_voice_channel(voice_channel)
            self.voice_clients[server_id] = voice
            #self.volumes[server_id] = .5
            #why set volume here?

    async def _disconnect(self,ctx):
        """Disconnects from current channel"""
        server_id = ctx.message.server.id
        if server_id not in self.voice_clients:
            await ctx.bot.send_message(ctx.message.channel, "I'm not even in the channel...? :thinking:")
            return
        else:
            await ctx.bot.send_message(ctx.message.channel, "Crunk time over. Wu-tang out!")
            await self.voice_clients[server_id].disconnect()
            del self.voice_clients[server_id]
        return

    def _userinchannel(self,ctx):
        """Checks if user is in channel or same channel as bot. (Take that Nico!). Hardcheck T/F """
        server_id = ctx.message.server.id
        if ctx.message.author.voice.voice_channel is None:
            return False
        elif ctx.message.author.voice.voice_channel is not self.voice_clients[server_id].channel:
            return False
        else:
            return True

    def _addqueue(self,yturl):
        """Adds url to a queue list in case a song is already playing"""
        self.QueueURL.append(yturl)
        return

    def _removequeue(self):
        """Removes first item in queue list"""
        self.QueueURL.pop(0)
        return

    def _is_queue_empty(self):
        if len(self.QueueURL) == 0:
            return True
        else:
            return False

    @commands.command(pass_context=True)
    async def clear(self,ctx):
        """Clears entire queue. Becareful!"""
        self.QueueURL.clear()
        await ctx.bot.send_message(ctx.message.channel, 'Music queue empty. Like this bottle of Gin.')
        return

    @commands.command(pass_context=True)
    async def disconnect(self,ctx):
        await self._disconnect(ctx)
        return

    @commands.command(pass_context=True)
    async def queue(self,ctx):
        """Shows current queued items"""
        await ctx.bot.send_message(ctx.message.channel, "We have about {} songs in queue".format(len(self.QueueURL)) )
        await ctx.bot.send_message(ctx.message.channel, self.QueueURL)

    def _autoplay(self,ctx):
        server_id = ctx.message.server.id
        ytdl_opts = {'format': 'bestaudio/webm[abr>0]/best'}
        if self._is_queue_empty():
            asyncio.run_coroutine_threadsafe(self._disconnect(ctx),ctx.bot.loop).result()
            return
        corocall = self.voice_clients[server_id].create_ytdl_player(self.QueueURL[0], ytdl_options=ytdl_opts, after=lambda: self._autoplay(ctx))
        scheduling = asyncio.run_coroutine_threadsafe(corocall,ctx.bot.loop)
        try:
            self.players[server_id] = scheduling.result()
        except Exception as e:
            print(e)
            return #oh no.
        self.players[server_id].start()
        self._removequeue()
        return

    async def _play(self,ctx,url):
        """Plays youtube links. IE 'https://www.youtube.com/watch?v=mPMC3GYpBHg' """
        server_id = ctx.message.server.id
        await self._join(ctx.bot, server_id, ctx.message.author.voice.voice_channel)
        try:
            ytdl_opts = {'format': 'bestaudio/webm[abr>0]/best'}
            self.players[server_id] = await self.voice_clients[server_id].create_ytdl_player(url, ytdl_options=ytdl_opts, after=lambda: self._autoplay(ctx))
        except:
                #raise BadArgument()
            return False
        self.players[server_id].volume = self.volumes[server_id]
        self.players[server_id].start()
        return True

    @commands.command(pass_context=True)
    async def play(self,ctx,url):
        """Plays youtube links. IE 'https://www.youtube.com/watch?v=mPMC3GYpBHg' """
        #create ytdl instance
        #set quiet: True if needed
        ytdl_opts = {'quiet': False, 'noplaylist': True, 'playlist_items': '1'}
        ytdl = YoutubeDL(ytdl_opts)
        validation_play_check = False
        server_id = ctx.message.server.id
        try:
            info = ytdl.extract_info(url, download=False)
        except DownloadError:
            #url was bullshit
            await ctx.bot.send_message(ctx.message.channel, "Unsupported URL, I'll try to find a video.")
            search_kw = str(ctx.message.content)
            search_kw = search_kw[5:]
            await ctx.bot.send_message(ctx.message.channel, "searching: {}".format(search_kw))
            yt_search = {'default_search':'ytsearch1', 'quiet':False}
            ytdl = YoutubeDL(yt_search)
            info = ytdl.extract_info(search_kw, download=False)
            if 'entries' not in info:
                await ctx.bot.send_message(ctx.message.channel, "Critical failure.")
                return
            await ctx.bot.send_message(ctx.message.channel, "{} hits.".format(len(info['entries'])))
            if len(info['entries']) <= 0:
                return
            info = info['entries'][0]
            url = info.get('webpage_url')
        if 'entries' in info:
            #it's a playlist
            await ctx.bot.send_message(ctx.message.channel, "Entire playlists are not supported")
            return
        if not self._is_queue_empty():
            await ctx.bot.send_message(ctx.message.channel, "I'm already playing something but I'll add it to the queue!")
            self._addqueue(url)
            return
        if server_id not in self.voice_clients:
            self._addqueue(url)
            validation_play_check = await self._play(ctx,self.QueueURL[0])
            self._removequeue()
            return
        if server_id in self.players: #This is gross, fix later.
            if self.players[server_id].is_playing():
                await ctx.bot.send_message(ctx.message.channel, "I'm already playing something but I'll add it to the queue!")
                self._addqueue(url)
                return
        self._addqueue(url)
        validation_play_check = await self._play(ctx,self.QueueURL[0])
        if not validation_play_check:
            await ctx.bot.send_message(ctx.message.channel, "Playback failed!")
        self._removequeue()
        return


    @commands.command(pass_context=True)
    async def next(self,ctx):
        """Plays song next in queue."""
        server_id = ctx.message.server.id
        if server_id not in self.voice_clients:
            await ctx.bot.send_message(ctx.message.channel, 'Bruh, I\'m not even in a channel. :thinking:')
            return
        elif self._is_queue_empty():
            await ctx.bot.send_message(ctx.message.channel, 'We ain\'t got no more tunes! Pass the AUX cord!!!!! :pray::skin-tone-4:')
            return
        elif server_id not in self.players:
            await self._play(ctx,self.QueueURL[0])
            self._removequeue()
            return
        elif not self._userinchannel(ctx):
            await ctx.bot.send_message(ctx.message.channel, "Nice try. :information_desk_person::skin-tone-4: ")
            return
        else:
            self.players[server_id].pause()
            await self._play(ctx,self.QueueURL[0])
            self._removequeue()
            await ctx.bot.send_message(ctx.message.channel, 'Here we go skipping again!')
            return

    @commands.command(pass_context=True)
    async def pause(self,ctx):
        """Pauses song"""
        server_id = ctx.message.server.id
        if server_id not in self.voice_clients:
            await ctx.bot.send_message(ctx.message.channel, "Pause? When I'm not there? ....Really?")
            return
        elif server_id not in self.players:
            await ctx.bot.send_message(ctx.message.channel, "I'm not playing anything")
            return
        elif not self.players[server_id].is_playing():
            await ctx.bot.send_message(ctx.message.channel, "I'm not playing anything")
            return
        elif not self._userinchannel(ctx):
            await ctx.bot.send_message(ctx.message.channel, "Nice try. :information_desk_person::skin-tone-4: ")
            return
        else:
            self.players[server_id].pause()
            await ctx.bot.send_message(ctx.message.channel, "Playback paused.")
            return

    @commands.command(pass_context=True)
    async def resume(self,ctx):
        """Resumes playback"""
        server_id = ctx.message.server.id
        if server_id not in self.voice_clients:
            await ctx.bot.send_message(ctx.message.channel, "Resume? When I'm not there? ....Really?")
            return
        elif server_id not in self.players:
            await ctx.bot.send_message(ctx.message.channel, "I'm not playing anything")
            return
        elif self.players[server_id].is_playing():
            await ctx.bot.send_message(ctx.message.channel, "I'm already playing something.")
            return
        elif not self._userinchannel(ctx):
            await ctx.bot.send_message(ctx.message.channel, "Nice try. :information_desk_person::skin-tone-4: ")
            return
        else:
            self.players[server_id].resume()
            await ctx.bot.send_message(ctx.message.channel, "Playback paused.")
            return

    def format_volume_bar(self, value):
        """Returns the volume bar string. Expects value = [0.0-2.0]"""
        length = 20
        full = int(value / 2.0 * length)
        bar = "``{}{} {:.0f}%``".format('█' * full, '-' * (length - full), value * 100)
        return bar

    @commands.command(pass_context=True)
    async def setvolume(self,ctx, vol):
        """Sets volume between 0 and 200."""
        server_id = ctx.message.server.id
        vol = int(vol)
        if vol > 200 or vol < 0:
            return False
        elif not self._userinchannel(ctx):
            return False
        else:
            self.volumes[server_id] = vol/100
            await ctx.bot.send_message(ctx.message.channel, self.format_volume_bar(self.volumes[server_id]))
            if server_id in self.players:
                self.players[server_id].volume = self.volumes[server_id]
                return True
            return True
        return
