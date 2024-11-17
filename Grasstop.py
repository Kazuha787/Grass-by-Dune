import asyncio
import random
import ssl
import json
import time
import uuid
from urllib.parse import urlparse
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

async def connect_to_wss(proxy_url, user_id):
    """
    Connect to a WebSocket server using a proxy and handle communication.
    """
    user_agent = UserAgent()
    random_user_agent = user_agent.random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_url))
    logger.info(f"Generated Device ID: {device_id}")
    
    urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
    server_hostname = "proxy2.wynd.network"
    
    # Extract proxy details
    parsed_proxy = urlparse(proxy_url)
    proxy_user = parsed_proxy.username
    proxy_pass = parsed_proxy.password
    proxy_host = parsed_proxy.hostname
    proxy_port = parsed_proxy.port

    proxy = Proxy(proxy_host, proxy_port, proxy_user, proxy_pass)

    while True:
        try:
            await asyncio.sleep(random.uniform(0.1, 1.0))  # Random delay
            custom_headers = {"User-Agent": random_user_agent}

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            uri = random.choice(urilist)
            logger.info(f"Connecting to URI: {uri} via Proxy: {proxy_host}:{proxy_port}")

            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                
                async def send_ping():
                    while True:
                        ping_message = {
                            "id": str(uuid.uuid4()),
                            "version": "1.0.0",
                            "action": "PING",
                            "data": {}
                        }
                        logger.debug(f"Sending Ping: {ping_message}")
                        await websocket.send(json.dumps(ping_message))
                        await asyncio.sleep(5)

                asyncio.create_task(send_ping())

                while True:
                    try:
                        response = await websocket.recv()
                        message = json.loads(response)
                        logger.info(f"Received: {message}")

                        if message.get("action") == "AUTH":
                            auth_response = {
                                "id": message["id"],
                                "origin_action": "AUTH",
                                "result": {
                                    "browser_id": device_id,
                                    "user_id": user_id,
                                    "user_agent": custom_headers['User-Agent'],
                                    "timestamp": int(time.time()),
                                    "device_type": "desktop",
                                    "version": "4.28.2",
                                }
                            }
                            logger.debug(f"Sending Auth Response: {auth_response}")
                            await websocket.send(json.dumps(auth_response))

                        elif message.get("action") == "PONG":
                            pong_response = {"id": message["id"], "origin_action": "PONG"}
                            logger.debug(f"Sending Pong Response: {pong_response}")
                            await websocket.send(json.dumps(pong_response))
                    except Exception as e:
                        logger.error(f"Error handling WebSocket message: {e}")
                        break

        except Exception as e:
            logger.error(f"Connection Error: {e}")
            logger.error(f"Proxy Used: {proxy_url}")
            await asyncio.sleep(5)  # Retry after a short delay

async def main():
    """
    Main entry point to start WebSocket connections.
    """
    user_id = input("Please Enter Your User ID: ")
    try:
        with open('local_proxies.txt', 'r') as file:
            local_proxies = file.read().splitlines()

        tasks = [connect_to_wss(proxy, user_id) for proxy in local_proxies]
        await asyncio.gather(*tasks)
    except FileNotFoundError:
        logger.error("File 'local_proxies.txt' not found. Please provide the file with proxy details.")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
