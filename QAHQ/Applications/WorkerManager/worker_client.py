import asyncio
import websockets
import json
import subprocess
import platform
import socket

# Configuration
HQ_URL = "ws://localhost:8000/ws/worker"
CLIENT_ID = socket.gethostname()
CAPABILITIES = ["run_command", "file_transfer"]

async def run_command(command):
    try:
        # Run command and capture output
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return {
            "status": "success" if process.returncode == 0 else "error",
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": process.returncode
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def worker():
    uri = f"{HQ_URL}/{CLIENT_ID}"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as websocket:
        # Register capabilities
        registration = {
            "capabilities": CAPABILITIES
        }
        await websocket.send(json.dumps(registration))
        print(f"Registered with capabilities: {CAPABILITIES}")
        
        response = await websocket.recv()
        print(f"HQ Response: {response}")

        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Received task: {data}")
                
                if data.get("type") == "run_command":
                    command = data.get("command")
                    print(f"Executing: {command}")
                    result = await run_command(command)
                    
                    # Send result back
                    response_msg = {
                        "type": "command_result",
                        "original_task": data,
                        "result": result
                    }
                    await websocket.send(json.dumps(response_msg))
                    print("Result sent.")
                    
            except websockets.ConnectionClosed:
                print("Connection closed")
                break
            except Exception as e:
                print(f"Error: {e}")
                break

if __name__ == "__main__":
    asyncio.run(worker())
