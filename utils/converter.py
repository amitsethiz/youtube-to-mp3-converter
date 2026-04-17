"""
YouTube Converter Utility
Handles downloading and conversion of YouTube videos to MP3/MP4.

Strategy:
  1. Try yt-dlp directly (with multiple player clients)
  2. On bot-block failure, fall back to Invidious public API (no auth needed)
     - Fetch video metadata and CDN stream URLs via Invidious REST API
     - Download the raw audio stream with requests
     - Convert to MP3/MP4 using bundled ffmpeg
"""

import os
import re
import subprocess
import tempfile
import logging
import requests

import yt_dlp

# ---------------------------------------------------------------------------
# Bundled FFmpeg (imageio-ffmpeg) — works on Render without system install
# ---------------------------------------------------------------------------
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = 'ffmpeg'  # Fallback to system ffmpeg

# ---------------------------------------------------------------------------
# Public Invidious instances used as fallback when YouTube blocks the server
# These are community-run proxies that don't require authentication
# ---------------------------------------------------------------------------
INVIDIOUS_INSTANCES = [
    'https://invidious.fdn.fr',
    'https://yt.artemislena.eu',
    'https://inv.nadeko.net',
    'https://invidious.nerdvpn.de',
    'https://iv.datura.network',
]

logger = logging.getLogger(__name__)


