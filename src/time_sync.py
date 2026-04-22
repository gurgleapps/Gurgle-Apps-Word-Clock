SEASONAL_TIME_REGION_OFF = 'off'
SEASONAL_TIME_REGION_UK = 'uk'
SEASONAL_TIME_REGION_CENTRAL_EUROPE = 'central_europe'
SEASONAL_TIME_REGION_US_EASTERN = 'us_eastern'
SEASONAL_TIME_REGION_US_CENTRAL = 'us_central'
SEASONAL_TIME_REGION_US_MOUNTAIN = 'us_mountain'
SEASONAL_TIME_REGION_US_PACIFIC = 'us_pacific'
SEASONAL_TIME_REGION_AUSTRALIA_EASTERN = 'australia_eastern'

VALID_SEASONAL_TIME_REGIONS = (
    SEASONAL_TIME_REGION_OFF,
    SEASONAL_TIME_REGION_UK,
    SEASONAL_TIME_REGION_CENTRAL_EUROPE,
    SEASONAL_TIME_REGION_US_EASTERN,
    SEASONAL_TIME_REGION_US_CENTRAL,
    SEASONAL_TIME_REGION_US_MOUNTAIN,
    SEASONAL_TIME_REGION_US_PACIFIC,
    SEASONAL_TIME_REGION_AUSTRALIA_EASTERN,
)

# To test regional time set region to UK set time to 2026-03-29 00:59 after 1 min it should switch to 2026-03-29 02:00


def test_dns(socket_module, logger=print):
    try:
        ip = socket_module.getaddrinfo('www.google.com', 80)
        logger("DNS resolution successful, IP:", ip)
        return True
    except OSError as error:
        logger("DNS resolution failed:", error)
        return False


async def sync_ntp_time(
    *,
    use_alternative,
    timeout,
    time_module,
    ticks_ms,
    asyncio_module,
    ntptime_module,
    alt_ntptime_module,
    retry_interval_seconds,
    last_ntp_sync_attempt,
    test_dns,
    is_wifi_connected,
    logger=print
):
    if last_ntp_sync_attempt and (time_module.time() - last_ntp_sync_attempt) < retry_interval_seconds:
        return {
            'success': False,
            'ntp_synced_at': None,
            'last_ntp_sync_attempt': last_ntp_sync_attempt,
            'last_wifi_connected_ticks': None
        }

    ntp_hosts = ['pool.ntp.org', 'time.nist.gov', 'time.google.com', 'time.windows.com']
    ntptime_module.timeout = timeout
    for ntp_host in ntp_hosts:
        try:
            if use_alternative:
                alt_ntptime_module.settime(ntp_host, timeout=timeout)
            else:
                ntptime_module.host = ntp_host
                ntptime_module.settime()
            now_seconds = time_module.time()
            logger(f"Time synced with {ntp_host} successfully using alternative method: {use_alternative}")
            return {
                'success': True,
                'ntp_synced_at': now_seconds,
                'last_ntp_sync_attempt': last_ntp_sync_attempt,
                'last_wifi_connected_ticks': ticks_ms()
            }
        except Exception as error:
            await asyncio_module.sleep(3)
            logger(f"Error syncing time with {ntp_host}: {error} using alternative method.{use_alternative}")

    if not use_alternative:
        logger("Standard methods failed, trying alternative methods.")
        return await sync_ntp_time(
            use_alternative=True,
            timeout=timeout,
            time_module=time_module,
            ticks_ms=ticks_ms,
            asyncio_module=asyncio_module,
            ntptime_module=ntptime_module,
            alt_ntptime_module=alt_ntptime_module,
            retry_interval_seconds=retry_interval_seconds,
            last_ntp_sync_attempt=last_ntp_sync_attempt,
            test_dns=test_dns,
            is_wifi_connected=is_wifi_connected,
            logger=logger
        )

    try:
        alt_ntptime_module.settime_via_http()
        now_seconds = time_module.time()
        logger("Time synced successfully using HTTP fallback")
        return {
            'success': True,
            'ntp_synced_at': now_seconds,
            'last_ntp_sync_attempt': last_ntp_sync_attempt,
            'last_wifi_connected_ticks': ticks_ms()
        }
    except Exception as error:
        logger(f"Error syncing time via HTTP fallback: {error}")

    dns_ok = test_dns()
    logger(f"Failed to sync time with all NTP servers. DNS check status: {dns_ok}")
    try:
        ntp_test = alt_ntptime_module.test_ntp_server()
        logger(f"NTP test result: {ntp_test}")
    except Exception as error:
        logger(f"Failed to test NTP server: {error}")
    try:
        http_time = alt_ntptime_module.get_time_via_http()
        logger(f"HTTP time: {http_time}")
    except Exception as error:
        logger(f"Failed to get time via HTTP: {error}")
    if is_wifi_connected() and test_dns():
        logger('wifi up, dns ok, but still failed to sync time')

    return {
        'success': False,
        'ntp_synced_at': None,
        'last_ntp_sync_attempt': time_module.time(),
        'last_wifi_connected_ticks': None
    }


