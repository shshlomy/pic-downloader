# 🖼️ Advanced Image Downloader Suite

A powerful, multi-threaded image downloading system with **fixed duplicate detection** and enhanced image filtering. Downloads high-quality images from original source websites with comprehensive tracking via SQLite database.

## 🌟 Key Features

### Core Capabilities
- **🔍 Smart URL Extraction**: Extracts original website URLs from Google Images (not thumbnails)
- **⚡ Multi-threaded Downloads**: Concurrent downloading with configurable worker threads
- **🔒 Fixed Duplicate Detection**: Proper hash-based deduplication using actual saved file content
- **📊 SQLite Database**: Complete tracking of searches, URLs, and downloaded images
- **🌐 Source Website Visiting**: Downloads images directly from original websites
- **🎯 Enhanced Image Filtering**: Skips irrelevant images like logos, icons, and UI elements

### Technical Features
- **Async/Await Architecture**: Efficient concurrent website visiting
- **Thread Pool Executor**: Parallel image downloading
- **MD5 Hash Verification**: Content-based duplicate detection using final saved files
- **Robust Error Handling**: Graceful failure recovery
- **Progress Tracking**: Real-time download status
- **Configurable Parameters**: Max images, worker threads, quality thresholds

## 📁 Project Structure

```
pic-downloader/
├── pic_downloader.py                    # Main entry point
├── comprehensive_downloader_fixed.py    # Core downloader with fixes
├── cleanup_duplicates.py               # Utility to remove duplicates
├── analyze_visit_buttons.py            # URL extraction analyzer/debugger
├── setup.py                            # Installation and setup script
├── requirements.txt                    # Python dependencies
├── image_sources.db                   # SQLite database (auto-created)
└── downloads/                         # Downloaded images directory
    ├── michael jordan/
    ├── noa kirel/
    └── [search_query]/
```

## 🚀 Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup
```bash
# Clone the repository
git clone [repository-url]
cd pic-downloader

# Install dependencies and Playwright browsers
python setup.py
```

## 💻 Usage

### Basic Usage

```bash
# Download with defaults (30 images, 5 threads)
python pic_downloader.py "michael jordan"

# Specify max images
python pic_downloader.py "noa kirel" 50

# Specify max images and worker threads
python pic_downloader.py "lebron james" 100 8
```

### Advanced Usage

```bash
# Use the core downloader directly
python comprehensive_downloader_fixed.py "search query" [max_images] [max_workers]

# Clean up existing duplicates in a folder
python cleanup_duplicates.py "downloads/folder_name"

# Analyze URL extraction from Google Images (debug tool)
python analyze_visit_buttons.py
```

## 🔧 Fixed Issues

### **Duplicate Detection Bug (FIXED)**
- **Previous Issue**: Hash calculated before PIL processing, but files saved after processing
- **Fix**: Hash now calculated from actual saved file content
- **Result**: True duplicate detection with 0% false negatives

### **Irrelevant Images (FIXED)**
- **Previous Issue**: Downloaded Wikipedia logos, UI elements, navigation icons
- **Fix**: Enhanced filtering with pattern recognition and size validation
- **Result**: Only relevant person/subject images downloaded

## 🗄️ Database Schema

The system uses SQLite with three main tables:

### `searches`
- `id`: Primary key
- `query`: Search term
- `search_date`: Timestamp
- `total_urls`: Number of URLs found

### `source_urls`
- `id`: Primary key
- `url`: Original website URL
- `domain`: Website domain
- `visited`: Boolean flag
- `images_found`: Count of images from this URL
- `error_message`: Any errors encountered

### `downloaded_images`
- `id`: Primary key
- `image_url`: Direct image URL
- `image_hash`: MD5 hash of **final saved file** (UNIQUE - for duplicate detection)
- `file_path`: Local file location
- `file_size`: Size in bytes
- `width`, `height`: Image dimensions
- `download_date`: Timestamp

