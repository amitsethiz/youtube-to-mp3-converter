# YouTube to MP3 Converter

A modern, secure, and user-friendly web application for converting YouTube videos to high-quality MP3 audio files. Built with Flask, Bootstrap 5, and advanced security features.

## ⚠️ IMPORTANT: Known Issues & Solutions

### Common Installation Problems & Fixes

**1. Python 3.13 Compatibility Issues**
- **Problem:** `cryptography==41.0.8` not available, dependency conflicts
- **Solution:** Use version ranges in requirements.txt: `cryptography>=3.4.0,<45.0.0`

**2. FFmpeg Not Found Error**
- **Problem:** `[WinError 2] The system cannot find the file specified`
- **Solution:** Install FFmpeg first:
  ```powershell
  # PowerShell (as Admin):
  choco install ffmpeg -y
  # OR manual: Download from ffmpeg.org, add to PATH
  ```

**3. Missing Flask Dependencies**
- **Problem:** Import errors for Flask components
- **Solution:** Install all Flask dependencies:
  ```powershell
  pip install Flask Jinja2 MarkupSafe itsdangerous Click blinker
  ```

**4. Virtual Environment Issues**
- **Problem:** Permission errors, venv not working
- **Solution:** 
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  .\venv\Scripts\Activate.ps1
  ```

**5. Regex Character Range Error**
- **Problem:** `bad character range \s-. at position 4`
- **Solution:** Escape dash in regex: `[^\w\s\-\.]` not `[^\w\s-.]`

### Quick Fix Commands
```powershell
# Complete setup with troubleshooting
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
ffmpeg -version  # Must work before running app
python app.py
```

## ✨ Features

### Core Functionality
- 🎵 **YouTube to MP3 Conversion**: Download and convert YouTube videos to high-quality MP3 files
- 🔍 **URL Validation**: Real-time YouTube URL validation and security checks
- 📊 **Video Preview**: Display video title, thumbnail, duration, and uploader information
- 🎚️ **Quality Selection**: Choose from 128kbps, 192kbps, or 320kbps audio quality
- 📁 **Custom Download Location**: Select your preferred download directory
- ⏱️ **Progress Tracking**: Real-time conversion progress with status updates

### Security & Performance
- 🛡️ **Security First**: Input validation, CSRF protection, and rate limiting
- 🚀 **High Performance**: Optimized for fast conversion and download speeds
- 🔒 **Privacy Focused**: No user data storage, everything processed locally
- 🌐 **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- 🌓 **Dark/Light Mode**: Toggle between themes for optimal user experience

### User Experience
- 🎨 **Modern UI**: Clean, intuitive interface with smooth animations
- ⚡ **Fast Processing**: Efficient video downloading and audio extraction
- 📱 **Mobile Responsive**: Optimized for all screen sizes
- 🧭 **Easy Navigation**: Simple one-click conversion process
- 📈 **Real-time Feedback**: Progress bars and status messages

## 🚀 Quick Start (Windows 11)

### Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.8+** - Download from [python.org](https://www.python.org/downloads/)
2. **Git** (optional) - Download from [git-scm.com](https://git-scm.com/download/win)
3. **FFmpeg** - For audio conversion (instructions below) ❗ **REQUIRED**

### Step 1: Install FFmpeg ⚠️ IMPORTANT

**FFmpeg is REQUIRED for audio conversion. Follow these steps carefully:**

#### Method 1: Using Chocolatey (Recommended)
```powershell
# Install Chocolatey first (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install FFmpeg
choco install ffmpeg -y

