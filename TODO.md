# Sweet Game Engine - TODO

## High Priority

### Sound System
- [ ] Implement audio module (`sound.py`)
- [ ] Add support for multiple audio formats (MP3, WAV, OGG)
- [ ] Implement sound manager with volume and playback controls
- [ ] Support 3D audio positioning
- [ ] Add background music system

### Path Finding
- [ ] Complete path-finding implementation (`linalg/pathing.py`)
- [ ] Implement A* algorithm
- [ ] Support for different path interpolation types (Bezier, Piecewise)
- [ ] Path smoothing and optimization

### Network Improvements
- [ ] Implement client connection logic (`network/client.py`)
- [ ] Add connection error handling and reconnection logic
- [ ] Implement message acknowledgment system
- [ ] Add encryption/authentication for multiplayer
- [ ] Support for UDP in addition to TCP

## Medium Priority

### Entity System
- [ ] Expand `EntityManager` functionality
- [ ] Implement entity pooling for performance
- [ ] Add entity lifecycle hooks (on_create, on_destroy, on_update)
- [ ] Support entity groups and layers

### Graphics & Rendering
- [ ] Implement missing UI components (`graphics/UI.py`)
- [ ] Add font rendering system
- [ ] Implement particle effects system
- [ ] Add lighting system (normal mapping, dynamic lights)
- [ ] Support for multiple render targets/post-processing

### Input System
- [ ] Add gamepad/controller support
- [ ] Implement input binding system (rebindable controls)
- [ ] Add input state machine
- [ ] Support for touch input (mobile compatibility)

### Camera System
- [ ] Add camera animations/tweening
- [ ] Implement camera shake effect
- [ ] Add viewport culling for performance
- [ ] Support for parallax scrolling

### Physics & Collision
- [ ] Expand collision system beyond SAT
- [ ] Add physics body system (velocity, acceleration, forces)
- [ ] Implement gravity simulation
- [ ] Add trigger/event-based collisions
- [ ] Performance optimization for large object counts

## Low Priority

### Testing & Debugging
- [ ] Expand testing framework (`testing.py`)
- [ ] Add debug visualization tools
- [ ] Implement performance profiler
- [ ] Add memory leak detection

### Code Quality
- [ ] Add comprehensive docstrings to all modules
- [ ] Implement type hints throughout codebase
- [ ] Add unit tests
- [ ] Set up CI/CD pipeline
- [ ] Code coverage reporting

### Documentation
- [ ] Create API documentation
- [ ] Write setup/installation guide
- [ ] Create tutorial series for beginners
- [ ] Document shader system and custom shaders

### Performance
- [ ] Profile and optimize hot paths
- [ ] Implement spatial partitioning (quadtree/grid)
- [ ] Add object pooling system
- [ ] Optimize collision detection queries
- [ ] Reduce garbage collection pressure

## Known Issues

- [ ] Font system incomplete in `EntityTools`
- [ ] Sound module is empty placeholder
- [ ] Client networking not implemented
- [ ] Path finding system incomplete

## Future Features

- [ ] Scripting system (Lua integration)
- [ ] Save/Load system
- [ ] Level editor
- [ ] Asset pipeline and compiler
- [ ] Mobile platform support
- [ ] VR/XR support
- [ ] AI behavior tree system
- [ ] Dialog system
