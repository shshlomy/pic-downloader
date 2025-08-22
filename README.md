# 🚀 Modular Image Downloader

A **clean, modular, and maintainable** image downloading system built with **SOLID principles** and **design patterns**.

## ✨ Features

- **🔍 Smart Search**: Intelligent Google search with early termination
- **🖼️ Content Extraction**: Automated image extraction from websites
- **💾 Database Storage**: SQLite with proper foreign key constraints
- **📁 Organized Storage**: Sequential file naming with duplicate detection
- **⚡ Performance**: Multi-threaded downloads with configurable workers
- **🎯 Accuracy**: Meets exact image count requirements efficiently

## 🏗️ Architecture

### **SOLID Principles Implementation**
- **Single Responsibility**: Each class has one clear purpose
- **Open/Closed**: Extensible without modification
- **Liskov Substitution**: Interfaces work with any implementation
- **Interface Segregation**: Components only depend on needed interfaces
- **Dependency Inversion**: High-level modules depend on abstractions

### **Design Patterns**
- **Factory Pattern**: Centralized component creation
- **Strategy Pattern**: Pluggable search strategies
- **Dependency Injection**: Loose coupling between components
- **Template Method**: Structured workflow orchestration

### **Domain-Driven Design (DDD)**
- **Core Domain**: Fundamental business logic and interfaces
- **Search Domain**: Search operations and strategies
- **Extraction Domain**: Image extraction from web sources
- **Download Domain**: Image downloading operations
- **Storage Domain**: File storage and database management
- **Monitoring Domain**: Progress tracking and logging
- **Factory Domain**: Component creation and wiring
- **Configuration Domain**: Settings and configuration management

## 📁 Project Structure

```
pic-downloader/
├── main.py                       # 🎯 Main entry point
├── requirements.txt              # 📦 Dependencies
├── MODULAR_ARCHITECTURE.md      # 📚 Detailed documentation
├── downloads/                    # 📁 Downloaded images
└── pic_downloader/              # 📦 Main package
    ├── __init__.py
    ├── main.py                   # 🎯 Package entry point
    ├── core/                     # 🧠 Core domain
    │   ├── __init__.py
    │   ├── interfaces.py         # 🔌 Core abstractions
    │   └── orchestrator.py       # 🎼 Main coordinator
    ├── search/                   # 🔍 Search domain
    │   ├── __init__.py
    │   ├── providers/            # 🌐 Search providers
    │   │   ├── __init__.py
    │   │   └── google_provider.py
    │   └── strategies/           # 🧠 Search strategies
    │       ├── __init__.py
    │       └── smart_strategy.py
    ├── extraction/               # 🖼️ Extraction domain
    │   ├── __init__.py
    │   └── web_extractor.py
    ├── download/                 # ⬇️ Download domain
    │   ├── __init__.py
    │   └── http_downloader.py
    ├── storage/                  # 💾 Storage domain
    │   ├── __init__.py
    │   ├── managers/             # 📁 Storage managers
    │   │   ├── __init__.py
    │   │   └── sequential_manager.py
    │   └── database/             # 🗄️ Database operations
    │       ├── __init__.py
    │       └── sqlite_manager.py
    ├── monitoring/               # 📊 Monitoring domain
    │   ├── __init__.py
    │   └── progress_tracker.py
    ├── factory/                  # 🏭 Factory domain
    │   ├── __init__.py
    │   └── component_factory.py
    └── config/                   # ⚙️ Configuration domain
        ├── __init__.py
        └── settings.py
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Downloader
```bash
python3 main.py "search query" [number_of_images]
```

### 3. Examples
```bash
# Download 10 images of "sarit hadad"
python3 main.py "sarit hadad" 10

# Download 20 images of "gidi gov"
python3 main.py "gidi gov" 20

# Download 5 images of "eden harel"
python3 main.py "eden harel" 5
```

## 🔧 Configuration

The system automatically configures:
- **Max Workers**: 8 concurrent downloads
- **Database**: SQLite with foreign key enforcement
- **Storage**: Sequential file naming (000.jpg, 001.jpg, etc.)
- **Progress**: Real-time tracking with ETA

## 📊 Performance

- **Efficient Search**: Limits URL processing to avoid over-searching
- **Smart Termination**: Stops when target is nearly reached
- **Early Optimization**: Avoids unnecessary search variations
- **Resource Management**: Optimized memory and CPU usage

## 🗄️ Database Schema

### Tables
- **`searches`**: Search queries and metadata
- **`source_urls`**: Website URLs with foreign key to searches
- **`downloaded_images`**: Image metadata with foreign key to source_urls

### Features
- **Foreign Key Constraints**: Proper referential integrity
- **Indexes**: Optimized query performance
- **Cascade Deletes**: Automatic cleanup of related data

## 🧪 Testing

The system has been tested with:
- ✅ **Small downloads** (1-5 images)
- ✅ **Medium downloads** (10-20 images)
- ✅ **Large downloads** (30+ images)
- ✅ **Various search queries** (Hebrew, English, mixed)

## 🔍 How It Works

1. **Search Phase**: Google search for the query
2. **URL Collection**: Extract and store relevant URLs
3. **Website Processing**: Visit websites to extract images
4. **Image Download**: Download and validate images
5. **Storage**: Save images with sequential naming
6. **Database**: Store metadata and relationships

## 🎯 Key Benefits

- **Maintainable**: Clean, modular code structure
- **Extensible**: Easy to add new features
- **Efficient**: Smart search and early termination
- **Reliable**: Proper error handling and validation
- **Scalable**: Configurable worker pools and limits

## 🤝 Contributing

This codebase follows strict architectural principles:
- **No circular dependencies**
- **Clear interface contracts**
- **Comprehensive error handling**
- **Consistent naming conventions**

## 📚 Documentation

For detailed architectural information, see:
- [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md) - Complete architecture guide

---

**Built with ❤️ using SOLID principles and modern Python practices**
