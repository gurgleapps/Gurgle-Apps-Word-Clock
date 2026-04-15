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


def get_corrected_time(time_module, time_offset):
    return time_module.localtime(time_module.time() + time_offset)


def calculate_manual_time_offset(time_module, year, month, day, hour, minute, second):
    current_time = time_module.localtime()
    current_seconds = time_module.time()
    if second == 0:
        current_seconds -= current_time[5]
    manual_seconds = time_module.mktime((year, month, day, hour, minute, second, 0, 0))
    return manual_seconds - current_seconds
