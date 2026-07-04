
- Solve parameters that accept both 2D and 3D tuples (like pos, scale and angle in Entity).
- Implement a way to get the mouse delta without having to track it manually in the game code.
- Decide how to pass dt into tick() and render() and whether to make it optional or not. If optional, decide what the default value should be.
```python
def pos_tick(self, dt: float) -> None:
    pass

def pre_tick(self, dt: float) -> None:
    pass

def tick(self, dt: float) -> None:
    pass
```
- ShaderRender.render is creating a buffer at the wrong size, bug when instanciating two of the same entity:
```python
    # after this line: buffer_data = cls.create_instance_buffer(objects, instance_ssbo)
    if instance_buffer.size < len(buffer_data):
        instance_buffer.release()
        instance_buffer = cls._ctx.buffer(reserve=len(buffer_data))
        cls.buffer_map[shader_name][
            instance_ssbo.binding
        ] = instance_buffer
```
- Fix is_key_pressed and is_mouse_pressed to actually only return true on the frame the key was pressed, and not every frame the key is held down. (This probably applies to the mouse func too) 
- Destroying an object doesn't actually remove it from `EntityManager._entities`:
```python
def destroy_entity(cls, entity: Entity) -> None:
    cls.remove_entity_tick(entity, 0)
    cls.remove_entity_tick(entity, 1)
    cls.remove_entity_tick(entity, 2)
    
    cls._entities.pop(entity.get_id())  # <- Add this
```