
- Change `Input.get_press` to `Input.is_pressed` and `Input.get_pressed` to `Input.is_pressed`
- Solve parameters that accept both 2D and 3D tuples (like pos, scale and angle in Entity).
- Implement a way to get the mouse delta without having to track it manually in the game code.
- Decide how to pass dt into tick() and render() and whether to make it optional or not. If optional, decide what the default value should be.
