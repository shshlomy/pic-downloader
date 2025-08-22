# 🏗️ Modular Image Downloader Architecture

## 🎯 Overview

This project has been completely refactored to follow **SOLID principles**, **design patterns**, **Domain-Driven Design (DDD)**, and **good OO design practices**. The monolithic code has been organized into a clean, modular package structure with clear domain boundaries and proper separation of concerns.

## 📦 Package Structure & Domain Organization

The codebase is organized into logical domains following **Domain-Driven Design (DDD)** principles:

### **🧠 Core Domain (`pic_downloader/core/`)**
Contains the fundamental business logic and abstractions:
- **`interfaces.py`**: All interface definitions and data classes
- **`orchestrator.py`**: Main workflow coordinator

### **🔍 Search Domain (`pic_downloader/search/`)**
Handles all search-related operations:
- **`providers/`**: Search engine implementations (Google, etc.)
- **`strategies/`**: Search optimization algorithms

### **🖼️ Extraction Domain (`pic_downloader/extraction/`)**
Manages image extraction from web sources:
- **`web_extractor.py`**: Website image extraction logic

### **⬇️ Download Domain (`pic_downloader/download/`)**
Handles actual image downloading:
- **`http_downloader.py`**: HTTP-based image downloading

### **💾 Storage Domain (`pic_downloader/storage/`)**
Manages data persistence:
- **`managers/`**: File storage implementations
- **`database/`**: Database operations and schemas

### **📊 Monitoring Domain (`pic_downloader/monitoring/`)**
Provides observability and progress tracking:
- **`progress_tracker.py`**: Console-based progress tracking

### **🏭 Factory Domain (`pic_downloader/factory/`)**
Handles component creation and dependency injection:
- **`component_factory.py`**: Factory classes and wiring logic

### **⚙️ Configuration Domain (`pic_downloader/config/`)**
Manages application settings:
- **`settings.py`**: Configuration classes and management

## 🧩 Architecture Components

### **1. Core Interfaces (`interfaces.py`)**
- **Interface Segregation Principle (ISP)**: Each interface has a single, focused responsibility
- **Dependency Inversion Principle (DIP)**: High-level modules depend on abstractions, not concretions

```python
# Example interfaces
class ISearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str) -> SearchResult:
        pass

class IImageDownloader(ABC):
    @abstractmethod
    async def download_image(self, image_task: ImageTask) -> DownloadResult:
        pass
```

### **2. Concrete Implementations**
Each interface has concrete implementations following the **Single Responsibility Principle (SRP)**:

- **`GoogleSearchProvider`**: Handles Google search operations
- **`WebsiteImageExtractor`**: Extracts images from websites
- **`HTTPImageDownloader`**: Downloads images via HTTP
- **`SQLiteDatabaseManager`**: Manages database operations
- **`SequentialStorageManager`**: Handles file storage and naming
- **`SmartSearchStrategy`**: Manages search variation logic
- **`ConsoleProgressTracker`**: Tracks progress and provides logging

### **3. Main Orchestrator (`image_download_orchestrator.py`)**
- **Open/Closed Principle (OCP)**: Open for extension, closed for modification
- **Dependency Injection**: All dependencies injected through constructor
- **Single Responsibility**: Coordinates the workflow without implementing details

### **4. Factory Pattern (`factory.py`)**
- **Factory Pattern**: Centralized object creation
- **Dependency Injection**: Wires all components together
- **Configuration Management**: Centralized configuration handling

## 🔧 SOLID Principles Implementation

### **S - Single Responsibility Principle (SRP)**
Each class has one reason to change:

```python
class SQLiteDatabaseManager(IDatabaseManager):
    """Only handles database operations"""
    
class SequentialStorageManager(IStorageManager):
    """Only handles file storage operations"""
    
class ConsoleProgressTracker(IProgressTracker):
    """Only handles progress tracking and logging"""
```

### **O - Open/Closed Principle (OCP)**
System is open for extension, closed for modification:

```python
# Easy to add new search providers
class BingSearchProvider(ISearchProvider):
    async def search(self, query: str) -> SearchResult:
        # Bing-specific implementation
        pass

# Easy to add new storage managers
class CloudStorageManager(IStorageManager):
    def save_image(self, content: bytes, filepath: Path) -> bool:
        # Cloud storage implementation
        pass
```