## 🎯 Image Quality Settings

- **Minimum dimensions**: 150x150 pixels (increased from 100x100)
- **Minimum file size**: 8KB (increased from 5KB)
- **Supported formats**: JPG, JPEG, PNG, GIF, WebP
- **Enhanced filtering**: Skips logos, icons, sprites, UI elements

## 🚄 Performance

### Multi-Threading Benefits
- **5x faster** than sequential downloading
- Downloads 5-10 images simultaneously
- Concurrent website visiting
- Thread-safe database operations

### Benchmarks
- ~30 images in 30-60 seconds (with 5 threads)
- ~100 images in 2-3 minutes (with 8 threads)
- **0 duplicates** with proper hash-based detection

## 🔍 Duplicate Detection (Fixed)

The system implements **proper duplicate detection**:

1. **Content-Based**: Uses MD5 hash of **final saved file content**
2. **Database-Backed**: Hashes stored permanently in SQLite
3. **Cross-Search**: Detects duplicates across different searches
4. **Real-Time**: Checks both database and in-memory cache
5. **File Cleanup**: Removes duplicate files immediately upon detection

Example workflow:
```
1. Download image → Save with PIL → Calculate hash of saved file
2. Check hash against database and memory
3. If duplicate: delete file and skip
4. If unique: store hash in database and keep file
```

## 🧹 Cleanup Utilities

### Remove Existing Duplicates
```bash
# Clean up duplicates in a specific folder
python cleanup_duplicates.py "downloads/noa kirel"

# Example output:
# 📋 Duplicate set 1 (hash: e1c268f49ec7...):
#   ✅ Keeping: 020_upload_wikimedia_org.jpeg
#   🗑️  Removing: 021_upload_wikimedia_org.jpeg
#   🗑️  Removing: 036_upload_wikimedia_org.jpeg
```

## 🛠️ Troubleshooting

### Common Issues

1. **No images downloaded**
   - Check internet connection
   - Verify Playwright browsers are installed: `python setup.py`
   - Some websites may block automated access

2. **SSL Warnings**
   - Normal for some sites
   - Images still download successfully

3. **Database locked errors**
   - Close other instances of the script
   - Delete `image_sources.db` to start fresh

## 📈 Statistics & Monitoring

View database statistics:
```bash
# Total unique images
sqlite3 image_sources.db "SELECT COUNT(DISTINCT image_hash) FROM downloaded_images;"

# Images per search
sqlite3 image_sources.db "SELECT query, total_urls FROM searches;"

# Most productive domains
sqlite3 image_sources.db "SELECT domain, SUM(images_found) as total FROM source_urls GROUP BY domain ORDER BY total DESC LIMIT 10;"
```

## 🔍 URL Extraction Analysis

The `analyze_visit_buttons.py` tool helps debug URL extraction:

```bash
python analyze_visit_buttons.py
```

Output shows:
- Number of URLs found
- Extraction methods used
- Original website domains
- Cleaning of tracking parameters

## 📝 Requirements

### Python Packages
- `playwright>=1.40.0` - Browser automation
- `aiohttp>=3.9.0` - Async HTTP client
- `Pillow>=10.0.0` - Image processing
- `requests>=2.31.0` - Sync HTTP for threading

### System Requirements
- 4GB+ RAM recommended
- Stable internet connection
- 100MB+ free disk space per 100 images

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional image sources beyond Google Images
- Image quality scoring algorithms
- Cloud storage integration
- Web UI interface
- Docker containerization

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Playwright team for excellent browser automation
- Google Images for search capabilities
- Python async/threading communities

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section

---

**Note**: This tool is for educational purposes. Please respect website terms of service and copyright laws when downloading images.

## 🔄 Version History

- **v2.0** - Fixed duplicate detection, enhanced filtering, improved performance
- **v1.0** - Initial multi-threaded downloader with basic duplicate detection