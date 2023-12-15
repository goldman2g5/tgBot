import asyncio
import websockets
import requests
import json


# Function for summing two numbers
def sum_of_two(number1, number2):
    print("function call")
    try:
        num1 = float(number1)
        num2 = float(number2)
    except ValueError:
        return {"error": "Invalid input. Please provide valid numbers."}

    total = num1 + num2
    return {"result": total}


# Helper function to format SignalR messages
def toSignalRMessage(data):
    return f'{json.dumps(data)}\u001e'


# Function to perform the handshake with the WebSocket server
async def handshake(websocket):
    await websocket.send(toSignalRMessage({"protocol": "json", "version": 1}))
    handshake_response = await websocket.recv()
    print(f"handshake_response: {handshake_response}")


# Function to maintain a ping to the WebSocket server
async def start_pinging(websocket, running):
    while running:
        await asyncio.sleep(10)
        try:
            await websocket.send(toSignalRMessage({"type": 6}))
        except websockets.exceptions.ConnectionClosed:
            break


# Function to listen for messages from the WebSocket server
async def listen(websocket, running):
    while running:
        try:
            get_response = await websocket.recv()
            print(f"get_response: {get_response}")
            # Find the end of the JSON object and trim the string
            end_of_json = get_response.rfind("}") + 1
            json_string = get_response[:end_of_json]

            # Parse the incoming JSON message
            try:
                outer_message_data = json.loads(json_string)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                continue  # Skip processing for this message

            # Check for the 'arguments' field which contains the actual function call
            if "arguments" in outer_message_data and outer_message_data["arguments"]:
                try:
                    # The function call data is expected to be a JSON string inside the 'arguments' array
                    function_call_data = json.loads(outer_message_data["arguments"][0])
                except (IndexError, json.JSONDecodeError) as e:
                    print(f"Error processing arguments: {e}")
                    continue  # Skip processing this message

                function_name = function_call_data.get("functionName")
                parameters = function_call_data.get("parameters", {})

                # Map function names to actual function calls
                function_map = {
                    "sumOfTwo": sum_of_two,  # Adding the sum_of_two function
                    # Add other functions here as needed
                }

                # Call the appropriate function
                if function_name in function_map:
                    try:
                        result = function_map[function_name](**parameters)
                    except TypeError as e:
                        result = {"error": f"Invalid parameters for {function_name}: {str(e)}"}
                    except Exception as e:
                        result = {"error": f"Error in {function_name}: {str(e)}"}
                else:
                    result = {"error": "Unknown function"}
            else:
                print("Not a function call type message. Skipping.")
                continue

            # Send the result back
            # start
            start_message = {
                "type": 1,
                "invocationId": "invocation_id",
                "target": "ReceiveStream",
                "arguments": [
                    'Bob'
                ],
                "streamIds": [
                    "stream_id"
                ]
            }
            await websocket.send(toSignalRMessage(start_message))
            # send
            message = {
                "type": 2,
                "invocationId": "stream_id",
                "item": f'{result}'
            }
            await websocket.send(toSignalRMessage(message))

            # end
            completion_message = {
                "type": 3,
                "invocationId": "stream_id"
            }
            await websocket.send(toSignalRMessage(completion_message))
        except websockets.exceptions.ConnectionClosed:
            break


# Main function to connect to the SignalR hub
async def connectToHub():

    while True:
        try:
            negotiation = requests.post('http://localhost:7256/BotHub/negotiate?negotiateVersion=0').json()
            connectionid = negotiation['connectionId']  # Update connectionId from new negotiation
            uri = f"ws://localhost:7256/BotHub?id={connectionid}"  # Update the URI with the new connectionId
            async with websockets.connect(uri) as websocket:
                await handshake(websocket)
                running = True
                listen_task = asyncio.create_task(listen(websocket, running))
                ping_task = asyncio.create_task(start_pinging(websocket, running))

                await asyncio.gather(listen_task, ping_task)
        except Exception as e:
            print(f"Error: {e}")
            print("Connection closed, attempting to reconnect...")
            await asyncio.sleep(5)  # Wait for 5 seconds before trying to reconnect


