from nekolib.console import Console
from nekolib.blocks import Label, Theme, Button, Row, PadX, Divider, Card, Box, VCenter, Center, Image, List, FlexGrow, TextInput, FullScreen, Border
from nekolib import panel


console = Console()

console.append(Label("Heading", align="center", size="lg")),

console.append(List([
  Label("primary", "primary", align="center"),
  Label("secondary", "secondary", align="center"),
  Label("accent", "accent", align="center"),
  
  Label("info", "info", align="center"),
  Label("success", "success", align="center"),
  Label("warning", "warning", align="center"),
  Label("error", "error", align="center"),
]))

console.append(Divider())

console.append(PadX(Row([
    Button("primary", "primary"),
    Button("secondary", "secondary"),
    FlexGrow(Button("accent", "accent")),
    FlexGrow(Button("success", "success"))
  ], gap=1, wrap=True)
))

console.append(Divider())

console.append(PadX(VCenter(
  Card(Center("This is card"), width="100%", height="200px"),
)))


console.append(Divider())
console.append(PadX(TextInput("This is input")))

console.append(Divider())
console.append(VCenter(Box(Image("/share/images/bg/hato.jpg"), width="50%")))
console.append(Divider())

console.append(Center("FullScreen"))

console.append(PadX(Border(Box("Hello", width="100%", height="200px"))))

