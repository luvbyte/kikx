let activeClients = [];

const ws = new WebSocket("ws://localhost:8000/client?token=1234");

class Client {
  constructor(payload) {
    this.clientID = payload.client_id;
    this.meta = payload.meta;
  }
}

function updateClients() {
  let clientsBox = $("#clients");
  clientsBox.empty();
  activeClients.forEach(e => {
    clientsBox.append(e + "\n");
  });
}

ws.onmessage = e => {
  let data = JSON.parse(e.data);
  if (data.event === "client:connect") {
    activeClients.push(new Client(data.payload));
    updateClients();
  } else if (data.event === "client:disconnect") {
    // const clientID = data.payload.client_id
    // const index = activeClients.indexOf(data.payload.client_id); // Find index of value 3
    // if (index !== -1) {
    // activeClients.splice(index, 1); // Remove the element at that index
    // }
    // updateClients();
  } else if (data.event === "broadcast") {
    console.log(data.payload);
  }
};

function sendEvent(event, payload) {
  ws.send(JSON.stringify({ event, payload }));
}
function send() {
  let el = $("#input");
  sendEvent("echo", {
    data: el.val()
  });
  el.val("");
}
