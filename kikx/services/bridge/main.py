import logging
from uuid import uuid4
from typing import List, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from lib.service import create_service
from lib.utils import is_websocket_connected

# Init logger
logger = logging.getLogger("node-group")
logging.basicConfig(level=logging.INFO)

srv = create_service(__file__)


class Node:
  def __init__(self, websocket: WebSocket):
    self.websocket = websocket
    self.id: str = uuid4().hex

  async def send_event(self, event: str, payload: dict):
    if not is_websocket_connected(self.websocket):
      logger.warning(f"Node {self.id} is disconnected. Skipping send.")
      return

    try:
      await self.websocket.send_json({
        "event": event,
        "payload": payload
      })
    except Exception as e:
      logger.error(f"Failed to send event to node {self.id}: {e}")


class Group:
  def __init__(self, group_id: str, limit: int = 2):
    self.group_id = group_id
    self.limit = limit
    self.nodes: List[Node] = []

  async def broadcast(self, event: str, data: dict, exclude: List[str] = []):
    logger.debug(f"Broadcasting '{event}' to group '{self.group_id}'")
    for node in self.nodes:
      if node.id in exclude:
        continue
      await node.send_event(event, data)

  async def connect_node(self, websocket: WebSocket) -> Node:
    if len(self.nodes) >= self.limit:
      raise Exception(f"Group '{self.group_id}' is full (limit={self.limit})")

    node = Node(websocket)
    self.nodes.append(node)

    logger.info(f"Node {node.id} connected to group '{self.group_id}'")

    await self.broadcast("node:connect", {"id": node.id}, exclude=[node.id])
    return node

  async def disconnect_node(self, node: Node):
    if node in self.nodes:
      self.nodes.remove(node)
      logger.info(f"Node {node.id} disconnected from group '{self.group_id}'")
      await self.broadcast("node:disconnect", {"id": node.id})

  async def on_data(self, node: Node, data: dict):
    """
    Handle incoming data from a node.
    This is a placeholder for extending routing logic.
    """
    logger.info(f"Data from node {node.id} in group '{self.group_id}': {data}")
    await self.broadcast("node:data", {"from": node.id, "data": data}, exclude=[node.id])


class GroupManager:
  def __init__(self):
    self.groups: Dict[str, Group] = {}

  def get_or_create(self, gid: str, limit: int = 2) -> Group:
    if gid not in self.groups:
      self.groups[gid] = Group(gid, limit)
      logger.info(f"Created new group: '{gid}' (limit={limit})")
    return self.groups[gid]

  def cleanup(self, gid: str):
    group = self.groups.get(gid)
    if group and len(group.nodes) == 0:
      self.groups.pop(gid)
      logger.info(f"Group '{gid}' cleaned up (no active nodes)")


group_manager = GroupManager()


@srv.router.websocket("/connect/{gid}")
async def connect_node(websocket: WebSocket, gid: str, limit: int = 2):
  await websocket.accept()
  try:
    group = group_manager.get_or_create(gid, limit)
    node = await group.connect_node(websocket)
  except Exception as e:
    logger.error(f"Connection failed for group '{gid}': {e}")
    await websocket.close(reason=str(e))
    return

  try:
    while True:
      data = await websocket.receive_json()
      await group.on_data(node, data)
  except WebSocketDisconnect:
    logger.info(f"WebSocket disconnected for node {node.id}")
    await group.disconnect_node(node)
    group_manager.cleanup(gid)
  except Exception as e:
    logger.error(f"Unexpected error in group '{gid}': {e}")
    await websocket.close()
