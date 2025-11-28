package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"

	"github.com/gorilla/websocket"
)

type CommandResult struct {
	Event      string `json:"event"`
	ID         string `json:"id"`
	ReturnCode int    `json:"returnCode"`
	Stdout     string `json:"stdout"`
	Stderr     string `json:"stderr"`
	Error      string `json:"error,omitempty"`
}

// Incoming message format
type ServerMessage struct {
	Event   string `json:"event"`
	ID      string `json:"id"`
	Payload string `json:"payload"`
}

// RunCommand runs a shell command and returns stdout, stderr, and return code
func RunCommand(command string) (string, string, int, error) {
	cmd := exec.Command("bash", "-c", command)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = 1
		}
	}

	return stdout.String(), stderr.String(), exitCode, err
}

func main() {
	url := "ws://localhost:8000/service/vi/client/GoLinuxBash"
	if len(os.Args) > 1 {
		url = os.Args[1]
	}
	fmt.Println("Connecting to:", url)

	conn, _, err := websocket.DefaultDialer.Dial(url, nil)
	if err != nil {
		log.Fatal("dial error:", err)
	}
	defer conn.Close()

	go func() {
    for {
        _, message, err := conn.ReadMessage()
        if err != nil {
            fmt.Println("Disconnected:", err)
            os.Exit(0)
        }

        var msg ServerMessage
        if err := json.Unmarshal(message, &msg); err != nil {
            conn.WriteMessage(websocket.TextMessage, []byte(`{"error":"invalid json"}`))
            continue
        }

        if msg.Event != "exec" {
            conn.WriteMessage(websocket.TextMessage, []byte(`{"error":"unsupported event"}`))
            continue
        }

        cmd := msg.Payload

        // ✅ Async command execution
        go func(id, command string) {
            stdout, stderr, code, _ := RunCommand(command)

            resp := CommandResult{
                Event:      "exec",
                ID:         id,
                ReturnCode: code,
                Stdout:     stdout,
                Stderr:     stderr,
            }

            jsonResp, _ := json.Marshal(resp)
            conn.WriteMessage(websocket.TextMessage, jsonResp)
        }(msg.ID, cmd)
    }
}()

	scanner := bufio.NewScanner(os.Stdin)
	fmt.Println("Type messages and press Enter (Ctrl+C to quit):")
	for scanner.Scan() {
		text := scanner.Text()
		if text == "" {
			continue
		}
		err := conn.WriteMessage(websocket.TextMessage, []byte(text))
		if err != nil {
			fmt.Println("Write error:", err)
			break
		}
	}
}
