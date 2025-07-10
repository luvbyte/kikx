package main

import (
    "fmt"
    // "io"
    // "net/http"
)


// Function that returns device details as a map
func getDeviceDetails() map[string]string {
    details := map[string]string{
        "id":   "12345",
        "name": "Sensor-X",
        "type": "Temperature",
    }
    return details
}


func main() {
  device_meta := map[string]interface{
    "system": "kikku",
  }
  files := [...]string{
    "static",
    "hooks/script.js",
  }
  
  for index, value := range files {
    fmt.Printf("%d : %s\n", index, value)
  }
  
  fmt.Println(device_meta["name"])
  
}