class YouTubeConverter:
    """
    Handles YouTube video downloading and MP3/MP4 conversion.
    Uses yt-dlp as primary engine with Invidious as an automatic fallback.
    """

    def __init__(self, temp_dir=None, downloads_dir=None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.downloads_dir = downloads_dir or os.path.join(os.getcwd(), 'downloads')

        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)

        # yt-dlp base options — try several player clients to bypass bot checks
        self.ydl_base_opts = {
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # tv_embedded → ios → android_vr → mweb (escalating bypass attempts)
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded', 'ios', 'android_vr', 'mweb'],
                    'player_skip': ['webpage'],   # skip webpage fetch → less bot signals
                }
            },
            'ffmpeg_location': FFMPEG_PATH,
        }

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def get_video_info(self, url):
        """
        Return video metadata dict or None.
        Tries yt-dlp first; falls back to Invidious API automatically.
        """
        # --- Primary: yt-dlp ---
        try:
            with yt_dlp.YoutubeDL(self.ydl_base_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return {
                        'title': info.get('title', 'Unknown Title'),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'uploader': info.get('uploader', 'Unknown Uploader'),
                        'view_count': info.get('view_count', 0),
                        'upload_date': info.get('upload_date', ''),
                        'description': (info.get('description') or '')[:200],
                        'webpage_url': info.get('webpage_url', url),
                    }
        except Exception as e:
            logger.warning(f"yt-dlp info extraction failed ({e}), trying Invidious…")

        # --- Fallback: Invidious REST API ---
        video_id = self._extract_video_id(url)
        if video_id:
            return self._get_info_via_invidious(video_id)
        return None

    def convert_to_mp3(self, url, quality='192k', status_callback=None,
                       start_time=None, end_time=None):
        """
        Download + convert to MP3.  Falls back to Invidious on bot-block.
        Returns path to the MP3 file, or None on failure.
        """
        numeric_quality = quality.rstrip('kK')

        # --- Primary: yt-dlp ---
        mp3_file = self._ytdlp_to_mp3(url, numeric_quality, status_callback)
        if mp3_file:
            return self._maybe_crop(mp3_file, start_time, end_time, status_callback)

        # --- Fallback: Invidious ---
        logger.warning("yt-dlp MP3 conversion blocked, falling back to Invidious…")
        video_id = self._extract_video_id(url)
        if video_id:
            mp3_file = self._invidious_to_mp3(video_id, numeric_quality, status_callback)
            if mp3_file:
                return self._maybe_crop(mp3_file, start_time, end_time, status_callback)

        if status_callback:
            status_callback.update({'status': 'error', 'progress': 0,
                                    'message': 'Conversion failed — YouTube is blocking this server.'})
        return None

    def convert_to_mp4(self, url, quality='720p', status_callback=None):
        """
        Download as MP4.  Falls back to Invidious on bot-block.
        Returns path to the MP4 file, or None on failure.
        """
        # --- Primary: yt-dlp ---
        mp4_file = self._ytdlp_to_mp4(url, quality, status_callback)
        if mp4_file:
            return mp4_file

        # --- Fallback: Invidious ---
        logger.warning("yt-dlp MP4 download blocked, falling back to Invidious…")
        video_id = self._extract_video_id(url)
        if video_id:
            return self._invidious_to_mp4(video_id, quality, status_callback)

        if status_callback:
            status_callback.update({'status': 'error', 'progress': 0,
                                    'message': 'Download failed — YouTube is blocking this server.'})
        return None

    # -----------------------------------------------------------------------
    # yt-dlp helpers
    # -----------------------------------------------------------------------

    def _ytdlp_to_mp3(self, url, numeric_quality, status_callback):
        try:
            if status_callback:
                status_callback.update({'status': 'downloading', 'progress': 10,
                                        'message': 'Connecting to YouTube…'})
            outtmpl = os.path.join(self.downloads_dir, f'%(title)s_{numeric_quality}k.%(ext)s')
            opts = {
                **self.ydl_base_opts,
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': numeric_quality,
                }],
            }
            downloaded_path = [None]

            def hook(d):
                if d['status'] == 'downloading' and status_callback:
                    status_callback.update({'progress': 50, 'message': 'Downloading audio…'})
                elif d['status'] == 'finished':
                    downloaded_path[0] = d['filename']
                    if status_callback:
                        status_callback.update({'status': 'converting', 'progress': 80,
                                                'message': 'Converting to MP3…'})

            opts['progress_hooks'] = [hook]
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None

            return self._resolve_output(downloaded_path[0], '.mp3')
        except Exception as e:
            logger.warning(f"yt-dlp MP3 error: {e}")
            return None

    def _ytdlp_to_mp4(self, url, quality, status_callback):
        try:
            if status_callback:
                status_callback.update({'status': 'downloading', 'progress': 10,
                                        'message': 'Connecting to YouTube…'})
            q_num = quality.replace('p', '')
            fmt = f'bestvideo[ext=mp4][height<={q_num}]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            outtmpl = os.path.join(self.downloads_dir, f'%(title)s_{quality}.%(ext)s')
            opts = {
                **self.ydl_base_opts,
                'format': fmt,
                'outtmpl': outtmpl,
                'merge_output_format': 'mp4',
            }
            downloaded_path = [None]

            def hook(d):
                if d['status'] == 'downloading' and status_callback:
                    status_callback.update({'progress': 50, 'message': 'Downloading video…'})
                elif d['status'] == 'finished':
                    downloaded_path[0] = (d.get('info_dict') or {}).get('_filename') or d.get('filename')
                    if status_callback:
                        status_callback.update({'status': 'converting', 'progress': 80,
                                                'message': 'Processing MP4…'})

            opts['progress_hooks'] = [hook]
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None

            return self._resolve_output(downloaded_path[0], '.mp4')
        except Exception as e:
            logger.warning(f"yt-dlp MP4 error: {e}")
            return None

    # -----------------------------------------------------------------------
    # Invidious fallback helpers
    # -----------------------------------------------------------------------

    def _get_info_via_invidious(self, video_id):
        """Fetch video metadata from a public Invidious instance."""
        for instance in INVIDIOUS_INSTANCES:
            try:
                r = requests.get(f'{instance}/api/v1/videos/{video_id}',
                                 timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code == 200:
                    data = r.json()
                    thumbs = data.get('videoThumbnails', [])
                    thumb = next((t['url'] for t in thumbs if t.get('quality') == 'high'), '')
                    if thumb and thumb.startswith('/'):
                        thumb = instance + thumb
                    logger.info(f"Invidious info OK via {instance}")
                    return {
                        'title': data.get('title', 'Unknown Title'),
                        'duration': data.get('lengthSeconds', 0),
                        'thumbnail': thumb,
                        'uploader': data.get('author', 'Unknown Uploader'),
                        'view_count': data.get('viewCount', 0),
                        'upload_date': '',
                        'description': (data.get('description') or '')[:200],
                        'webpage_url': f'https://www.youtube.com/watch?v={video_id}',
                    }
            except Exception as e:
                logger.warning(f"Invidious info failed ({instance}): {e}")
        return None

    def _invidious_to_mp3(self, video_id, numeric_quality, status_callback):
        """
        Download best audio stream via Invidious CDN proxy, then convert to MP3 with ffmpeg.
        The Invidious /api/v1/videos endpoint returns pre-signed googlevideo.com URLs
        that don't require YouTube authentication.
        """
        if status_callback:
            status_callback.update({'status': 'downloading', 'progress': 15,
                                    'message': 'Connecting via mirror server…'})

        for instance in INVIDIOUS_INSTANCES:
            try:
                r = requests.get(f'{instance}/api/v1/videos/{video_id}',
                                 timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code != 200:
                    continue

                data = r.json()
                # Pick best audio-only adaptive format (prefer opus/webm at highest bitrate)
                audio_formats = [
                    f for f in data.get('adaptiveFormats', [])
                    if f.get('type', '').startswith('audio/')
                ]
                if not audio_formats:
                    continue

                audio_formats.sort(key=lambda x: int(x.get('bitrate', 0)), reverse=True)
                stream_url = audio_formats[0].get('url', '')

                # Some instances proxy the URL through themselves
                if stream_url and stream_url.startswith('/'):
                    stream_url = instance + stream_url

                if not stream_url:
                    continue

                logger.info(f"Invidious stream URL from {instance}, downloading…")
                if status_callback:
                    status_callback.update({'progress': 40, 'message': 'Downloading audio stream…'})

                # Stream-download the audio file
                raw_audio = self._stream_download(stream_url, suffix='.webm')
                if not raw_audio:
                    continue

                if status_callback:
                    status_callback.update({'status': 'converting', 'progress': 75,
                                            'message': 'Converting to MP3…'})

                # Convert to MP3 with ffmpeg
                title = data.get('title', f'audio_{video_id}')
                safe_title = self._sanitize_filename(title)
                mp3_path = os.path.join(self.downloads_dir, f'{safe_title}_{numeric_quality}k.mp3')
                cmd = [FFMPEG_PATH, '-y', '-i', raw_audio,
                       '-vn', '-ar', '44100', '-ac', '2', '-b:a', f'{numeric_quality}k',
                       mp3_path]
                result = subprocess.run(cmd, capture_output=True, timeout=300)
                os.remove(raw_audio)  # clean up raw stream

                if result.returncode == 0 and os.path.exists(mp3_path):
                    logger.info(f"Invidious MP3 conversion OK: {mp3_path}")
                    if status_callback:
                        status_callback.update({'status': 'completed', 'progress': 100,
                                                'message': 'Conversion completed!'})
                    return mp3_path
                else:
                    logger.error(f"FFmpeg error: {result.stderr.decode()}")

            except Exception as e:
                logger.warning(f"Invidious MP3 failed ({instance}): {e}")

        return None

    def _invidious_to_mp4(self, video_id, quality, status_callback):
        """Download best combined video stream via Invidious and convert to MP4."""
        if status_callback:
            status_callback.update({'status': 'downloading', 'progress': 15,
                                    'message': 'Connecting via mirror server…'})
        q_num = int(quality.replace('p', ''))

        for instance in INVIDIOUS_INSTANCES:
            try:
                r = requests.get(f'{instance}/api/v1/videos/{video_id}',
                                 timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code != 200:
                    continue

                data = r.json()

                # Try combined format streams first (simpler, no mux needed)
                format_streams = data.get('formatStreams', [])
                format_streams.sort(key=lambda x: int(x.get('resolution', '0p').rstrip('p') or 0),
                                    reverse=True)
                stream_url = None
                for fs in format_streams:
                    res = int(fs.get('resolution', '0p').rstrip('p') or 0)
                    if res <= q_num:
                        stream_url = fs.get('url', '')
                        break

                if not stream_url:
                    continue
                if stream_url.startswith('/'):
                    stream_url = instance + stream_url

                if status_callback:
                    status_callback.update({'progress': 40, 'message': 'Downloading video stream…'})

                raw_video = self._stream_download(stream_url, suffix='.mp4')
                if not raw_video:
                    continue

                title = data.get('title', f'video_{video_id}')
                safe_title = self._sanitize_filename(title)
                mp4_path = os.path.join(self.downloads_dir, f'{safe_title}_{quality}.mp4')

                # Re-mux to ensure valid MP4
                cmd = [FFMPEG_PATH, '-y', '-i', raw_video, '-c', 'copy', mp4_path]
                result = subprocess.run(cmd, capture_output=True, timeout=300)
                os.remove(raw_video)

                if result.returncode == 0 and os.path.exists(mp4_path):
                    logger.info(f"Invidious MP4 download OK: {mp4_path}")
                    if status_callback:
                        status_callback.update({'status': 'completed', 'progress': 100,
                                                'message': 'Download completed!'})
                    return mp4_path
                else:
                    logger.error(f"FFmpeg error: {result.stderr.decode()}")

            except Exception as e:
                logger.warning(f"Invidious MP4 failed ({instance}): {e}")

        return None

    # -----------------------------------------------------------------------
    # Shared helpers
    # -----------------------------------------------------------------------

    def _stream_download(self, url, suffix='.tmp'):
        """Download a URL in chunks to a temp file. Returns file path or None."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            with requests.get(url, stream=True, timeout=300, headers=headers) as resp:
                resp.raise_for_status()
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix,
                                                  dir=self.temp_dir)
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        tmp.write(chunk)
                tmp.close()
                return tmp.name
        except Exception as e:
            logger.error(f"Stream download failed: {e}")
            return None

    def _resolve_output(self, downloaded_path, ext):
        """Find the output file after yt-dlp processing."""
        if downloaded_path:
            candidate = os.path.splitext(downloaded_path)[0] + ext
            if os.path.exists(candidate):
                return candidate
        # Fallback: newest file with this extension in downloads dir
        files = sorted(
            [os.path.join(self.downloads_dir, f)
             for f in os.listdir(self.downloads_dir) if f.endswith(ext)],
            key=os.path.getmtime, reverse=True
        )
        return files[0] if files else None

    def _maybe_crop(self, mp3_file, start_time, end_time, status_callback):
        """Apply ffmpeg crop if start/end times are given."""
        if start_time is None and end_time is None:
            return mp3_file
        try:
            if status_callback:
                status_callback.update({'status': 'converting', 'message': 'Cropping audio…'})
            cropped = os.path.join(self.downloads_dir, f'cropped_{os.path.basename(mp3_file)}')
            cmd = [FFMPEG_PATH, '-y', '-i', mp3_file]
            if start_time is not None:
                cmd.extend(['-ss', str(start_time)])
            if end_time is not None:
                cmd.extend(['-to', str(end_time)])
            cmd.extend(['-c', 'copy', cropped])
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0:
                return cropped
            logger.error(f"Crop failed: {result.stderr.decode()}")
        except Exception as e:
            logger.error(f"Crop error: {e}")
        return mp3_file  # return uncropped if crop fails

    def _extract_video_id(self, url):
        """Extract 11-char YouTube video ID from any valid YouTube URL."""
        match = re.search(r'(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None

    def _sanitize_filename(self, filename):
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'[^\w\s\-\.]', '', filename)
        filename = re.sub(r'\s+', '_', filename)
        return filename[:100] or 'audio'

    def estimate_file_size(self, duration, quality):
        bitrates = {'128k': 128000, '192k': 192000, '320k': 320000}
        bitrate = bitrates.get(quality, 192000)
        return (duration * bitrate) // 8

    def format_file_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
        names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {names[i]}"

    def check_dependencies(self):
        status = {
            'ffmpeg': False,
            'yt_dlp': False,
            'invidious': False,
            'temp_dir': os.path.exists(self.temp_dir),
            'downloads_dir': os.path.exists(self.downloads_dir),
        }
        try:
            result = subprocess.run([FFMPEG_PATH, '-version'],
                                    capture_output=True, text=True, timeout=10)
            status['ffmpeg'] = result.returncode == 0
        except Exception:
            pass
        try:
            import yt_dlp  # noqa
            status['yt_dlp'] = True
        except ImportError:
            pass
        # Quick Invidious connectivity check
        try:
            r = requests.get(f'{INVIDIOUS_INSTANCES[0]}/api/v1/stats', timeout=5)
            status['invidious'] = r.status_code == 200
        except Exception:
            pass
        return status

    def cleanup_temp_files(self):
        try:
            for f in os.listdir(self.temp_dir):
                fp = os.path.join(self.temp_dir, f)
                if os.path.isfile(fp):
                    os.remove(fp)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")