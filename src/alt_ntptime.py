try:
    import utime as time
except ImportError:
    import time
from time import gmtime
import machine
try:
    import usocket as socket
except ImportError:
    import socket
try:
    import ustruct as struct
except ImportError:
    import struct
try:
    import uselect as select
except ImportError:
    import select

# Default NTP server and constants
NTP_SERVER = 'pool.ntp.org'
NTP_DELTA = 3155673600 if gmtime(0)[0] == 2000 else 2208988800

def get_ntp_time(server=NTP_SERVER, timeout=1):
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B  # NTP packet mode: Client, version 3
    try:
        addr = socket.getaddrinfo(server, 123)[0][-1]
    except OSError as e:
        raise ValueError(f"Failed to resolve NTP server address: {e}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #s.settimeout(timeout)
        poller = select.poll()
        poller.register(s, select.POLLIN)
        s.sendto(NTP_QUERY, addr)
        if poller.poll(timeout * 1000):  # timeout in milliseconds
            msg = s.recv(48)
            if len(msg) < 48:
                raise ValueError("Received incomplete NTP response.")
            timestamp = struct.unpack("!I", msg[40:44])[0]
            return timestamp - NTP_DELTA
        else:
            raise TimeoutError("NTP request timed out.")
    finally:
        s.close()

def settime(server=NTP_SERVER, timeout=1):
    try:
        t = get_ntp_time(server, timeout)
        tm = time.gmtime(t)
        rtc = machine.RTC()
        rtc.datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
        print("Time successfully synchronized.")
    except Exception as e:
        # Propagate the exception or handle it here, depending on your design choice
        print(f"Failed to set system time due to: {e}")
        raise
