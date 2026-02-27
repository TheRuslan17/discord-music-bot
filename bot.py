import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
import asyncio
from dotenv import load_dotenv
import urllib.parse
import urllib.request
import re
import logging

logging.basicConfig(level=logging.INFO)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
    'no_warnings': True,
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)
queues = {}

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'🎵 Команды: {", ".join([cmd.name for cmd in bot.commands])}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send('❌ Вы должны находиться в голосовом канале!')
        return
    
    channel = ctx.author.voice.channel
    
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
    
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []
    
    if ctx.voice_client.is_playing():
        queues[ctx.guild.id].append(query)
        await ctx.send(f'➕ Добавлен в очередь. Позиция: {len(queues[ctx.guild.id])}')
    else:
        await play_song(ctx, query)

async def play_song(ctx, url):
    voice_client = ctx.voice_client
    if not voice_client:
        return
    
    async with ctx.typing():
        try:
            if not url.startswith('http'):
                search = urllib.parse.urlencode({'search_query': url})
                html = urllib.request.urlopen('http://www.youtube.com/results?' + search)
                video_ids = re.findall(r'/watch\?v=(.{11})', html.read().decode())
                if not video_ids:
                    await ctx.send('❌ Ничего не найдено')
                    return
                url = 'http://www.youtube.com/watch?v=' + video_ids[0]
            
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['url']
                title = info.get('title', 'Неизвестный трек')
            
            voice_client.play(discord.FFmpegPCMAudio(url2, **ffmpeg_options), 
                            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            
            await ctx.send(f'🎵 **{title}**')
            
        except Exception as e:
            await ctx.send(f'❌ Ошибка: {str(e)}')
            await play_next(ctx)

async def play_next(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        url = queues[ctx.guild.id].pop(0)
        await play_song(ctx, url)

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('⏭️ Пропущено')

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send('⏹️ Остановлено')

@bot.command(name='queue')
async def queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queue_list = '\n'.join(f'{i+1}. {q}' for i, q in enumerate(queues[ctx.guild.id][:5]))
        if len(queues[ctx.guild.id]) > 5:
            queue_list += f'\n... и ещё {len(queues[ctx.guild.id]) - 5}'
        await ctx.send(f'📋 **Очередь:**\n{queue_list}')
    else:
        await ctx.send('📭 Очередь пуста')

@bot.command(name='test')
async def test(ctx):
    await ctx.send('✅ Бот работает!')

if __name__ == '__main__':
    if not TOKEN:
        print('❌ ОШИБКА: Токен не найден!')
    else:
        bot.run(TOKEN)