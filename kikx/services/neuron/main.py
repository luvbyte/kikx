from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uuid import uuid4
import logging

from lib.utils import is_websocket_connected
from lib.service import create_service

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

srv = create_service(__file__)

class Node:
  def __init__(self, access, role, websocket, payload):
    self.id = uuid4().hex
    self.role = role
    self.access = access
    self.payload = payload
    self.websocket = websocket

class ChildNode(Node):
  def __init__(self, access, websocket, payload):
    super().__init__(access, "child", websocket, payload)

class ParentNode(Node):
  def __init__(self, access, websocket, payload):
    super().__init__(access, "parent", websocket, payload)
    self.children = set()

  async def create_child(self, access, websocket, payload):
    node = ChildNode(access, websocket, payload)
    self.children.add(node)
    logger.info(f"Child {node.id} connected to Parent {self.id} (Access: {self.access})")

    # Notify parent about child connection
    await self.send_event_to_parent("child:connected", node.id)

    return node

  async def remove_child(self, node):
    self.children.discard(node)
    logger.info(f"Child {node.id} disconnected from Parent {self.id} (Access: {self.access})")

    # Notify parent about child disconnection
    await self.send_event_to_parent("child:disconnected", node.id)

  async def broadcast(self, data):
    for child in list(self.children):
      try:
        await child.websocket.send_text(data)
        logger.debug(f"Broadcasted data to Child {child.id}")
      except Exception as e:
        logger.error(f"Failed to send data to Child {child.id}: {e}")
        await self.remove_child(child)

  async def send_data(self, child_node_id: str, data):
    for child in self.children:
      if child.id == child_node_id:
        try:
          await child.websocket.send_text(data)
          logger.debug(f"Sent data to Child {child.id}")
          return
        except Exception as e:
          logger.error(f"Error sending data to Child {child.id}: {e}")
          await self.remove_child(child)
        break
    logger.warning(f"Child node {child_node_id} not found for Parent {self.id} (Access: {self.access})")

  async def send_event_to_parent(self, event_type, child_id, payload=None):
    """Send an event notification to the parent."""
    if is_websocket_connected(self.websocket):
      event = {"event": event_type, "payload": { "id": child_id, "data": payload }}
      logger.info(f"Sending event to Parent {self.id}: {event}")
      try:
        await self.websocket.send_json(event)
      except Exception as e:
        logger.error(f"Failed to send event {event_type} to Parent {self.id}: {e}")

class NodesManager:
  def __init__(self):
    self.nodes = {}  # access_id -> ParentNode

  async def on_connect(self, role, access, websocket, payload):
    if access is None or len(access.strip()) <= 0:
      raise Exception("Access must be greter than 0")
    if role == "parent":
      if access in self.nodes:
        logger.warning(f"Parent connection attempt failed: Access {access} already in use.")
        raise Exception("Access code already exists")
      
      # app id check for auth
      _, app = srv.kikx_core.get_client_app_by_id(payload)
      if app is None:
        raise Exception("Unauthorized")
      # change access here with app_name
      # access = f"{app.name}:{access}"

      node = ParentNode(access, websocket, payload)
      self.nodes[access] = node
      logger.info(f"Parent {node.id} connected (Access: {access})")
      return node
    else:
      parent_node = self.nodes.get(access)
      if not parent_node:
        logger.warning(f"Child connection attempt failed: Parent not found for Access {access}.")
        raise Exception("Parent node not found for the given access code")

      return await parent_node.create_child(access, websocket, payload)

  async def on_data(self, node, data):
    if node.role == "parent":
      logger.debug(f"Parent {node.id} received data: {data}")
      await node.broadcast(data)
    else:
      parent_node = self.nodes.get(node.access)
      if parent_node:
        # Notify parent when child sends data
        logger.info(f"Child {node.id} sent data to Parent {parent_node.id}: {data}")
        await parent_node.send_event_to_parent("child:data", node.id, data)

  async def on_disconnect(self, node):
    """Handles disconnection for both parent and child nodes"""
    if node is None:
      return

    if node.role == "parent":
      logger.info(f"Disconnecting Parent {node.id} and all its children (Access: {node.access})")
      # Disconnect all child nodes
      for child in list(node.children):
        try:
          await child.websocket.close()
        except Exception:
          pass
      del self.nodes[node.access]
      logger.info(f"Parent {node.id} and its children were removed.")
    else:
      # Remove child from parent
      parent_node = self.nodes.get(node.access)
      if parent_node:
        await parent_node.remove_child(node)
        try:
          await node.websocket.close()
        except Exception:
          pass
      logger.info(f"Child {node.id} was removed from Parent {node.access}.")

nodes_manager = NodesManager()

@srv.router.get("/uuid")
def get_node_uuid():
  return uuid4().hex

@srv.router.websocket("/node/{access}")
async def connect_node(websocket: WebSocket, access: str, role: str = "child", payload=None):
  await websocket.accept()
  try:
    node = await nodes_manager.on_connect(role, access, websocket, payload)
  except Exception as e:
    logger.error(f"Connection error: {e}")
    await websocket.close(reason=str(e))
    return

  try:
    async for message in websocket.iter_text():
      logger.debug(f"Received message on Access {access}: {message}")
      await nodes_manager.on_data(node, message)
  except WebSocketDisconnect:
    logger.info(f"WebSocket disconnected. Role: {role}, Access: {access}")
  except Exception as e:
    logger.exception(f"Unexpected WebSocket error: {e}")
  finally:
    await nodes_manager.on_disconnect(node)
