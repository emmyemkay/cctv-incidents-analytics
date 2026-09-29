from channels.generic.websocket import AsyncJsonWebsocketConsumer


class IncidentStreamConsumer(AsyncJsonWebsocketConsumer):
    group_name = "incident_stream"

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connection", "message": "Real-time incident stream connected."})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def incident_created(self, event):
        await self.send_json({"type": "incident.created", "incident": event["incident"]})
