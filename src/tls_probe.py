import asyncio
import ssl
import time

async def probe(ip, port, domain, timeout=3):
    start = time.perf_counter()

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                ip,
                port,
                ssl=ssl_context,
                server_hostname=domain
            ),
            timeout=timeout
        )

        req = (
            f"HEAD / HTTP/1.1\r\n"
            f"Host: {domain}\r\n"
            f"User-Agent: Mozilla/5.0\r\n"
            f"Connection: close\r\n\r\n"
        )

        writer.write(req.encode())
        await writer.drain()

        await asyncio.wait_for(reader.read(1), timeout=timeout)

        latency = int((time.perf_counter() - start) * 1000)

        writer.close()
        await writer.wait_closed()

        return {
            "ok": True,
            "latency": latency,
            "sni": domain
        }

    except:
        return {
            "ok": False
        }
