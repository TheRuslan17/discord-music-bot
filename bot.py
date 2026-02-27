import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
import asyncio
from dotenv import load_dotenv
import urllib.parse
import urllib.request
import re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Прямой путь к вашему FFmpeg
FFMPEG_PATH = r"D:\FFmpeg\ffmpeg-2026-02-26-git-6695528af6-full_build\bin\ffmpeg.exe"

# Настройки для yt-dlp
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

# Настройки FFmpeg с прямым путем
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
    'executable': FFMPEG_PATH
}

# Включаем все необходимые намерения
intents = discord.Intents.default()
intents.message_content = True  # Это критически важно!
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Очереди для каждого сервера
queues = {}

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'📁 FFmpeg путь: {FFMPEG_PATH}')
    print(f'📊 Намерения включены: message_content={intents.message_content}')
    print(f'🎵 Команды загружены: {len(bot.commands)}')
    print(f'📋 Список команд: {", ".join([cmd.name for cmd in bot.commands])}')

@bot.event
async def on_message(message):
    # Не реагируем на свои сообщения
    if message.author == bot.user:
        return
    
    # Выводим в консоль для отладки
    print(f'📨 Получено сообщение: "{message.content}" от {message.author}')
    
    # Важно! Нужно вызвать эту функцию для обработки команд
    await bot.process_commands(message)

@bot.command(name='test')
async def test(ctx):
    """Тестовая команда"""
    await ctx.send('✅ Бот работает! Команда получена.')
    print('✅ Тестовая команда выполнена')

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query):
    """Подключается к каналу и добавляет трек в очередь"""
    print(f'🎵 Команда play получена: {query}')
    
    # Проверяем, находится ли пользователь в голосовом канале
    if not ctx.author.voice:
        await ctx.send('❌ Вы должны находиться в голосовом канале!')
        return
    
    channel = ctx.author.voice.channel
    print(f'🔊 Голосовой канал: {channel.name}')
    
    # Подключаемся к голосовому каналу
    if ctx.voice_client is None:
        await channel.connect()
        print('✅ Подключились к каналу')
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
        print('✅ Переместились в канал')
    
    # Инициализируем очередь для сервера
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []
    
    # Если бот уже играет, добавляем в очередь
    if ctx.voice_client.is_playing():
        queues[ctx.guild.id].append(query)
        position = len(queues[ctx.guild.id])
        await ctx.send(f'➕ Трек добавлен в очередь. Позиция: {position}')
        print(f'➕ Добавлено в очередь: {query}')
    else:
        # Иначе играем сразу
        print(f'🎯 Начинаем воспроизведение: {query}')
        await play_song(ctx, query)

async def play_song(ctx, url):
    """Воспроизводит конкретную песню"""
    voice_client = ctx.voice_client
    if not voice_client:
        return
    
    async with ctx.typing():
        try:
            # Проверяем, является ли ввод ссылкой или поисковым запросом
            if not url.startswith('http'):
                # Поиск на YouTube
                print(f'🔍 Ищем: {url}')
                search = urllib.parse.urlencode({'search_query': url})
                html = urllib.request.urlopen('http://www.youtube.com/results?' + search)
                video_ids = re.findall(r'/watch\?v=(.{11})', html.read().decode())
                if not video_ids:
                    await ctx.send('❌ Ничего не найдено')
                    return
                url = 'http://www.youtube.com/watch?v=' + video_ids[0]
                print(f'✅ Найдено видео: {url}')
            
            # Получаем информацию о видео
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['url']
                title = info.get('title', 'Неизвестный трек')
                print(f'🎵 Трек: {title}')
            
            # Воспроизводим аудио
            voice_client.play(discord.FFmpegPCMAudio(url2, **ffmpeg_options), 
                            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            
            await ctx.send(f'🎵 **{title}**')
            print(f'▶️ Начало воспроизведения: {title}')
            
        except Exception as e:
            await ctx.send(f'❌ Ошибка при воспроизведении: {str(e)}')
            print(f'❌ Ошибка: {str(e)}')

async def play_next(ctx):
    """Воспроизводит следующий трек в очереди"""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        url = queues[ctx.guild.id].pop(0)
        print(f'⏭️ Следующий трек из очереди')
        await play_song(ctx, url)

@bot.command(name='skip')
async def skip(ctx):
    """Пропускает текущий трек"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('⏭️ Трек пропущен')
        print('⏭️ Трек пропущен')
    else:
        await ctx.send('❌ Сейчас ничего не играет')

@bot.command(name='stop')
async def stop(ctx):
    """Останавливает воспроизведение и очищает очередь"""
    if ctx.voice_client:
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send('⏹️ Воспроизведение остановлено')
        print('⏹️ Бот отключен')
    else:
        await ctx.send('❌ Бот не в голосовом канале')

@bot.command(name='queue')
async def queue(ctx):
    """Показывает текущую очередь"""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queue_list = '\n'.join(f'{i+1}. {q}' for i, q in enumerate(queues[ctx.guild.id][:5]))
        if len(queues[ctx.guild.id]) > 5:
            queue_list += f'\n... и ещё {len(queues[ctx.guild.id]) - 5}'
        await ctx.send(f'📋 **Очередь:**\n{queue_list}')
        print(f'📋 Показана очередь ({len(queues[ctx.guild.id])} треков)')
    else:
        await ctx.send('📭 Очередь пуста')

if __name__ == '__main__':
    if not TOKEN:
        print('❌ ОШИБКА: Токен не найден в файле .env!')
    else:
        print('🚀 Запуск бота...')
        bot.run(TOKEN)