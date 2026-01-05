# Breville Joule Integration - Modernization

This integration has been updated to meet current Home Assistant standards and best practices.

## What's Changed

### ✅ **Modernized Architecture**
- **Config Flow UI**: Replaced YAML configuration with modern UI setup
- **Data Update Coordinator**: Replaced direct API calls with proper coordinator pattern
- **Runtime Data**: Using `config_entry.runtime_data` instead of `hass.data`
- **Proper Entity Design**: Modern entity structure with translation support

### ✅ **Updated Dependencies**
- **WebSocket Client**: Updated from 1.6.1 to >=1.8.0
- **Removed requests**: Using aiohttp (already available in HA)
- **PyJWT**: Updated to >=2.10.0 with better version flexibility

### ✅ **Modern Features**
- **Translation Support**: Full i18n with strings.json
- **Device Registry**: Proper device grouping and identification
- **Entity Descriptions**: Modern entity description pattern
- **Diagnostics**: Built-in diagnostic data collection
- **Reauthentication**: Automatic credential refresh flow

### ✅ **Better Error Handling**
- **Proper Exception Types**: Using HA's exception hierarchy
- **Async-First Design**: Full async/await pattern
- **Connection Management**: Better WebSocket connection handling
- **Logging**: Proper structured logging

### ✅ **Code Quality**
- **Type Hints**: Full type annotations for better IDE support
- **Documentation**: Comprehensive docstrings
- **Modern Python**: Using latest Python features (match/case, dataclasses)
- **Home Assistant Standards**: Following all current HA development guidelines

## Configuration

The integration now supports:
1. **UI Configuration**: Set up through Home Assistant's integration page
2. **Reauthentication**: Automatic handling of expired credentials
3. **Validation**: Real-time validation of credentials and device discovery

## Entities

The integration creates the following sensors for each Breville Joule device:
- **Current Temperature**: Real-time cooking temperature
- **Target Temperature**: Set cooking temperature
- **Start Time**: When cooking session started
- **End Time**: When cooking session will end
- **Cooking State**: Current state (idle/active)

## Technical Improvements

### Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Config Flow   │────│   Coordinator   │────│     Sensors     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │     Client      │
                       └─────────────────┘
                              │
                       ┌─────────────────┐
                       │  WebSocket API  │
                       └─────────────────┘
```

### Data Flow
1. **Setup**: Config flow validates credentials and discovers devices
2. **Initialization**: Coordinator sets up client and WebSocket connection
3. **Real-time Updates**: WebSocket pushes live data to entities
4. **State Management**: Coordinator manages all device state centrally

This modernization brings the integration up to current Home Assistant standards while maintaining full compatibility with existing functionality.