### **L - Liskov Substitution Principle (LSP)**
Subtypes can be substituted for their base types:

```python
# Any implementation of ISearchProvider can be used
search_provider: ISearchProvider = GoogleSearchProvider()
# or
search_provider: ISearchProvider = BingSearchProvider()

# The orchestrator works with either
result = await search_provider.search("query")
```

### **I - Interface Segregation Principle (ISP)**
Clients don't depend on interfaces they don't use:

```python
# Image downloader only needs storage and content filter
class HTTPImageDownloader(IImageDownloader):
    def __init__(self, storage_manager: IStorageManager, content_filter: IContentFilter):
        # Only depends on what it actually uses
        pass

# Progress tracker only needs progress tracking methods
class ConsoleProgressTracker(IProgressTracker):
    # No unnecessary dependencies
    pass
```

### **D - Dependency Inversion Principle (DIP)**
High-level modules depend on abstractions:

```python
class ImageDownloadOrchestrator:
    def __init__(
        self,
        search_provider: ISearchProvider,  # Abstract interface
        image_extractor: IImageExtractor,  # Abstract interface
        image_downloader: IImageDownloader,  # Abstract interface
        # ... other abstractions
    ):
        # Depends on abstractions, not concrete implementations
        pass
```

## 🎨 Design Patterns Used

### **1. Factory Pattern**
```python
class ImageDownloaderFactory:
    @staticmethod
    def create_orchestrator(base_query: str, max_images: int) -> ImageDownloadOrchestrator:
        # Creates and wires all components
        pass
```

### **2. Strategy Pattern**
```python
class SmartSearchStrategy(ISearchStrategy):
    def should_generate_variations(self, current_count: int, target_count: int) -> bool:
        # Different strategies for when to generate variations
        pass
```

### **3. Dependency Injection**
```python
# Dependencies injected through constructor
downloader = create_image_downloader(
    base_query="sarit hadad",
    max_images=20,
    max_workers=8
)
```

### **4. Template Method Pattern**
```python
class ImageDownloadOrchestrator:
    async def download_images(self, base_query: str, max_images: int):
        # Template method defining the workflow
        await self._process_urls_phase()
        await self._try_remaining_urls()
        await self._process_variations()
```

## 🚀 Usage Examples

### **Basic Usage**
```python
from factory import create_image_downloader

# Create downloader
downloader = create_image_downloader("sarit hadad", 20)

# Run download
result = await downloader.download_images("sarit hadad", 20)
```

### **Custom Configuration**
```python
from factory import ImageDownloaderFactory
from google_search_provider import GoogleSearchProvider

# Custom search provider
custom_search = GoogleSearchProvider(headless=False, timeout=60000)

# Create with custom components
downloader = ImageDownloaderFactory.create_orchestrator(
    base_query="custom query",
    max_images=50,
    max_workers=16
)
```

### **Extending the System**
```python
# Add new search provider
class DuckDuckGoSearchProvider(ISearchProvider):
    async def search(self, query: str) -> SearchResult:
        # DuckDuckGo implementation
        pass

# Add new storage manager
class S3StorageManager(IStorageManager):
    def save_image(self, content: bytes, filepath: Path) -> bool:
        # S3 implementation
        pass
```

## 📊 Benefits of the New Architecture

### **1. Maintainability**
- **Single Responsibility**: Each class has one job
- **Clear Dependencies**: Easy to see what depends on what
- **Isolated Changes**: Changes in one component don't affect others

### **2. Testability**
- **Mocking**: Easy to mock interfaces for testing
- **Unit Testing**: Each component can be tested in isolation
- **Integration Testing**: Clear boundaries for integration tests

### **3. Extensibility**
- **New Search Providers**: Implement `ISearchProvider` interface
- **New Storage Backends**: Implement `IStorageManager` interface
- **New Content Filters**: Implement `IContentFilter` interface

### **4. Reusability**
- **Component Reuse**: Components can be used in other projects
- **Interface Contracts**: Clear contracts for component interaction
- **Plugin Architecture**: Easy to add new functionality

### **5. Performance**
- **Efficient Processing**: Better resource management
- **Parallel Downloads**: Improved concurrency handling
- **Memory Management**: Better memory usage patterns

