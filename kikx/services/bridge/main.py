from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uuid import uuid4
import logging

from lib.utils import is_websocket_connected
from lib.service import create_service

srv = create_service(__file__)

# - \ Node <-> Node <-> None /


class Node:
  def __init__(self, websocket):
    self.websocket = websocket
    self.id = uuid4().hex
  
  async def send_event(self, event, payload):
    if not is_websocket_connected(self.websocket):
      return
    
    await self.websocket.send_json({
      "event": event, "payload": payload
    })

class Group:
  def __init__(self, limit=2):
    self.limit = limit
    self.nodes = []
  
  async def broadcast(self, event, data, exclude=[]):
    for node in self.nodes:
      # skipping exclude ids
      if node.id in exclude:
        continue
      await node.send_event(event, data)
    
  async def connect_node(self, websocket) -> Node:
    if len(self.nodes) >= self.limit:
      raise Exception("Limit exceded")
    
    node = Node(websocket)
    self.nodes.append(node)
    
    # it will broadcast node:connect to everyone

    return node
  
  async def on_data(self, node: Node, data):
    pass
  
  async def disconnect_node(self, node):
    self.nodes.remove(node)

groups = {}

@srv.router.websocket("/connect/{gid}")
async def connect_node(websocket: WebSocket, gid: str, limit=2):
  await websocket.accept()
  try:
    group = groups.setdefault(gid, Group(limit))
    node = await group.connect_node(websocket)
    
  except Exception as e:
    await websocket.close(reason=str(e))
    return
  
  try:
    while True:
      await group.on_data(node, await websocket.receive_json())
  except WebSocketDisconnect:
    await group.disconnect_node(node)
    
    # cleaning empty group
    if len(group.nodes) <= 0:
      groups.pop(gid, None)
  except Exception as e:
    print(e)