# Restart your terminal and verify
ffmpeg -version
```

#### Method 2: Manual Installation
1. **Download FFmpeg** from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
2. **Extract** to `C:\ffmpeg`
3. **Add to PATH:**
   ```powershell
   [Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\ffmpeg\bin", "Machine")
   ```
4. **Restart terminal** and verify:
   ```powershell
   ffmpeg -version
   ```

**If you still get "file not found" errors, see INSTALL_FALLBACK.md for detailed troubleshooting.**

### Step 2: Clone and Setup Project

```powershell
# Navigate to your projects directory
cd C:\Users\$env:USERNAME\Documents

# Clone or create the project directory
git clone https://github.com/yourusername/youtube-to-mp3-converter.git
# OR if you have the source files, create the directory:
New-Item -ItemType Directory -Path "youtube-to-mp3-converter"
Set-Location "youtube-to-mp3-converter"
```

### Step 3: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# You should see (venv) in your prompt
```

**If you get execution policy error:**
```powershell
# Allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

### Step 4: Install Dependencies

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt
```

**If some packages fail to install individually:**
```powershell
# Install core dependencies first
pip install Flask>=2.3.0,<4.0.0
pip install yt-dlp>=2023.0.0
pip install Flask-CORS>=4.0.0
pip install python-dotenv>=1.0.0
pip install validators>=0.22.0
pip install Flask-Limiter>=3.5.0
pip install Werkzeug>=3.0.0
```

### Step 5: Run the Application

```powershell
# Start the Flask development server
python app.py
```

### Step 6: Access the Application

Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

## 🧪 Testing Your Installation

```powershell
# Run the installation test script
python test_installation.py

# Manual tests
python -c "import flask; print('Flask OK')"
python -c "import yt_dlp; print('yt-dlp OK')"
ffmpeg -version  # Must show version info
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | development |
| `FLASK_DEBUG` | Debug mode | false |
| `SECRET_KEY` | Flask secret key | auto-generated |
| `FFMPEG_PATH` | FFmpeg executable path | ffmpeg |
| `MAX_CONTENT_LENGTH` | Max file size | 50MB |
| `LOG_LEVEL` | Logging level | INFO |

### Custom Configuration

Edit `config.py` to modify:
- File size limits
- Conversion timeouts
- Rate limiting settings
- Security parameters

## 🔒 Security Information

### Security Features
- **Input Validation**: All URLs are validated and sanitized
- **Rate Limiting**: Prevents abuse and DoS attacks
- **CSRF Protection**: Cross-site request forgery prevention
- **File Type Validation**: Only allows safe file types
- **Temporary File Cleanup**: Automatic cleanup of temp files
- **Error Handling**: Secure error messages without data leakage

### Best Practices
- Always use HTTPS in production
- Set strong `SECRET_KEY` environment variable
- Keep dependencies updated
- Monitor logs for suspicious activity
- Use proper file permissions

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. "ModuleNotFoundError" or Import Errors
```powershell
# Check if virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. "FFmpeg not found" Error
```powershell
# Verify FFmpeg installation
ffmpeg -version

# Reinstall if needed
choco install ffmpeg -y
```

#### 3. Permission Errors in PowerShell
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 4. Virtual Environment Issues
```powershell
# Delete and recreate venv
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### 5. Port Already in Use
```powershell
# Find process using port 5000
netstat -ano | findstr :5000

# Kill the process or use different port
$env:FLASK_RUN_PORT = "5001"
python app.py
```

### Error Codes and Meanings

| Error Code | Description | Solution |
|------------|-------------|----------|
| 400 | Invalid URL | Check YouTube URL format |
| 413 | File too large | Reduce file size limits |
| 429 | Rate limit exceeded | Wait and try again |
| 500 | Server error | Check logs, restart application |
| 503 | Service unavailable | YouTube might be blocking requests |

### Logs and Debugging

```powershell
# View application logs
Get-Content youtube_converter.log -Wait

# Run with verbose output
$env:FLASK_DEBUG = "true"
python app.py
```

## 📦 Dependencies

### Core Dependencies
- **Flask 3.0.0**: Web framework
- **yt-dlp 2023.12.30**: YouTube video downloader
- **Flask-CORS 4.0.0**: Cross-origin resource sharing
- **Flask-Limiter 3.5.0**: Rate limiting

### Security & Validation
- **validators 0.22.0**: URL and input validation
- **python-dotenv 1.0.0**: Environment variable management
- **cryptography 41.0.8**: Cryptographic functions

### Utilities
- **Werkzeug 3.0.1**: WSGI utilities
- **requests 2.31.0**: HTTP library
- **tqdm 4.66.1**: Progress bars

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Add comments for complex logic
- Include docstrings for functions
- Write meaningful commit messages

### Testing
- Write unit tests for new features
- Test on different YouTube URL formats
- Verify error handling
- Test on different devices/browsers

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **yt-dlp**: For robust YouTube video downloading
- **FFmpeg**: For audio processing capabilities
- **Flask**: For the web framework
- **Bootstrap**: For responsive UI components
- **Font Awesome**: For beautiful icons

## 📞 Support

If you encounter any issues or have questions:

1. **Check the troubleshooting section** above
2. **Search existing issues** on GitHub
3. **Create a new issue** with detailed information
4. **Join our community** discussions

### Bug Reports
When reporting bugs, please include:
- Operating system and version
- Python version
- Complete error message
- Steps to reproduce
- Expected vs actual behavior

### Feature Requests
We welcome feature requests! Please describe:
- The problem you're trying to solve
- Proposed solution
- Alternative solutions you've considered

---

**Happy converting! 🎵**
http://127.0.0.1:5000/

*Built with ❤️ using modern web technologies and security best practices.*