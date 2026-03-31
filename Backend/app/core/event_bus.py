import asyncio
from typing import Callable, List, Dict, Any

class EventBus:
    """Asynchronous Pub/Sub internal event bus for decoupling modules."""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._queue = asyncio.Queue()

    def subscribe(self, event_type: str, listener: Callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    async def publish(self, event_type: str, payload: Any):
        await self._queue.put((event_type, payload))

    async def start_processing(self):
        """Must be launched as a background task during application startup."""
        while True:
            event_type, payload = await self._queue.get()
            if event_type in self._listeners:
                for listener in self._listeners[event_type]:
                    # Fire and forget asynchronous executions
                    asyncio.create_task(listener(payload))
            self._queue.task_done()

# Singleton shared instance
event_bus = EventBus()
