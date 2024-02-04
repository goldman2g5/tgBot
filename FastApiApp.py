from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from typing import Optional

from Websocket.SocketFunctions import *  # Import your functions here

app = FastAPI()


class FunctionCallRequest(BaseModel):
    functionName: str
    parameters: Optional[dict] = {}
    invocationId: Optional[str] = "unknown"


@app.post("/call-function/")
async def call_function(request: FunctionCallRequest):
    function_map = {
        "getDailyViewsByChannel": get_daily_views_by_channel,
        "getSubscribersCount": get_subscribers_count,
        "getProfilePictureAndUsername": get_profile_picture_and_username,
        "get_subscribers_count_batch": get_subscribers_count_batch,
        "getMonthlyViews": get_monthly_views_by_channel,
        "getBroadcastStats": get_broadcast_stats
    }

    function_name = request.functionName
    parameters = request.parameters
    invocation_id = request.invocationId

    if function_name in function_map:
        try:
            # Determine if the function is a coroutine for async call
            if asyncio.iscoroutinefunction(function_map[function_name]):
                result = await function_map[function_name](**parameters)
            else:
                result = function_map[function_name](**parameters)
            return {"invocationId": invocation_id, "data": result}
        except Exception as e:
            # Return an error message in the same format as the WebSocket service
            return {"invocationId": invocation_id, "error": f"Error in function execution: {str(e)}"}
    else:
        # If the function name does not match, raise an HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown function: {function_name}")
