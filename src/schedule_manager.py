def parse_schedule_time(time_string):
    if not isinstance(time_string, str) or len(time_string) != 5 or time_string[2] != ':':
        return None
    try:
        hour = int(time_string[:2])
        minute = int(time_string[3:])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return (hour, minute)


def normalise_schedule_days(days, weekday_names):
    if not isinstance(days, list) or not days:
        return None
    normalised_days = []
    for day in days:
        if not isinstance(day, str):
            return None
        day_name = day.lower()
        if day_name == 'all':
            return tuple(range(7))
        if day_name not in weekday_names:
            return None
        day_index = weekday_names.index(day_name)
        if day_index not in normalised_days:
            normalised_days.append(day_index)
    return tuple(normalised_days)


def validate_schedule_action(action, schedule_index, *, log_schedule, action_types, max_brightness, scenes):
    if not isinstance(action, dict):
        log_schedule("Ignoring schedule " + str(schedule_index) + ": action must be an object")
        return None

    action_type = action.get('type')
    if action_type not in action_types:
        log_schedule("Ignoring schedule " + str(schedule_index) + ": unsupported action type " + str(action_type))
        return None

    validated_action = {'type': action_type}
    if action_type == 'set_brightness':
        value = action.get('value')
        if not isinstance(value, int) or value < 0 or value > max_brightness:
            log_schedule("Ignoring schedule " + str(schedule_index) + ": invalid brightness value")
            return None
        validated_action['value'] = value
    elif action_type == 'apply_scene':
        scene_name = action.get('scene')
        if not isinstance(scene_name, str) or not scene_name:
            log_schedule("Ignoring schedule " + str(schedule_index) + ": invalid scene name")
            return None
        if scene_name not in scenes:
            log_schedule("Ignoring schedule " + str(schedule_index) + ": unknown scene " + scene_name)
            return None
        validated_action['scene'] = scene_name

    return validated_action


def validate_schedule_entry(entry, schedule_index, *, log_schedule, weekday_names, action_types, max_brightness, scenes):
    if not isinstance(entry, dict):
        log_schedule("Ignoring schedule " + str(schedule_index) + ": entry must be an object")
        return None

    schedule_name = entry.get('name', '')
    if schedule_name is None:
        schedule_name = ''
    if not isinstance(schedule_name, str):
        log_schedule("Ignoring schedule " + str(schedule_index) + ": name must be a string")
        return None

    enabled = entry.get('enabled', True)
    if not isinstance(enabled, bool):
        log_schedule("Ignoring schedule " + str(schedule_index) + ": enabled must be a boolean")
        return None
    if not enabled:
        return None

    days = normalise_schedule_days(entry.get('days'), weekday_names)
    if days is None:
        log_schedule("Ignoring schedule " + str(schedule_index) + ": invalid days")
        return None

    parsed_time = parse_schedule_time(entry.get('time'))
    if parsed_time is None:
        log_schedule("Ignoring schedule " + str(schedule_index) + ": invalid time")
        return None

    action = validate_schedule_action(
        entry.get('action'),
        schedule_index,
        log_schedule=log_schedule,
        action_types=action_types,
        max_brightness=max_brightness,
        scenes=scenes
    )
    if action is None:
        return None

    return {
        'index': schedule_index,
        'name': schedule_name.strip(),
        'days': days,
        'time': parsed_time,
        'time_string': entry.get('time'),
        'action': action
    }


def validate_schedules(schedule_entries, *, log_schedule, weekday_names, action_types, max_brightness, scenes):
    validated = []
    for index, entry in enumerate(schedule_entries):
        validated_entry = validate_schedule_entry(
            entry,
            index,
            log_schedule=log_schedule,
            weekday_names=weekday_names,
            action_types=action_types,
            max_brightness=max_brightness,
            scenes=scenes
        )
        if validated_entry is not None:
            validated.append(validated_entry)
    return validated


def describe_schedule_action(action):
    action_type = action['type']
    if action_type == 'set_brightness':
        return action_type + "(" + str(action['value']) + ")"
    if action_type == 'apply_scene':
        return action_type + "(" + action['scene'] + ")"
    return action_type


def evaluate_schedules(
    *,
    schedules_enabled,
    valid_schedules,
    last_schedule_evaluation_key,
    get_corrected_time,
    run_schedule_action,
    log_schedule,
    weekday_names
):
    if not schedules_enabled or not valid_schedules:
        return last_schedule_evaluation_key

    now = get_corrected_time()
    evaluation_key = (now[0], now[1], now[2], now[3], now[4])
    if evaluation_key == last_schedule_evaluation_key:
        return last_schedule_evaluation_key

    weekday = now[6]
    hour = now[3]
    minute = now[4]
    for schedule in valid_schedules:
        if weekday in schedule['days'] and (hour, minute) == schedule['time']:
            action_description = describe_schedule_action(schedule['action'])
            schedule_label = schedule['name'] if schedule['name'] else ('schedule ' + str(schedule['index'] + 1))
            log_schedule(
                "Matched " + schedule_label + " at " + schedule['time_string'] +
                " on " + weekday_names[weekday] +
                " -> running " + action_description
            )
            if not run_schedule_action(schedule['action']):
                log_schedule("Failed to run action: " + action_description)

    return evaluation_key