def should_attempt_ntp_sync(
    *,
    is_wifi_connected,
    is_access_point_active,
    ticks_diff,
    ticks_ms,
    last_wifi_connected_time,
    initial_delay_ms,
    now,
    ntp_synced_at,
    sync_interval_seconds,
    last_ntp_sync_attempt,
    retry_interval_seconds
):
    if not is_wifi_connected():
        return False
    if is_access_point_active():
        return False
    if ticks_diff(ticks_ms(), last_wifi_connected_time) < initial_delay_ms:
        return False
    if ntp_synced_at >= (now - sync_interval_seconds):
        return False
    if last_ntp_sync_attempt and (now - last_ntp_sync_attempt) < retry_interval_seconds:
        return False
    return True


def normalise_seasonal_time_region(region):
    if not isinstance(region, str):
        return SEASONAL_TIME_REGION_OFF
    if region not in VALID_SEASONAL_TIME_REGIONS:
        return SEASONAL_TIME_REGION_OFF
    return region


def _is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_month(year, month):
    if month == 2:
        return 29 if _is_leap_year(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def _weekday(time_module, year, month, day):
    # We use the RTC's calendar math only to derive weekdays from dates.
    # This stays valid even though the device itself keeps UTC internally.
    return time_module.localtime(time_module.mktime((year, month, day, 0, 0, 0, 0, 0)))[6]


def _nth_sunday_of_month(time_module, year, month, nth):
    first_weekday = _weekday(time_module, year, month, 1)
    first_sunday = 1 + ((6 - first_weekday) % 7)
    return first_sunday + ((nth - 1) * 7)


def _last_sunday_of_month(time_module, year, month):
    last_day = _days_in_month(year, month)
    last_weekday = _weekday(time_module, year, month, last_day)
    return last_day - ((last_weekday - 6) % 7)


def _utc_epoch_from_local(time_module, year, month, day, hour, minute, second, offset_seconds):
    # Convert a local wall-clock transition into a UTC timestamp by subtracting
    # the region's offset that applies immediately before that transition.
    return time_module.mktime((year, month, day, hour, minute, second, 0, 0)) - offset_seconds


def get_region_possible_offsets_seconds(region):
    region = normalise_seasonal_time_region(region)
    if region == SEASONAL_TIME_REGION_OFF:
        return (0,)
    if region == SEASONAL_TIME_REGION_UK:
        return (0, 3600)
    if region == SEASONAL_TIME_REGION_CENTRAL_EUROPE:
        return (3600, 7200)
    if region == SEASONAL_TIME_REGION_US_EASTERN:
        return (-5 * 3600, -4 * 3600)
    if region == SEASONAL_TIME_REGION_US_CENTRAL:
        return (-6 * 3600, -5 * 3600)
    if region == SEASONAL_TIME_REGION_US_MOUNTAIN:
        return (-7 * 3600, -6 * 3600)
    if region == SEASONAL_TIME_REGION_US_PACIFIC:
        return (-8 * 3600, -7 * 3600)
    if region == SEASONAL_TIME_REGION_AUSTRALIA_EASTERN:
        return (10 * 3600, 11 * 3600)
    return (0,)


def get_region_time_offset_seconds(time_module, unix_time, region):
    region = normalise_seasonal_time_region(region)
    if region == SEASONAL_TIME_REGION_OFF:
        return 0

    year = time_module.localtime(unix_time)[0]

    # UK: clocks change on the last Sunday in March and October.
    # The official switch happens at 01:00 UTC in both directions.
    if region == SEASONAL_TIME_REGION_UK:
        start_day = _last_sunday_of_month(time_module, year, 3)
        end_day = _last_sunday_of_month(time_module, year, 10)
        start_utc = time_module.mktime((year, 3, start_day, 1, 0, 0, 0, 0))
        end_utc = time_module.mktime((year, 10, end_day, 1, 0, 0, 0, 0))
        return 3600 if start_utc <= unix_time < end_utc else 0

    # Central Europe (CET/CEST): standard UTC+1, then summer time at the
    # same EU-wide UTC transition moments as the UK.
    if region == SEASONAL_TIME_REGION_CENTRAL_EUROPE:
        start_day = _last_sunday_of_month(time_module, year, 3)
        end_day = _last_sunday_of_month(time_module, year, 10)
        start_utc = time_module.mktime((year, 3, start_day, 1, 0, 0, 0, 0))
        end_utc = time_module.mktime((year, 10, end_day, 1, 0, 0, 0, 0))
        return 7200 if start_utc <= unix_time < end_utc else 3600

    # US/Canada regions below use the same DST dates in most states/provinces:
    # second Sunday in March at 02:00 local standard time, then first Sunday in
    # November at 02:00 local daylight time.
    if region in (
        SEASONAL_TIME_REGION_US_EASTERN,
        SEASONAL_TIME_REGION_US_CENTRAL,
        SEASONAL_TIME_REGION_US_MOUNTAIN,
        SEASONAL_TIME_REGION_US_PACIFIC
    ):
        if region == SEASONAL_TIME_REGION_US_EASTERN:
            standard_offset = -5 * 3600
        elif region == SEASONAL_TIME_REGION_US_CENTRAL:
            standard_offset = -6 * 3600
        elif region == SEASONAL_TIME_REGION_US_MOUNTAIN:
            standard_offset = -7 * 3600
        else:
            standard_offset = -8 * 3600

        dst_offset = standard_offset + 3600
        start_day = _nth_sunday_of_month(time_module, year, 3, 2)
        end_day = _nth_sunday_of_month(time_module, year, 11, 1)
        start_utc = _utc_epoch_from_local(time_module, year, 3, start_day, 2, 0, 0, standard_offset)
        end_utc = _utc_epoch_from_local(time_module, year, 11, end_day, 2, 0, 0, dst_offset)
        return dst_offset if start_utc <= unix_time < end_utc else standard_offset

    # Australia Eastern here means NSW/VIC/ACT/TAS only:
    # first Sunday in October at 02:00 AEST, then first Sunday in April at
    # 03:00 AEDT back to 02:00 AEST.
    if region == SEASONAL_TIME_REGION_AUSTRALIA_EASTERN:
        standard_offset = 10 * 3600
        dst_offset = 11 * 3600
        start_day_this_year = _nth_sunday_of_month(time_module, year, 10, 1)
        end_day_this_year = _nth_sunday_of_month(time_module, year, 4, 1)
        start_this_year = _utc_epoch_from_local(time_module, year, 10, start_day_this_year, 2, 0, 0, standard_offset)
        end_this_year = _utc_epoch_from_local(time_module, year, 4, end_day_this_year, 3, 0, 0, dst_offset)
        if unix_time >= start_this_year:
            end_next_year_day = _nth_sunday_of_month(time_module, year + 1, 4, 1)
            end_next_year = _utc_epoch_from_local(time_module, year + 1, 4, end_next_year_day, 3, 0, 0, dst_offset)
            return dst_offset if unix_time < end_next_year else standard_offset

        start_previous_year_day = _nth_sunday_of_month(time_module, year - 1, 10, 1)
        start_previous_year = _utc_epoch_from_local(time_module, year - 1, 10, start_previous_year_day, 2, 0, 0, standard_offset)
        return dst_offset if start_previous_year <= unix_time < end_this_year else standard_offset

    return 0


def infer_region_offset_for_local_datetime(time_module, region, year, month, day, hour, minute, second):
    """
    Determine which UTC offset applies to a local wall-clock datetime.

    We intentionally use `mktime()` here as naive calendar arithmetic. The
    tuple is treated as "local wall clock" input for the region we are trying
    to resolve, not as the Pico's current timezone.

    Resolution policy:
    - Ambiguous fall-back times prefer the first valid offset from
      `get_region_possible_offsets_seconds()`, which is ordered with standard
      time first.
    - Non-existent spring-forward times fall forward to the DST/summer offset.
    """
    local_seconds = time_module.mktime((year, month, day, hour, minute, second, 0, 0))
    possible_offsets = get_region_possible_offsets_seconds(region)
    for offset_seconds in possible_offsets:
        candidate_utc = local_seconds - offset_seconds
        if get_region_time_offset_seconds(time_module, candidate_utc, region) == offset_seconds:
            return offset_seconds
    return max(possible_offsets)


def get_corrected_time(time_module, time_offset):
    return time_module.localtime(time_module.time() + time_offset)


def calculate_manual_time_offset(time_module, year, month, day, hour, minute, second, base_offset_seconds=0):
    current_time = time_module.localtime()
    current_seconds = time_module.time()
    if second == 0:
        current_seconds -= current_time[5]
    manual_seconds = time_module.mktime((year, month, day, hour, minute, second, 0, 0))
    return manual_seconds - current_seconds - base_offset_seconds