## 🎯 Benefits of Package Organization

### **🔍 Clear Domain Boundaries**
- Each package represents a distinct business domain
- No circular dependencies between domains
- Easy to understand the system's structure at a glance

### **🧩 Modular Development**
- Teams can work on different domains independently
- Easy to add new providers, strategies, or storage backends
- Clear interfaces define contracts between domains

### **🔧 Maintainability**
- Changes in one domain don't affect others
- Easy to locate and modify specific functionality
- Clear separation of concerns reduces complexity

### **🚀 Extensibility**
- New search providers: Add to `search/providers/`
- New storage backends: Add to `storage/managers/`
- New monitoring systems: Add to `monitoring/`
- New configuration sources: Add to `config/`

### **🧪 Testability**
- Each domain can be tested in isolation
- Mock interfaces for unit testing
- Clear boundaries make integration testing easier

### **📖 Documentation**
- Package structure serves as living documentation
- Easy to onboard new developers
- Clear mental model of the system

## 🔄 Migration from Old Code

### **Before (Monolithic)**
```python
# Old usage
downloader = UnifiedMultiSearchDownloader("sarit hadad", 20)
await downloader.run()
```

### **After (Modular Package)**
```python
# New usage with package structure
from pic_downloader.factory import create_image_downloader

downloader = create_image_downloader(base_query="sarit hadad", max_images=20)
result = await downloader.download_images("sarit hadad", 20)
```

## 🧪 Testing the New Architecture

```bash
# Test the modular system
python3 main.py "sarit hadad" 10

# Test with different parameters
python3 main.py "gidi gov" 30

# Test small download
python3 main.py "test" 1
```

## 📁 Package Structure

```
pic-downloader/
├── main.py                          # 🎯 Main entry point
├── requirements.txt                 # 📦 Dependencies
├── MODULAR_ARCHITECTURE.md         # 📚 This documentation
├── downloads/                       # 📁 Downloaded images
└── pic_downloader/                 # 📦 Main package
    ├── __init__.py
    ├── main.py                      # 🎯 Package entry point
    ├── core/                        # 🧠 Core domain
    │   ├── __init__.py
    │   ├── interfaces.py            # 🔌 Core abstractions
    │   └── orchestrator.py          # 🎼 Main coordinator
    ├── search/                      # 🔍 Search domain
    │   ├── __init__.py
    │   ├── providers/               # 🌐 Search providers
    │   │   ├── __init__.py
    │   │   └── google_provider.py
    │   └── strategies/              # 🧠 Search strategies
    │       ├── __init__.py
    │       └── smart_strategy.py
    ├── extraction/                  # 🖼️ Extraction domain
    │   ├── __init__.py
    │   └── web_extractor.py
    ├── download/                    # ⬇️ Download domain
    │   ├── __init__.py
    │   └── http_downloader.py
    ├── storage/                     # 💾 Storage domain
    │   ├── __init__.py
    │   ├── managers/                # 📁 Storage managers
    │   │   ├── __init__.py
    │   │   └── sequential_manager.py
    │   └── database/                # 🗄️ Database operations
    │       ├── __init__.py
    │       └── sqlite_manager.py
    ├── monitoring/                  # 📊 Monitoring domain
    │   ├── __init__.py
    │   └── progress_tracker.py
    ├── factory/                     # 🏭 Factory domain
    │   ├── __init__.py
    │   └── component_factory.py
    └── config/                      # ⚙️ Configuration domain
        ├── __init__.py
        └── settings.py
```

## 🎯 Future Enhancements

1. **Multiple Search Providers**: Bing, DuckDuckGo, etc.
2. **Cloud Storage**: S3, Google Cloud Storage
3. **Advanced Content Filtering**: AI-powered image analysis
4. **Plugin System**: Dynamic loading of new components
5. **Configuration UI**: Web-based configuration interface
6. **API Endpoints**: RESTful API for programmatic access

## 🔍 Code Quality Metrics

- **SOLID Principles**: ✅ Fully implemented
- **Design Patterns**: ✅ Factory, Strategy, Dependency Injection
- **Code Coverage**: 🎯 High testability
- **Maintainability**: 🎯 Excellent separation of concerns
- **Extensibility**: 🎯 Easy to add new features
- **Performance**: 🎯 Optimized resource usage
