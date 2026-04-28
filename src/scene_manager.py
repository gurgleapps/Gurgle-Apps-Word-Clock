def apply_color_field(scene, field_name, *, normalise_color, log_scene, apply_color_value):
    color = normalise_color(scene[field_name])
    if color is None:
        log_scene("Invalid " + field_name + " in scene")
        return
    apply_color_value(field_name, color)


def apply_mode_specific_scene_fields(
    scene,
    mode,
    *,
    scene_mode_fields,
    normalise_color,
    log_scene,
    apply_color_value
):
    allowed_fields = scene_mode_fields.get(mode)
    if allowed_fields is None:
        log_scene("No scene field metadata for mode: " + str(mode))
        return

    for field_name in allowed_fields:
        if field_name in scene:
            apply_color_field(
                scene,
                field_name,
                normalise_color=normalise_color,
                log_scene=log_scene,
                apply_color_value=apply_color_value
            )


def apply_scene(
    scene_name_or_object,
    *,
    scenes,
    current_display_mode,
    display_modes,
    set_display_enabled,
    set_brightness,
    set_display_mode,
    apply_mode_specific_scene_fields,
    app_state,
    log_scene,
    max_brightness,
    reset_matrix_rain_state,
    rainbow_cycle_styles,
    rainbow_cycle_speed_limits,
    rainbow_cycle_spread_limits,
    rainbow_cycle_step_limits,
    reset_rainbow_cycle_state,
    is_display_enabled,
    time_to_matrix,
    clear_matrix,
    fallback_name=None
):
    scene_name = None
    if isinstance(scene_name_or_object, str):
        scene_name = scene_name_or_object
        scene = scenes.get(scene_name)
        if scene is None:
            log_scene("Scene not found: " + scene_name)
            return False, None
    else:
        scene = scene_name_or_object

    if not isinstance(scene, dict):
        log_scene("Invalid scene definition")
        return False, None

    next_mode = scene.get('display_mode', current_display_mode)
    if next_mode not in display_modes:
        log_scene("Invalid display mode in scene: " + str(next_mode))
        return False, None

    if 'display_enabled' in scene:
        if isinstance(scene['display_enabled'], bool):
            set_display_enabled(scene['display_enabled'])
        else:
            log_scene("Invalid display_enabled in scene")

    if 'brightness' in scene:
        if isinstance(scene['brightness'], int) and 0 <= scene['brightness'] <= max_brightness:
            set_brightness(scene['brightness'], persist=False)
        else:
            log_scene("Invalid brightness in scene")

    if 'display_mode' in scene:
        set_display_mode(next_mode, persist=False)

    apply_mode_specific_scene_fields(scene, next_mode)

    if next_mode == 'matrix_rain':
        if 'matrix_rain_white_head' in scene:
            if isinstance(scene['matrix_rain_white_head'], bool):
                app_state.matrix_rain_white_head = scene['matrix_rain_white_head']
            else:
                log_scene("Invalid matrix_rain_white_head in scene")
        if 'matrix_rain_affect_time' in scene:
            if isinstance(scene['matrix_rain_affect_time'], bool):
                app_state.matrix_rain_affect_time = scene['matrix_rain_affect_time']
            else:
                log_scene("Invalid matrix_rain_affect_time in scene")
        if 'matrix_rain_speed_ms' in scene:
            if isinstance(scene['matrix_rain_speed_ms'], int) and 40 <= scene['matrix_rain_speed_ms'] <= 400:
                app_state.matrix_rain_speed_ms = scene['matrix_rain_speed_ms']
            else:
                log_scene("Invalid matrix_rain_speed_ms in scene")
        if 'matrix_rain_spawn_rate' in scene:
            if isinstance(scene['matrix_rain_spawn_rate'], int) and 0 <= scene['matrix_rain_spawn_rate'] <= 100:
                app_state.matrix_rain_spawn_rate = scene['matrix_rain_spawn_rate']
            else:
                log_scene("Invalid matrix_rain_spawn_rate in scene")
        if 'matrix_rain_trail_length' in scene:
            if isinstance(scene['matrix_rain_trail_length'], int) and 1 <= scene['matrix_rain_trail_length'] <= 8:
                app_state.matrix_rain_trail_length = scene['matrix_rain_trail_length']
            else:
                log_scene("Invalid matrix_rain_trail_length in scene")
        if 'matrix_rain_time_brightness_cap' in scene:
            if isinstance(scene['matrix_rain_time_brightness_cap'], int) and 0 <= scene['matrix_rain_time_brightness_cap'] <= max_brightness:
                app_state.matrix_rain_time_brightness_cap = scene['matrix_rain_time_brightness_cap']
            else:
                log_scene("Invalid matrix_rain_time_brightness_cap in scene")
        reset_matrix_rain_state()

    if next_mode == 'rainbow_cycle':
        if 'rainbow_cycle_style' in scene:
            if scene['rainbow_cycle_style'] in rainbow_cycle_styles:
                app_state.rainbow_cycle_style = scene['rainbow_cycle_style']
            else:
                log_scene("Invalid rainbow_cycle_style in scene")
        if 'rainbow_cycle_speed_ms' in scene:
            min_speed, max_speed = rainbow_cycle_speed_limits
            if (
                isinstance(scene['rainbow_cycle_speed_ms'], int) and
                not isinstance(scene['rainbow_cycle_speed_ms'], bool) and
                min_speed <= scene['rainbow_cycle_speed_ms'] <= max_speed
            ):
                app_state.rainbow_cycle_speed_ms = scene['rainbow_cycle_speed_ms']
            else:
                log_scene("Invalid rainbow_cycle_speed_ms in scene")
        if 'rainbow_cycle_spread' in scene:
            min_spread, max_spread = rainbow_cycle_spread_limits
            if (
                isinstance(scene['rainbow_cycle_spread'], int) and
                not isinstance(scene['rainbow_cycle_spread'], bool) and
                min_spread <= scene['rainbow_cycle_spread'] <= max_spread
            ):
                app_state.rainbow_cycle_spread = scene['rainbow_cycle_spread']
            else:
                log_scene("Invalid rainbow_cycle_spread in scene")
        if 'rainbow_cycle_step' in scene:
            min_step, max_step = rainbow_cycle_step_limits
            if (
                isinstance(scene['rainbow_cycle_step'], int) and
                not isinstance(scene['rainbow_cycle_step'], bool) and
                min_step <= scene['rainbow_cycle_step'] <= max_step
            ):
                app_state.rainbow_cycle_step = scene['rainbow_cycle_step']
            else:
                log_scene("Invalid rainbow_cycle_step in scene")
        reset_rainbow_cycle_state()

    current_scene_name = scene_name if scene_name is not None else fallback_name

    if is_display_enabled():
        time_to_matrix()
    else:
        clear_matrix()

    if scene_name:
        log_scene("Applied scene: " + scene_name)
    elif fallback_name:
        log_scene("Applied scene preview: " + fallback_name)
    else:
        log_scene("Applied inline scene")
    return True, current_scene_name
